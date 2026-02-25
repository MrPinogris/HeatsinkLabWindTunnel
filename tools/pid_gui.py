#!/usr/bin/env python3
"""Simple GUI to tune ESP32 PID parameters over serial."""

from __future__ import annotations

import queue
import re
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import serial
from serial import SerialException
from serial.tools import list_ports

TELEMETRY_RE = re.compile(
    r"Rawtemp\s+([-+]?\d*\.?\d+)\D+"
    r"Temp:\s*([-+]?\d*\.?\d+)\D+"
    r"Smooth:\s*([-+]?\d*\.?\d+)\D+"
    r"PWM:\s*([-+]?\d+)\D+"
    r"SP:\s*([-+]?\d*\.?\d+)"
)
CFG_RE = re.compile(
    r"CFG\s+KP:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"KI:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"KD:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"SP:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"ALPHA:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"MAXSTEP:\s*([-+]?\d+)"
)


class PIDGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("HeatsinkLab PID Tuner")
        self.root.geometry("760x520")

        self.serial_conn: serial.Serial | None = None
        self.reader_thread: threading.Thread | None = None
        self.reader_stop = threading.Event()
        self.msg_queue: queue.Queue[tuple[str, str]] = queue.Queue()

        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar(value="115200")
        self.status_var = tk.StringVar(value="Disconnected")

        self.kp_var = tk.StringVar(value="12.0")
        self.ki_var = tk.StringVar(value="0.6")
        self.kd_var = tk.StringVar(value="0.0")
        self.sp_var = tk.StringVar(value="70.0")
        self.alpha_var = tk.StringVar(value="0.25")
        self.maxstep_var = tk.StringVar(value="15")

        self.raw_temp_var = tk.StringVar(value="-")
        self.temp_var = tk.StringVar(value="-")
        self.smooth_var = tk.StringVar(value="-")
        self.pwm_var = tk.StringVar(value="-")

        self._build_ui()
        self._refresh_ports()
        self.root.after(100, self._drain_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Port").grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.port_combo = ttk.Combobox(top, textvariable=self.port_var, width=20, state="readonly")
        self.port_combo.grid(row=0, column=1, padx=(0, 8), sticky="w")

        ttk.Button(top, text="Refresh", command=self._refresh_ports).grid(row=0, column=2, padx=(0, 12))

        ttk.Label(top, text="Baud").grid(row=0, column=3, padx=(0, 6), sticky="w")
        ttk.Entry(top, textvariable=self.baud_var, width=10).grid(row=0, column=4, padx=(0, 12), sticky="w")

        ttk.Button(top, text="Connect", command=self._connect).grid(row=0, column=5, padx=(0, 6))
        ttk.Button(top, text="Disconnect", command=self._disconnect).grid(row=0, column=6, padx=(0, 12))
        ttk.Label(top, textvariable=self.status_var).grid(row=0, column=7, sticky="w")

        param_frame = ttk.LabelFrame(self.root, text="Controller Parameters", padding=10)
        param_frame.pack(fill="x", padx=10, pady=(0, 10))

        self._param_row(param_frame, 0, "KP", self.kp_var)
        self._param_row(param_frame, 1, "KI", self.ki_var)
        self._param_row(param_frame, 2, "KD", self.kd_var)
        self._param_row(param_frame, 3, "SP", self.sp_var)
        self._param_row(param_frame, 4, "ALPHA", self.alpha_var)
        self._param_row(param_frame, 5, "MAXSTEP", self.maxstep_var)

        btns = ttk.Frame(param_frame)
        btns.grid(row=6, column=0, columnspan=3, pady=(8, 0), sticky="w")
        ttk.Button(btns, text="Apply All", command=self._apply_all).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Get From ESP32", command=self._request_get).pack(side="left")

        live = ttk.LabelFrame(self.root, text="Live Telemetry", padding=10)
        live.pack(fill="x", padx=10, pady=(0, 10))

        self._live_row(live, 0, "Raw Temp [C]", self.raw_temp_var)
        self._live_row(live, 1, "Filtered Temp [C]", self.temp_var)
        self._live_row(live, 2, "Smoothed Temp [C]", self.smooth_var)
        self._live_row(live, 3, "PWM", self.pwm_var)

        log_frame = ttk.LabelFrame(self.root, text="Serial Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log_text = tk.Text(log_frame, wrap="word", height=12)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _param_row(self, parent: ttk.Frame, row: int, name: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=name, width=10).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(parent, textvariable=variable, width=18).grid(row=row, column=1, sticky="w", pady=2)
        ttk.Button(parent, text=f"Set {name}", command=lambda: self._set_param(name, variable)).grid(
            row=row, column=2, sticky="w", padx=(8, 0), pady=2
        )

    def _live_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label, width=20).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Label(parent, textvariable=variable).grid(row=row, column=1, sticky="w", pady=2)

    def _refresh_ports(self) -> None:
        ports = [p.device for p in list_ports.comports()]
        self.port_combo["values"] = ports
        if ports and self.port_var.get() not in ports:
            self.port_var.set(ports[0])

    def _connect(self) -> None:
        if self.serial_conn and self.serial_conn.is_open:
            return

        port = self.port_var.get().strip()
        if not port:
            messagebox.showerror("No Port", "Select a serial port first.")
            return

        try:
            baud = int(self.baud_var.get().strip())
            self.serial_conn = serial.Serial(port, baudrate=baud, timeout=0.2)
            self.reader_stop.clear()
            self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self.reader_thread.start()
            self.status_var.set(f"Connected: {port} @ {baud}")
            self._append_log(f"Connected to {port} @ {baud}")
            self._request_get()
        except (ValueError, SerialException) as exc:
            self.serial_conn = None
            messagebox.showerror("Connect Failed", str(exc))

    def _disconnect(self) -> None:
        self.reader_stop.set()
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except SerialException:
                pass
        self.serial_conn = None
        self.status_var.set("Disconnected")
        self._append_log("Disconnected")

    def _on_close(self) -> None:
        self._disconnect()
        self.root.destroy()

    def _send_command(self, command: str) -> None:
        if not self.serial_conn or not self.serial_conn.is_open:
            messagebox.showerror("Not Connected", "Connect to ESP32 first.")
            return
        try:
            self.serial_conn.write((command + "\n").encode("utf-8"))
            self._append_log(f"> {command}")
        except SerialException as exc:
            self._append_log(f"Write error: {exc}")
            self._disconnect()

    def _set_param(self, key: str, variable: tk.StringVar) -> None:
        value = variable.get().strip()
        if not value:
            messagebox.showerror("Missing Value", f"Enter a value for {key}.")
            return
        self._send_command(f"SET {key} {value}")

    def _apply_all(self) -> None:
        self._set_param("KP", self.kp_var)
        self._set_param("KI", self.ki_var)
        self._set_param("KD", self.kd_var)
        self._set_param("SP", self.sp_var)
        self._set_param("ALPHA", self.alpha_var)
        self._set_param("MAXSTEP", self.maxstep_var)

    def _request_get(self) -> None:
        self._send_command("GET")

    def _reader_loop(self) -> None:
        while not self.reader_stop.is_set():
            if not self.serial_conn:
                break
            try:
                line = self.serial_conn.readline().decode("utf-8", errors="replace").strip()
            except SerialException as exc:
                self.msg_queue.put(("log", f"Serial read error: {exc}"))
                self.msg_queue.put(("disconnect", ""))
                break

            if not line:
                continue

            self.msg_queue.put(("line", line))

    def _drain_queue(self) -> None:
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "disconnect":
                    self._disconnect()
                    continue
                if kind == "log":
                    self._append_log(payload)
                    continue
                self._handle_line(payload)
        except queue.Empty:
            pass
        self.root.after(100, self._drain_queue)

    def _handle_line(self, line: str) -> None:
        self._append_log(line)

        telemetry = TELEMETRY_RE.search(line)
        if telemetry:
            self.raw_temp_var.set(f"{float(telemetry.group(1)):.2f}")
            self.temp_var.set(f"{float(telemetry.group(2)):.2f}")
            self.smooth_var.set(f"{float(telemetry.group(3)):.2f}")
            self.pwm_var.set(telemetry.group(4))
            return

        cfg = CFG_RE.search(line)
        if cfg:
            self.kp_var.set(cfg.group(1))
            self.ki_var.set(cfg.group(2))
            self.kd_var.set(cfg.group(3))
            self.sp_var.set(cfg.group(4))
            self.alpha_var.set(cfg.group(5))
            self.maxstep_var.set(cfg.group(6))

    def _append_log(self, text: str) -> None:
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")


def main() -> None:
    root = tk.Tk()
    ttk.Style(root).theme_use("clam")
    PIDGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
