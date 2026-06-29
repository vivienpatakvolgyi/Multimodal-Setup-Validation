from __future__ import annotations

import asyncio
import queue
import struct
import threading
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Deque, List, Optional

import bitstruct
from bleak import BleakClient, BleakError

from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

# CONFIGURATION
POLAR_ADDRESS    = "24:AC:AC:04:68:1E"
HR_CHARACTERISTIC = "00002A37-0000-1000-8000-00805F9B34FB"

WINDOW_SECONDS   = 60       # Rolling display window in seconds
STORE_MAXLEN     = 2000     # Deque capacity (~60 s at typical HR cadence)
UPDATE_INTERVAL_MS = 200    # Refresh rate

RECONNECT_BASE_DELAY = 2.0  
RECONNECT_MAX_DELAY  = 30.0

ENABLE_CSV_LOGGER = False
CSV_PATH = "hr_export.csv"


# DATA MODEL
@dataclass(frozen=True)
class SensorSample:
    timestamp: float          # POSIX seconds (datetime.now().timestamp())
    hr_bpm:    int            # Heart Rate in BPM
    rr_ms:     Optional[float]  # RR interval in ms, or None


# DATA CONSUMERS  (abstract base + concrete implementations)
class DataConsumer(ABC):
    @abstractmethod
    def consume(self, sample: SensorSample) -> None: ...
    def close(self) -> None:
      pass


class DataStore(DataConsumer):
    def __init__(self, maxlen: int = STORE_MAXLEN) -> None:
        self._lock = threading.RLock()
        self._timestamps: Deque[float]           = deque(maxlen=maxlen)
        self._hr_bpm:     Deque[int]             = deque(maxlen=maxlen)
        self._rr_ms:      Deque[Optional[float]] = deque(maxlen=maxlen)

    def consume(self, sample: SensorSample) -> None:
        with self._lock:
            self._timestamps.append(sample.timestamp)
            self._hr_bpm.append(sample.hr_bpm)
            self._rr_ms.append(sample.rr_ms)

    def snapshot(self, window_seconds: float = WINDOW_SECONDS):
        with self._lock:
            if not self._timestamps:
                return [], [], []

            t_right = self._timestamps[-1]
            cutoff  = t_right - window_seconds

            x_rel: List[float]          = []
            hr:    List[int]            = []
            rr:    List[Optional[float]] = []

            for ts, h, r in zip(self._timestamps, self._hr_bpm, self._rr_ms):
                if ts >= cutoff:
                    x_rel.append(ts - cutoff)   # 0 … window_seconds
                    hr.append(h)
                    rr.append(r)

        return x_rel, hr, rr

    @property
    def is_empty(self) -> bool:
        return len(self._timestamps) == 0


class CSVLogger(DataConsumer):
    def __init__(self, path: str = CSV_PATH) -> None:
        import csv
        self._file   = open(path, "a", newline="", buffering=1)
        self._writer = csv.writer(self._file)

    def consume(self, sample: SensorSample) -> None:
        rr_str = f"{sample.rr_ms:.2f}" if sample.rr_ms is not None else ""
        self._writer.writerow([int(sample.timestamp), sample.hr_bpm, rr_str])

    def close(self) -> None:
        self._file.close()


# DATA ROUTER 
class DataRouter:
    def __init__(self, data_queue: "queue.Queue[SensorSample]") -> None:
        self._queue     = data_queue
        self._consumers: List[DataConsumer] = []
        self._thread    = threading.Thread(
            target=self._run, name="DataRouter", daemon=True
        )

    def register_consumer(self, consumer: DataConsumer) -> None:
        """Register a consumer before start() is called."""
        self._consumers.append(consumer)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        while True:
            try:
                sample: SensorSample = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            for consumer in self._consumers:
                try:
                    consumer.consume(sample)
                except Exception as exc:
                    print(f"[DataRouter] Consumer {consumer!r} raised: {exc}")

# BLE WORKER  (Polar H10 via Bleak, asyncio in daemon thread)
class PolarBLEWorker:
    def __init__(
        self,
        address: str,
        characteristic: str,
        data_queue: "queue.Queue[SensorSample]",
    ) -> None:
        self._address        = address
        self._characteristic = characteristic
        self._queue          = data_queue

    # Public API
    def run_forever(self) -> None:
        asyncio.run(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        delay = RECONNECT_BASE_DELAY
        while True:
            try:
                await self._run_session()
                print("[BLE] Session ended cleanly — reconnecting …")
                delay = RECONNECT_BASE_DELAY  
            except BleakError as exc:
                print(f"[BLE] BleakError: {exc}. Retrying in {delay:.1f} s …")
            except Exception as exc:
                print(f"[BLE] Unexpected error: {exc}. Retrying in {delay:.1f} s …")

            await asyncio.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX_DELAY)

    async def _run_session(self) -> None:
        print(f"[BLE] Connecting to {self._address} …")
        async with BleakClient(
            self._address,
            timeout=20,
            winrt={"use_cached_services": False},
        ) as client:
            print(f"[BLE] Connected: {client.is_connected}")
            await client.start_notify(self._characteristic, self._hr_handler)
            print("[BLE] Subscribed to HR notifications.")
            while client.is_connected:
                await asyncio.sleep(0.5)

            print("[BLE] Device disconnected.")

    # Notification callback - PRESERVED from hrexample.py
    def _hr_handler(self, sender, data: bytearray) -> None:
        (
            rr_present,
            energy_present,
            sensor_supported,
            sensor_detected,
            hr_16bit,
        ) = bitstruct.unpack("p3b1b1b1b1b1<", data)

        # --- Heart Rate value ---
        if hr_16bit:
            hr_bpm = struct.unpack_from("<H", data, 1)[0]
            offset = 3
        else:
            hr_bpm = struct.unpack_from("<B", data, 1)[0]
            offset = 2

        # --- RR interval (optional) ---
        rr_ms: Optional[float] = None
        if rr_present:
            rr_raw = struct.unpack_from("<H", data, offset)[0]
            # Bluetooth HR spec: RR resolution is 1/1024 s
            rr_ms = rr_raw * 1000.0 / 1024.0

        sample = SensorSample(
            timestamp=datetime.now().timestamp(),
            hr_bpm=hr_bpm,
            rr_ms=rr_ms,
        )
        try:
            self._queue.put_nowait(sample)
        except queue.Full:
            print("[BLE] Warning: queue full — sample dropped.")


# DASH APPLICATION
_DARK_BG      = "#1a1a2e"
_PLOT_BG      = "#16213e"
_GRID_COLOR   = "#2a2a4e"
_FONT_COLOR   = "#e0e0e0"
_COLOR_HR     = "#e94560"
_COLOR_RR_LINE = "#5588cc"
_COLOR_RR_MARK = "#e94560"


def _base_layout(title: str, yaxis_title: str, y_range: list) -> dict:
    """Shared Plotly layout dict for both graphs."""
    return dict(
        title=title,
        xaxis_title="Time (s)",
        yaxis_title=yaxis_title,
        xaxis=dict(range=[0, WINDOW_SECONDS], gridcolor=_GRID_COLOR),
        yaxis=dict(range=y_range,             gridcolor=_GRID_COLOR),
        margin=dict(l=60, r=20, t=50, b=40),
        paper_bgcolor=_DARK_BG,
        plot_bgcolor=_PLOT_BG,
        font=dict(color=_FONT_COLOR),
        uirevision="constant",   # prevents Plotly from resetting zoom on update
    )


def _empty_figure(title: str, yaxis_title: str, y_range: list) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[], y=[], mode="lines"))
    fig.update_layout(**_base_layout(title, yaxis_title, y_range))
    return fig


def build_dash_app(store: DataStore) -> Dash:
    app = Dash(__name__, title="Polar H10 Live Monitor")

    app.layout = html.Div(
        style={
            "backgroundColor": _DARK_BG,
            "fontFamily": "'Segoe UI', Arial, sans-serif",
            "padding": "20px",
            "minHeight": "100vh",
        },
        children=[
            html.H2(
                "Polar H10 Live Monitor",
                style={"color": _COLOR_HR, "textAlign": "center", "marginBottom": "4px"},
            ),
            html.Div(
                id="status-bar",
                style={
                    "color": "#aaaaaa",
                    "textAlign": "center",
                    "marginBottom": "16px",
                    "fontSize": "14px",
                    "letterSpacing": "0.05em",
                },
                children="Connecting to Polar H10 …",
            ),
            dcc.Graph(
                id="hr-graph",
                figure=_empty_figure("Heart Rate", "BPM", [30, 220]),
                config={"displayModeBar": False},
                style={"marginBottom": "10px"},
            ),
            dcc.Graph(
                id="rr-graph",
                figure=_empty_figure("RR Interval", "ms", [300, 1500]),
                config={"displayModeBar": False},
            ),
            # Interval component drives all graph updates; no page refresh needed.
            dcc.Interval(
                id="interval-component",
                interval=UPDATE_INTERVAL_MS,
                n_intervals=0,
            ),
        ],
    )

    @app.callback(
        Output("hr-graph",   "figure"),
        Output("rr-graph",   "figure"),
        Output("status-bar", "children"),
        Input("interval-component", "n_intervals"),
    )
    def update_graphs(_n: int):
        x_rel, hr, rr = store.snapshot(WINDOW_SECONDS)

        if not x_rel:
            empty_status = "Connecting to Polar H10 …"
            return (
                _empty_figure("Heart Rate",  "BPM", [30, 220]),
                _empty_figure("RR Interval", "ms",  [300, 1500]),
                empty_status,
            )

        # Status bar summary
        latest_rr_str = f"{rr[-1]:.1f} ms" if rr[-1] is not None else "—"
        status = (
            f"HR: {hr[-1]} BPM   |   RR: {latest_rr_str}"
            f"   |   Samples in window: {len(hr)}"
        )

        # Heart Rate figure
        fig_hr = go.Figure()
        fig_hr.add_trace(go.Scatter(
            x=x_rel, y=hr,
            mode="lines+markers",
            name="HR",
            line=dict(color=_COLOR_HR, width=2),
            marker=dict(size=4, color=_COLOR_HR),
        ))
        fig_hr.update_layout(**_base_layout("Heart Rate", "BPM", [30, 220]))

        # RR Interval figure
        fig_rr = go.Figure()
        fig_rr.add_trace(go.Scatter(
            x=x_rel, y=rr,
            mode="lines+markers",
            name="RR",
            line=dict(color=_COLOR_RR_LINE, width=2),
            marker=dict(size=4, color=_COLOR_RR_MARK),
            connectgaps=False,   # leave visible gaps where rr_ms is None
        ))
        fig_rr.update_layout(**_base_layout("RR Interval", "ms", [300, 1500]))

        return fig_hr, fig_rr, status

    return app


# ENTRY POINT
def main() -> None:
    data_queue: "queue.Queue[SensorSample]" = queue.Queue(maxsize=500)
    store  = DataStore(maxlen=STORE_MAXLEN)
    router = DataRouter(data_queue)
    router.register_consumer(store)

    if ENABLE_CSV_LOGGER:
        router.register_consumer(CSVLogger(CSV_PATH))
    app = build_dash_app(store)
    dash_thread = threading.Thread(
        target=app.run,
        kwargs={
            "debug":        False,
            "host":         "127.0.0.1",
            "port":         8050,
            "use_reloader": False,
        },
        name="DashServer",
        daemon=True,
    )
    router.start()
    dash_thread.start()
    print("[Main] Dashboard running at  http://127.0.0.1:8050/")

    ble_worker = PolarBLEWorker(POLAR_ADDRESS, HR_CHARACTERISTIC, data_queue)
    ble_worker.run_forever() 

if __name__ == "__main__":
    main()
