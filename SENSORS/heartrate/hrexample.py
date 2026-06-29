import asyncio
import bitstruct
import struct
import csv

from bleak import BleakClient
from datetime import datetime

HR_MEAS = "00002A37-0000-1000-8000-00805F9B34FB"


async def run(address):
    with open("hr_export.csv", "a", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)

        async with BleakClient(address, timeout=20, winrt={"use_cached_services": False}) as client:
            print(f"Connected: {client.is_connected}")

            def hr_val_handler(sender, data):
                print(f"HR Measurement raw = {sender}: {data}")

                (
                    rr_int,
                    nrg_expnd,
                    snsr_cntct_spprtd,
                    snsr_detect,
                    hr_fmt,
                ) = bitstruct.unpack("p3b1b1b1b1b1<", data)

                if hr_fmt:
                    hr_val, = struct.unpack_from("<H", data, 1)
                    offset = 3
                else:
                    hr_val, = struct.unpack_from("<B", data, 1)
                    offset = 2

                print(f"HR Value: {hr_val}")

                if rr_int:
                    rr_raw, = struct.unpack_from("<H", data, offset)

                    # Bluetooth HR szabvány szerint 1/1024 s
                    rr_ms = rr_raw * 1000.0 / 1024.0

                    print(f"RR Value: {rr_ms:.1f} ms")
                    print(f"Instant HR: {60000.0 / rr_ms:.2f} bpm")

                    csvwriter.writerow([
                        int(datetime.now().timestamp()),
                        rr_ms,
                        hr_val
                    ])
                    csvfile.flush()

            await client.start_notify(HR_MEAS, hr_val_handler)

            while client.is_connected:
                await asyncio.sleep(0.5)

            print("Disconnected")


if __name__ == "__main__":
    address = "24:AC:AC:04:68:1E"

    asyncio.run(run(address))