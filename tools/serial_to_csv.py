#!/usr/bin/env python3
"""Read ESP32 serial output and log parsed telemetry lines to CSV."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import sys
import time

try:
    import serial
except ImportError:
    print("Missing dependency: pyserial. Install with: pip install pyserial", file=sys.stderr)
    sys.exit(1)


TELEMETRY_RE = re.compile(
    r"Rawtemp\s+([-+]?\d*\.?\d+)\D+"
    r"Temp:\s*([-+]?\d*\.?\d+)\D+"
    r"Smooth:\s*([-+]?\d*\.?\d+)\D+"
    r"PWM:\s*([-+]?\d+)\D+"
    r"(?:BIAS:\s*([-+]?\d*\.?\d+)\D+)?"
    r"(?:SPBIAS:\s*([-+]?\d*\.?\d+)\D+)?"
    r"SP:\s*([-+]?\d*\.?\d+)\D+"
    r"(?:EFFSP:\s*([-+]?\d*\.?\d+)\D+)?"
    r"FAN:\s*([-+]?\d*\.?\d+)\D+"
    r"FANPWM:\s*([-+]?\d+)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read ESP32 serial output and write parsed data to CSV."
    )
    parser.add_argument("--port", required=True, help="Serial port, e.g. COM5")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path (default: logs/serial_YYYYMMDD_HHMMSS.csv)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=1.0,
        help="Serial read timeout in seconds (default: 1.0)",
    )
    return parser.parse_args()


def default_output_path() -> str:
    os.makedirs("logs", exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join("logs", f"serial_{stamp}.csv")


def ensure_header(path: str, fieldnames: list[str]) -> None:
    is_new = not os.path.exists(path) or os.path.getsize(path) == 0
    if is_new:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def main() -> int:
    args = parse_args()
    output_path = args.output or default_output_path()

    fieldnames = [
        "timestamp_iso",
        "elapsed_s",
        "raw_temp_c",
        "temp_filtered_c",
        "temp_smooth_c",
        "pwm",
        "pid_bias",
        "setpoint_bias_c",
        "setpoint_c",
        "effective_setpoint_c",
        "fan_speed_pct",
        "fan_pwm_raw",
    ]
    ensure_header(output_path, fieldnames)

    start = time.time()
    rows_written = 0

    try:
        with serial.Serial(args.port, args.baud, timeout=args.timeout) as ser, open(
            output_path, "a", newline="", encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            print(f"Listening on {args.port} @ {args.baud} baud")
            print(f"Writing CSV to: {output_path}")
            print("Press Ctrl+C to stop.")

            while True:
                line = ser.readline().decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                match = TELEMETRY_RE.search(line)
                if not match:
                    continue

                now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="milliseconds")
                row = {
                    "timestamp_iso": now,
                    "elapsed_s": f"{time.time() - start:.3f}",
                    "raw_temp_c": float(match.group(1)),
                    "temp_filtered_c": float(match.group(2)),
                    "temp_smooth_c": float(match.group(3)),
                    "pwm": int(match.group(4)),
                    "pid_bias": float(match.group(5) or 0.0),
                    "setpoint_bias_c": float(match.group(6) or 0.0),
                    "setpoint_c": float(match.group(7)),
                    "effective_setpoint_c": float(match.group(8) or (float(match.group(7)) + float(match.group(6) or 0.0))),
                    "fan_speed_pct": float(match.group(9)),
                    "fan_pwm_raw": int(match.group(10)),
                }
                writer.writerow(row)
                f.flush()
                rows_written += 1

                print(
                    f"{rows_written:>6} | "
                    f"T={row['temp_filtered_c']:.2f} C "
                    f"Smooth={row['temp_smooth_c']:.2f} C "
                    f"PWM={row['pwm']} "
                    f"Bias={row['pid_bias']:.2f} "
                    f"SPBias={row['setpoint_bias_c']:.2f} "
                    f"Fan={row['fan_speed_pct']:.1f}% "
                    f"FanPWM={row['fan_pwm_raw']}"
                )

    except KeyboardInterrupt:
        print(f"\nStopped. Wrote {rows_written} rows to {output_path}")
        return 0
    except serial.SerialException as exc:
        print(f"Serial error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
