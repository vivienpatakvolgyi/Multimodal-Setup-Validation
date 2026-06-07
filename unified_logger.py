"""
unified_logger.py
Unified timeseries CSV logger for the experiment battery.
Records all peripheral inputs (keyboard, mouse/touchpad) and experiment events
into a single CSV file at a fixed sampling frequency.

Usage:
    from unified_logger import logger
    logger.start("participant_01")
    logger.set_active_test("stroop")
    logger.log_event("stimulus_shown", "redgreen incongruent")
    logger.log_event("response", "key=g rt=450ms status=CORRECT")
    logger.set_active_test("")
    logger.stop()
"""

import csv
import time
import datetime
import threading
import os
from collections import deque

try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("[unified_logger] WARNING: pynput not available. Peripheral logging disabled.")


# Configuration
SAMPLE_HZ = 100  # Sampling frequency in Hz (100 Hz = 10ms resolution)
SAMPLE_INTERVAL = 1.0 / SAMPLE_HZ

# CSV columns
CSV_COLUMNS = [
    "timestamp_ms",       # ms since session start
    "datetime",           # ISO datetime string
    "sample_hz",          # constant: configured sampling rate
    "key_pressed",        # key name if pressed in this sample, else empty
    "key_action",         # press/release if key event, else empty
    "mouse_x",           # current mouse X coordinate on screen
    "mouse_y",           # current mouse Y coordinate on screen
    "mouse_button",      # mouse button if clicked, else empty
    "mouse_action",      # click_down/click_up/scroll if mouse button event
    "active_test",       # name of currently running test
    "event_type",        # experiment event type (stimulus/response/feedback/trial_start/trial_end)
    "event_detail",      # details about the event
]


class UnifiedLogger:
    """
    Singleton-style unified logger that captures:
    - Keyboard events (every press/release)
    - Mouse/touchpad movements (at SAMPLE_HZ)
    - Mouse clicks and scrolls
    - Experiment events (logged by test scripts)
    
    All data goes into a single time-series CSV file.
    """

    def __init__(self):
        self._running = False
        self._lock = threading.Lock()
        self._csv_file = None
        self._writer = None
        self._start_time = None
        self._active_test = ""
        self._mouse_x = 0
        self._mouse_y = 0
        self._kb_listener = None
        self._mouse_listener = None
        self._sampler_thread = None
        self._event_queue = deque()
        self._log_path = None

    @property
    def is_running(self):
        return self._running

    @property
    def log_path(self):
        return self._log_path

    def start(self, participant_id="participant"):
        """Start the unified logger. Opens CSV and starts peripheral listeners."""
        if self._running:
            print("[unified_logger] Already running.")
            return

        self._start_time = time.time()
        start_dt = datetime.datetime.now()
        
        # Sanitize participant_id for use in filename
        import re
        safe_id = re.sub(r'[<>:"/\\|?*\s]+', '_', participant_id).strip('_') or "participant"
        
        # Generate filename
        filename = f"experiment_log_{safe_id}_{start_dt.strftime('%Y%m%d_%H%M%S')}.csv"
        self._log_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), filename
        )

        # Open CSV
        self._csv_file = open(self._log_path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._csv_file)
        self._writer.writerow(CSV_COLUMNS)
        self._csv_file.flush()

        self._running = True
        self._active_test = ""

        # Log session start
        self._write_row(key_pressed="", key_action="", mouse_btn="", mouse_action="",
                        event_type="session_start",
                        event_detail=f"participant={participant_id} sample_hz={SAMPLE_HZ}")

        # Start peripheral listeners
        if PYNPUT_AVAILABLE:
            self._start_listeners()

        # Start background sampler (writes mouse position at SAMPLE_HZ)
        self._sampler_thread = threading.Thread(target=self._sampler_loop, daemon=True)
        self._sampler_thread.start()

        print(f"[unified_logger] Started. Logging to: {self._log_path}")

    def stop(self):
        """Stop the unified logger. Closes listeners and CSV file."""
        if not self._running:
            return

        self._running = False

        # Log session end
        self._write_row(key_pressed="", key_action="", mouse_btn="", mouse_action="",
                        event_type="session_end", event_detail="")

        # Stop listeners
        if self._kb_listener:
            self._kb_listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()

        # Wait for sampler to finish
        if self._sampler_thread and self._sampler_thread.is_alive():
            self._sampler_thread.join(timeout=2.0)

        # Close CSV
        if self._csv_file:
            self._csv_file.close()
            self._csv_file = None

        print(f"[unified_logger] Stopped. File saved: {self._log_path}")

    def set_active_test(self, test_name: str):
        """Set the currently active test name."""
        old = self._active_test
        self._active_test = test_name
        if test_name:
            self._write_row(key_pressed="", key_action="", mouse_btn="", mouse_action="",
                            event_type="test_start", event_detail=f"test={test_name}")
        elif old:
            self._write_row(key_pressed="", key_action="", mouse_btn="", mouse_action="",
                            event_type="test_end", event_detail=f"test={old}")

    def log_event(self, event_type: str, event_detail: str = ""):
        """
        Log an experiment event (stimulus, response, feedback, etc.)
        Called by individual test scripts.
        """
        if not self._running:
            return
        self._write_row(key_pressed="", key_action="", mouse_btn="", mouse_action="",
                        event_type=event_type, event_detail=event_detail)

    # Internal methods

    def _timestamp_ms(self):
        """Milliseconds since session start."""
        return round((time.time() - self._start_time) * 1000, 1)

    def _current_datetime(self):
        """Current datetime string with ms precision."""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _write_row(self, key_pressed, key_action, mouse_btn, mouse_action,
                   event_type="", event_detail=""):
        """Write a single row to the CSV (thread-safe)."""
        if not self._running or not self._writer:
            return
        row = [
            self._timestamp_ms(),
            self._current_datetime(),
            SAMPLE_HZ,
            key_pressed,
            key_action,
            self._mouse_x,
            self._mouse_y,
            mouse_btn,
            mouse_action,
            self._active_test,
            event_type,
            event_detail,
        ]
        with self._lock:
            try:
                self._writer.writerow(row)
                self._csv_file.flush()
            except (ValueError, OSError):
                pass  # file closed

    # Peripheral listeners (pynput)

    def _start_listeners(self):
        """Start keyboard and mouse listeners in dedicated daemon threads.
        
        On Windows, pynput hooks need a running message pump (GetMessage loop).
        pynput.Listener.start() creates its own thread with a message pump,
        but it can be starved when PsychoPy/pyglet monopolises the main thread.
        
        We set the listeners as daemon threads and use win32_event_filter=None
        (default) so they don't suppress events, keeping them independent of
        the main thread's event loop.
        """
        self._kb_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
            suppress=False
        )
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll,
            suppress=False
        )
        # Set as daemon so they don't block exit
        self._kb_listener.daemon = True
        self._mouse_listener.daemon = True
        self._kb_listener.start()
        self._mouse_listener.start()

    def _on_key_press(self, key):
        """Handle keyboard press event."""
        if not self._running:
            return  # Return None to keep listener alive
        try:
            key_name = self._format_key(key)
            self._write_row(key_pressed=key_name, key_action="press",
                            mouse_btn="", mouse_action="")
        except Exception:
            pass  # Never kill the listener

    def _on_key_release(self, key):
        """Handle keyboard release event."""
        if not self._running:
            return  # Return None to keep listener alive
        try:
            key_name = self._format_key(key)
            self._write_row(key_pressed=key_name, key_action="release",
                            mouse_btn="", mouse_action="")
        except Exception:
            pass

    def _on_mouse_move(self, x, y):
        """Handle mouse move - just update coordinates (sampled by ticker)."""
        if not self._running:
            return  # Return None to keep listener alive
        self._mouse_x = x
        self._mouse_y = y

    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse click event."""
        if not self._running:
            return  # Return None to keep listener alive
        try:
            self._mouse_x = x
            self._mouse_y = y
            action = "click_down" if pressed else "click_up"
            self._write_row(key_pressed="", key_action="",
                            mouse_btn=str(button), mouse_action=action)
        except Exception:
            pass

    def _on_mouse_scroll(self, x, y, dx, dy):
        """Handle mouse scroll event."""
        if not self._running:
            return  # Return None to keep listener alive
        try:
            self._mouse_x = x
            self._mouse_y = y
            self._write_row(key_pressed="", key_action="",
                            mouse_btn=f"scroll({dx},{dy})", mouse_action="scroll")
        except Exception:
            pass

    def _format_key(self, key):
        """Format a pynput key to a readable string."""
        try:
            return key.char if key.char else str(key)
        except AttributeError:
            return str(key).replace("Key.", "")

    # Background sampler

    def _sampler_loop(self):
        """
        Background thread that writes mouse position at fixed SAMPLE_HZ.
        This ensures continuous time-series data even when no events occur.
        """
        while self._running:
            self._write_row(
                key_pressed="", key_action="",
                mouse_btn="", mouse_action="",
                event_type="sample", event_detail=""
            )
            time.sleep(SAMPLE_INTERVAL)


# Global singleton instance
logger = UnifiedLogger()
