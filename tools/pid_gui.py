#!/usr/bin/env python3
"""GUI to tune ESP32 PID parameters, monitor telemetry, and plot live data."""

from __future__ import annotations

import json
import csv
import queue
import re
import threading
import tkinter as tk
import time
import datetime as dt
from pathlib import Path
from tkinter import messagebox, ttk

import serial
from serial import SerialException
from serial.tools import list_ports

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk  # type: ignore[import-not-found]
    from matplotlib.figure import Figure
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: matplotlib. Install with: pip install matplotlib"
    ) from exc


TELEMETRY_RE = re.compile(
    r"Rawtemp\s+([-+]?\d*\.?\d+)\D+"
    r"Temp:\s*([-+]?\d*\.?\d+)\D+"
    r"Smooth:\s*([-+]?\d*\.?\d+)\D+"
    r"PWM:\s*([-+]?\d+)\D+"
    r"(?:P:\s*([-+]?\d*\.?\d+)\D+)?"
    r"(?:I:\s*([-+]?\d*\.?\d+)\D+)?"
    r"(?:D:\s*([-+]?\d*\.?\d+)\D+)?"
    r"(?:OUT:\s*([-+]?\d*\.?\d+)\D+)?"
    r"(?:BIAS:\s*([-+]?\d*\.?\d+)\D+)?"
    r"(?:SPBIAS:\s*([-+]?\d*\.?\d+)\D+)?"
    r"SP:\s*([-+]?\d*\.?\d+)\D+"
    r"(?:EFFSP:\s*([-+]?\d*\.?\d+)\D+)?"
    r"FAN:\s*([-+]?\d*\.?\d+)\D+"
    r"FANPWM:\s*([-+]?\d+)"
    r"(?:\D+MODE:\s*(AUTO|MANUAL|SMART)\D+STATE:\s*(PID|HOLD|MANUAL)\D+MANPWM:\s*([-+]?\d*\.?\d+)\D+HOLDPWM:\s*([-+]?\d*\.?\d+)\D+ENTPROG:\s*([-+]?\d*\.?\d+)\D+EXTPROG:\s*([-+]?\d*\.?\d+)\D+EABS:\s*([-+]?\d*\.?\d+))?"
    r"(?:\D+RUN:\s*(ON|OFF)\D+FANINV:\s*([01]))?"
)
CFG_RE = re.compile(
    r"CFG\s+KP:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"KI:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"KD:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"BIAS:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"SPBIAS:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"SP:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"ALPHA:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"MAXSTEP:\s*([-+]?\d+)\s*\|\s*"
    r"ENTCNT:\s*([-+]?\d+)\s*\|\s*"
    r"EXTCNT:\s*([-+]?\d+)\s*\|\s*"
    r"FAN:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"FANINV:\s*([01])\s*\|\s*"
    r"MODE:\s*(AUTO|MANUAL|SMART)\s*\|\s*"
    r"MANPWM:\s*([-+]?\d*\.?\d+)\s*\|\s*"
    r"RUN:\s*(ON|OFF)"
)


class PIDGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("HeatsinkLab PID Tuner")
        self.root.geometry("1200x860")

        self.serial_conn: serial.Serial | None = None
        self.reader_thread: threading.Thread | None = None
        self.reader_stop = threading.Event()
        self.msg_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.max_queue_items = 2000
        self.max_log_lines = 1500
        self.state_path = Path(__file__).with_name("pid_gui_state.json")
        self.saved_state = self._load_state()

        self.port_var = tk.StringVar()
        self.baud_var = tk.StringVar(value="115200")
        self.status_var = tk.StringVar(value="Disconnected")
        self.csv_status_var = tk.StringVar(value="CSV: Off")

        self.kp_var = tk.StringVar(value=self._state_value("kp", "8.0"))
        self.ki_var = tk.StringVar(value=self._state_value("ki", "0.06"))
        self.kd_var = tk.StringVar(value=self._state_value("kd", "0.0"))
        self.bias_var = tk.StringVar(value=self._state_value("bias", "0.0"))
        self.spbias_var = tk.StringVar(value=self._state_value("spbias", "0.0"))
        self.sp_var = tk.StringVar(value=self._state_value("sp", "70.0"))
        self.alpha_var = tk.StringVar(value=self._state_value("alpha", "0.25"))
        self.maxstep_var = tk.StringVar(value=self._state_value("maxstep", "15"))
        self.entercnt_var = tk.StringVar(value=self._state_value("entercnt", "16"))
        self.exitcnt_var = tk.StringVar(value=self._state_value("exitcnt", "8"))
        self.fan_var = tk.StringVar(value=self._state_value("fan", "0"))
        self.manpwm_var = tk.StringVar(value=self._state_value("manpwm", "0.0"))
        self.ctrl_mode_var = tk.StringVar(value=self._state_value("ctrl_mode", "AUTO"))
        self.fan_inv_var = tk.BooleanVar(value=self._state_value("fan_inv", "0") in {"1", "true", "True"})
        self.spbias_slider_var = tk.DoubleVar(value=0.0)
        self.sp_slider_var = tk.DoubleVar(value=0.0)
        self.alpha_slider_var = tk.DoubleVar(value=0.0)
        self.maxstep_slider_var = tk.DoubleVar(value=0.0)
        self.entercnt_slider_var = tk.DoubleVar(value=0.0)
        self.exitcnt_slider_var = tk.DoubleVar(value=0.0)
        self.fan_slider_var = tk.DoubleVar(value=0.0)
        self.manpwm_slider_var = tk.DoubleVar(value=0.0)

        self.raw_temp_var = tk.StringVar(value="-")
        self.temp_var = tk.StringVar(value="-")
        self.smooth_var = tk.StringVar(value="-")
        self.bias_live_var = tk.StringVar(value="-")
        self.spbias_live_var = tk.StringVar(value="-")
        self.sp_live_var = tk.StringVar(value="-")
        self.effsp_live_var = tk.StringVar(value="-")
        self.pwm_var = tk.StringVar(value="-")
        self.p_term_var = tk.StringVar(value="-")
        self.i_term_var = tk.StringVar(value="-")
        self.d_term_var = tk.StringVar(value="-")
        self.out_var = tk.StringVar(value="-")
        self.fan_speed_var = tk.StringVar(value="-")
        self.fan_pwm_var = tk.StringVar(value="-")
        self.mode_live_var = tk.StringVar(value="-")
        self.state_live_var = tk.StringVar(value="-")
        self.manpwm_live_var = tk.StringVar(value="-")
        self.holdpwm_live_var = tk.StringVar(value="-")
        self.enter_prog_live_var = tk.StringVar(value="-")
        self.exit_prog_live_var = tk.StringVar(value="-")
        self.abs_err_live_var = tk.StringVar(value="-")
        self.run_live_var = tk.StringVar(value="-")
        self.fan_inv_live_var = tk.StringVar(value="-")

        self.show_raw_var = tk.BooleanVar(value=True)
        self.show_temp_var = tk.BooleanVar(value=True)
        self.show_smooth_var = tk.BooleanVar(value=True)
        self.show_sp_var = tk.BooleanVar(value=True)
        self.show_pwm_var = tk.BooleanVar(value=True)
        self.show_fan_pwm_var = tk.BooleanVar(value=False)
        self.show_p_var = tk.BooleanVar(value=False)
        self.show_i_var = tk.BooleanVar(value=False)
        self.show_d_var = tk.BooleanVar(value=False)
        self.show_out_var = tk.BooleanVar(value=False)
        self.show_holdpwm_var = tk.BooleanVar(value=False)
        self.show_enter_prog_var = tk.BooleanVar(value=False)
        self.show_exit_prog_var = tk.BooleanVar(value=False)

        self.mode_var = tk.StringVar(value="rolling")
        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.window_seconds_var = tk.StringVar(value="120")
        self.max_points_var = tk.StringVar(value="5000")
        self.offset_var = tk.DoubleVar(value=0.0)
        self.temp_auto_y_var = tk.BooleanVar(value=self._state_value("temp_auto_y", "1") in {"1", "true", "True"})
        self.temp_ymin_var = tk.StringVar(value=self._state_value("temp_ymin", "0"))
        self.temp_ymax_var = tk.StringVar(value=self._state_value("temp_ymax", "120"))
        self.pwm_auto_y_var = tk.BooleanVar(value=self._state_value("pwm_auto_y", "0") in {"1", "true", "True"})
        self.pwm_ymin_var = tk.StringVar(value=self._state_value("pwm_ymin", "0"))
        self.pwm_ymax_var = tk.StringVar(value=self._state_value("pwm_ymax", "255"))

        self.times: list[float] = []
        self.raw_values: list[float] = []
        self.temp_values: list[float] = []
        self.smooth_values: list[float] = []
        self.sp_values: list[float] = []
        self.pwm_values: list[float] = []
        self.p_term_values: list[float] = []
        self.i_term_values: list[float] = []
        self.d_term_values: list[float] = []
        self.out_values: list[float] = []
        self.holdpwm_values: list[float] = []
        self.enter_prog_values: list[float] = []
        self.exit_prog_values: list[float] = []
        self.fan_pwm_values: list[float] = []

        self.plot_dirty = False
        self.awaiting_handshake = False
        self.handshake_deadline = 0.0
        self.handshake_ok = False
        self.csv_logging_enabled = False
        self.csv_file = None
        self.csv_writer = None
        self.csv_path: Path | None = None
        self.csv_start_monotonic = 0.0

        self._build_ui()
        self._sync_slider_from_entry("SPBIAS")
        self._sync_slider_from_entry("SP")
        self._sync_slider_from_entry("ALPHA")
        self._sync_slider_from_entry("MAXSTEP")
        self._sync_slider_from_entry("ENTERCNT")
        self._sync_slider_from_entry("EXITCNT")
        self._sync_slider_from_entry("FAN")
        self._sync_slider_from_entry("MANPWM")
        self._refresh_ports()
        self._bind_scroll_handlers()

        self.root.after(100, self._drain_queue)
        self.root.after(250, self._refresh_plot_if_needed)
        self.root.after(300, self._check_handshake)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _state_value(self, key: str, default: str) -> str:
        value = self.saved_state.get(key, default)
        return str(value)

    def _load_state(self) -> dict[str, str]:
        if not self.state_path.exists():
            return {}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except (OSError, json.JSONDecodeError):
            pass
        return {}

    def _save_state(self) -> None:
        state = {
            "kp": self.kp_var.get().strip(),
            "ki": self.ki_var.get().strip(),
            "kd": self.kd_var.get().strip(),
            "bias": self.bias_var.get().strip(),
            "spbias": self.spbias_var.get().strip(),
            "sp": self.sp_var.get().strip(),
            "alpha": self.alpha_var.get().strip(),
            "maxstep": self.maxstep_var.get().strip(),
            "entercnt": self.entercnt_var.get().strip(),
            "exitcnt": self.exitcnt_var.get().strip(),
            "fan": self.fan_var.get().strip(),
            "manpwm": self.manpwm_var.get().strip(),
            "ctrl_mode": self.ctrl_mode_var.get().strip(),
            "fan_inv": "1" if self.fan_inv_var.get() else "0",
            "temp_auto_y": "1" if self.temp_auto_y_var.get() else "0",
            "temp_ymin": self.temp_ymin_var.get().strip(),
            "temp_ymax": self.temp_ymax_var.get().strip(),
            "pwm_auto_y": "1" if self.pwm_auto_y_var.get() else "0",
            "pwm_ymin": self.pwm_ymin_var.get().strip(),
            "pwm_ymax": self.pwm_ymax_var.get().strip(),
        }
        try:
            self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root)
        outer.pack(fill="both", expand=True)

        self.main_canvas = tk.Canvas(outer, highlightthickness=0)
        self.main_canvas.pack(side="left", fill="both", expand=True)

        vbar = ttk.Scrollbar(outer, orient="vertical", command=self.main_canvas.yview)
        vbar.pack(side="right", fill="y")
        hbar = ttk.Scrollbar(self.root, orient="horizontal", command=self.main_canvas.xview)
        hbar.pack(fill="x")

        self.main_canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        self.content = ttk.Frame(self.main_canvas, padding=10)
        self.canvas_window = self.main_canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._on_content_configure)
        self.main_canvas.bind("<Configure>", self._on_canvas_configure)

        top = ttk.Frame(self.content, padding=2)
        top.pack(fill="x")

        ttk.Label(top, text="Port").grid(row=0, column=0, padx=(0, 6), sticky="w")
        self.port_combo = ttk.Combobox(top, textvariable=self.port_var, width=20, state="readonly")
        self.port_combo.grid(row=0, column=1, padx=(0, 8), sticky="w")

        ttk.Button(top, text="Refresh", command=self._refresh_ports).grid(row=0, column=2, padx=(0, 12))

        ttk.Label(top, text="Baud").grid(row=0, column=3, padx=(0, 6), sticky="w")
        ttk.Entry(top, textvariable=self.baud_var, width=10).grid(row=0, column=4, padx=(0, 12), sticky="w")

        ttk.Button(top, text="Connect", command=self._connect).grid(row=0, column=5, padx=(0, 6))
        ttk.Button(top, text="Disconnect", command=self._disconnect).grid(row=0, column=6, padx=(0, 10))
        ttk.Label(top, textvariable=self.status_var).grid(row=0, column=7, sticky="w")

        ttk.Button(top, text="Start CSV", command=self._start_csv_logging).grid(row=1, column=5, padx=(0, 6), pady=(6, 0))
        ttk.Button(top, text="Stop CSV", command=self._stop_csv_logging).grid(row=1, column=6, padx=(0, 10), pady=(6, 0))
        ttk.Label(top, textvariable=self.csv_status_var).grid(row=1, column=7, sticky="w", pady=(6, 0))

        param_frame = ttk.LabelFrame(self.content, text="Controller Parameters", padding=10)
        param_frame.pack(fill="x", pady=(8, 8))
        param_frame.columnconfigure(3, weight=1)

        self._param_row(param_frame, 0, "KP", self.kp_var)
        self._param_row(param_frame, 1, "KI", self.ki_var)
        self._param_row(param_frame, 2, "KD", self.kd_var)
        self._param_row(param_frame, 3, "BIAS", self.bias_var)

        ttk.Label(param_frame, text="SPBIAS", width=10).grid(row=4, column=0, sticky="w", pady=2)
        spbias_entry = ttk.Entry(param_frame, textvariable=self.spbias_var, width=18)
        spbias_entry.grid(row=4, column=1, sticky="w", pady=2)
        spbias_entry.bind("<Return>", lambda _e: self._sync_slider_from_entry("SPBIAS"))
        spbias_entry.bind("<FocusOut>", lambda _e: self._sync_slider_from_entry("SPBIAS"))
        ttk.Button(param_frame, text="Set SPBIAS", command=lambda: self._set_param("SPBIAS", self.spbias_var)).grid(
            row=4, column=2, sticky="w", padx=(8, 0), pady=2
        )
        ttk.Scale(param_frame, from_=-200.0, to=200.0, variable=self.spbias_slider_var, command=self._on_spbias_slider).grid(
            row=4, column=3, sticky="ew", padx=(8, 0), pady=2
        )

        ttk.Label(param_frame, text="SP", width=10).grid(row=5, column=0, sticky="w", pady=2)
        sp_entry = ttk.Entry(param_frame, textvariable=self.sp_var, width=18)
        sp_entry.grid(row=5, column=1, sticky="w", pady=2)
        sp_entry.bind("<Return>", lambda _e: self._sync_slider_from_entry("SP"))
        sp_entry.bind("<FocusOut>", lambda _e: self._sync_slider_from_entry("SP"))
        ttk.Button(param_frame, text="Set SP", command=lambda: self._set_param("SP", self.sp_var)).grid(
            row=5, column=2, sticky="w", padx=(8, 0), pady=2
        )
        ttk.Scale(param_frame, from_=-20.0, to=400.0, variable=self.sp_slider_var, command=self._on_sp_slider).grid(
            row=5, column=3, sticky="ew", padx=(8, 0), pady=2
        )

        ttk.Label(param_frame, text="ALPHA", width=10).grid(row=6, column=0, sticky="w", pady=2)
        alpha_entry = ttk.Entry(param_frame, textvariable=self.alpha_var, width=18)
        alpha_entry.grid(row=6, column=1, sticky="w", pady=2)
        alpha_entry.bind("<Return>", lambda _e: self._sync_slider_from_entry("ALPHA"))
        alpha_entry.bind("<FocusOut>", lambda _e: self._sync_slider_from_entry("ALPHA"))
        ttk.Button(param_frame, text="Set ALPHA", command=lambda: self._set_param("ALPHA", self.alpha_var)).grid(
            row=6, column=2, sticky="w", padx=(8, 0), pady=2
        )
        ttk.Scale(param_frame, from_=0.001, to=1.0, variable=self.alpha_slider_var, command=self._on_alpha_slider).grid(
            row=6, column=3, sticky="ew", padx=(8, 0), pady=2
        )

        ttk.Label(param_frame, text="MAXSTEP", width=10).grid(row=7, column=0, sticky="w", pady=2)
        maxstep_entry = ttk.Entry(param_frame, textvariable=self.maxstep_var, width=18)
        maxstep_entry.grid(row=7, column=1, sticky="w", pady=2)
        maxstep_entry.bind("<Return>", lambda _e: self._sync_slider_from_entry("MAXSTEP"))
        maxstep_entry.bind("<FocusOut>", lambda _e: self._sync_slider_from_entry("MAXSTEP"))
        ttk.Button(param_frame, text="Set MAXSTEP", command=lambda: self._set_param("MAXSTEP", self.maxstep_var)).grid(
            row=7, column=2, sticky="w", padx=(8, 0), pady=2
        )
        ttk.Scale(param_frame, from_=0.0, to=255.0, variable=self.maxstep_slider_var, command=self._on_maxstep_slider).grid(
            row=7, column=3, sticky="ew", padx=(8, 0), pady=2
        )

        ttk.Label(param_frame, text="ENTERCNT", width=10).grid(row=8, column=0, sticky="w", pady=2)
        entercnt_entry = ttk.Entry(param_frame, textvariable=self.entercnt_var, width=18)
        entercnt_entry.grid(row=8, column=1, sticky="w", pady=2)
        entercnt_entry.bind("<Return>", lambda _e: self._sync_slider_from_entry("ENTERCNT"))
        entercnt_entry.bind("<FocusOut>", lambda _e: self._sync_slider_from_entry("ENTERCNT"))
        ttk.Button(param_frame, text="Set ENTERCNT", command=lambda: self._set_param("ENTERCNT", self.entercnt_var)).grid(
            row=8, column=2, sticky="w", padx=(8, 0), pady=2
        )
        ttk.Scale(param_frame, from_=1.0, to=400.0, variable=self.entercnt_slider_var, command=self._on_entercnt_slider).grid(
            row=8, column=3, sticky="ew", padx=(8, 0), pady=2
        )

        ttk.Label(param_frame, text="EXITCNT", width=10).grid(row=9, column=0, sticky="w", pady=2)
        exitcnt_entry = ttk.Entry(param_frame, textvariable=self.exitcnt_var, width=18)
        exitcnt_entry.grid(row=9, column=1, sticky="w", pady=2)
        exitcnt_entry.bind("<Return>", lambda _e: self._sync_slider_from_entry("EXITCNT"))
        exitcnt_entry.bind("<FocusOut>", lambda _e: self._sync_slider_from_entry("EXITCNT"))
        ttk.Button(param_frame, text="Set EXITCNT", command=lambda: self._set_param("EXITCNT", self.exitcnt_var)).grid(
            row=9, column=2, sticky="w", padx=(8, 0), pady=2
        )
        ttk.Scale(param_frame, from_=1.0, to=400.0, variable=self.exitcnt_slider_var, command=self._on_exitcnt_slider).grid(
            row=9, column=3, sticky="ew", padx=(8, 0), pady=2
        )
        ttk.Label(param_frame, text="FAN", width=10).grid(row=10, column=0, sticky="w", pady=2)
        fan_entry = ttk.Entry(param_frame, textvariable=self.fan_var, width=18)
        fan_entry.grid(row=10, column=1, sticky="w", pady=2)
        fan_entry.bind("<Return>", lambda _e: self._sync_slider_from_entry("FAN"))
        fan_entry.bind("<FocusOut>", lambda _e: self._sync_slider_from_entry("FAN"))
        ttk.Button(param_frame, text="Set FAN", command=lambda: self._set_param("FAN", self.fan_var)).grid(
            row=10, column=2, sticky="w", padx=(8, 0), pady=2
        )
        ttk.Scale(param_frame, from_=0.0, to=100.0, variable=self.fan_slider_var, command=self._on_fan_slider).grid(
            row=10, column=3, sticky="ew", padx=(8, 0), pady=2
        )

        ttk.Label(param_frame, text="MANPWM", width=10).grid(row=11, column=0, sticky="w", pady=2)
        manpwm_entry = ttk.Entry(param_frame, textvariable=self.manpwm_var, width=18)
        manpwm_entry.grid(row=11, column=1, sticky="w", pady=2)
        manpwm_entry.bind("<Return>", lambda _e: self._sync_slider_from_entry("MANPWM"))
        manpwm_entry.bind("<FocusOut>", lambda _e: self._sync_slider_from_entry("MANPWM"))
        ttk.Button(param_frame, text="Set MANPWM", command=lambda: self._set_param("MANPWM", self.manpwm_var)).grid(
            row=11, column=2, sticky="w", padx=(8, 0), pady=2
        )
        ttk.Scale(param_frame, from_=0.0, to=255.0, variable=self.manpwm_slider_var, command=self._on_manpwm_slider).grid(
            row=11, column=3, sticky="ew", padx=(8, 0), pady=2
        )

        mode_row = ttk.Frame(param_frame)
        mode_row.grid(row=12, column=0, columnspan=3, sticky="w", pady=(4, 2))
        ttk.Label(mode_row, text="MODE", width=10).pack(side="left")
        ttk.Radiobutton(mode_row, text="AUTO", value="AUTO", variable=self.ctrl_mode_var).pack(side="left")
        ttk.Radiobutton(mode_row, text="MANUAL", value="MANUAL", variable=self.ctrl_mode_var).pack(side="left", padx=(8, 0))
        ttk.Radiobutton(mode_row, text="SMART", value="SMART", variable=self.ctrl_mode_var).pack(side="left", padx=(8, 0))
        ttk.Button(mode_row, text="Set MODE", command=self._set_mode).pack(side="left", padx=(10, 0))

        safety_row = ttk.Frame(param_frame)
        safety_row.grid(row=13, column=0, columnspan=3, sticky="w", pady=(2, 2))
        ttk.Checkbutton(safety_row, text="Fan PWM Inverted", variable=self.fan_inv_var).pack(side="left")
        ttk.Button(safety_row, text="Apply FANINV", command=self._set_fan_inversion).pack(side="left", padx=(8, 0))
        ttk.Button(safety_row, text="Start Heater", command=self._run_on).pack(side="left", padx=(14, 0))
        ttk.Button(safety_row, text="Stop Heater", command=self._run_off).pack(side="left", padx=(6, 0))

        param_buttons = ttk.Frame(param_frame)
        param_buttons.grid(row=14, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(param_buttons, text="Apply All", command=self._apply_all).pack(side="left", padx=(0, 8))
        ttk.Button(param_buttons, text="Get From ESP32", command=self._request_get).pack(side="left")

        live = ttk.LabelFrame(self.content, text="Live Telemetry", padding=10)
        live.pack(fill="x", pady=(0, 8))

        self._live_row(live, 0, "Raw Temp [C]", self.raw_temp_var)
        self._live_row(live, 1, "Filtered Temp [C]", self.temp_var)
        self._live_row(live, 2, "Smoothed Temp [C]", self.smooth_var)
        self._live_row(live, 3, "Bias", self.bias_live_var)
        self._live_row(live, 4, "SP Bias [C]", self.spbias_live_var)
        self._live_row(live, 5, "Setpoint [C]", self.sp_live_var)
        self._live_row(live, 6, "Effective SP [C]", self.effsp_live_var)
        self._live_row(live, 7, "PWM", self.pwm_var)
        self._live_row(live, 8, "P Term", self.p_term_var)
        self._live_row(live, 9, "I Term", self.i_term_var)
        self._live_row(live, 10, "D Term", self.d_term_var)
        self._live_row(live, 11, "PID Output", self.out_var)
        self._live_row(live, 12, "Fan Speed [%]", self.fan_speed_var)
        self._live_row(live, 13, "Fan PWM Raw", self.fan_pwm_var)
        self._live_row(live, 14, "Controller Mode", self.mode_live_var)
        self._live_row(live, 15, "Controller State", self.state_live_var)
        self._live_row(live, 16, "Manual PWM Cmd", self.manpwm_live_var)
        self._live_row(live, 17, "Smart Hold PWM", self.holdpwm_live_var)
        self._live_row(live, 18, "Enter Progress [%]", self.enter_prog_live_var)
        self._live_row(live, 19, "Exit Progress [%]", self.exit_prog_live_var)
        self._live_row(live, 20, "Abs Error [C]", self.abs_err_live_var)
        self._live_row(live, 21, "Run State", self.run_live_var)
        self._live_row(live, 22, "Fan Inverted", self.fan_inv_live_var)

        plot_controls = ttk.LabelFrame(self.content, text="Plot Controls", padding=10)
        plot_controls.pack(fill="x", pady=(0, 8))

        series_frame = ttk.Frame(plot_controls)
        series_frame.grid(row=0, column=0, padx=(0, 20), sticky="nw")
        ttk.Label(series_frame, text="Visible series").pack(anchor="w")
        ttk.Checkbutton(series_frame, text="Raw Temp", variable=self.show_raw_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(series_frame, text="Temp", variable=self.show_temp_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(series_frame, text="Smooth", variable=self.show_smooth_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(series_frame, text="SP", variable=self.show_sp_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(series_frame, text="PWM", variable=self.show_pwm_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(series_frame, text="Fan PWM", variable=self.show_fan_pwm_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(series_frame, text="P term", variable=self.show_p_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(series_frame, text="I term", variable=self.show_i_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(series_frame, text="D term", variable=self.show_d_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(series_frame, text="PID out", variable=self.show_out_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(series_frame, text="Hold PWM", variable=self.show_holdpwm_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(series_frame, text="Enter %", variable=self.show_enter_prog_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(series_frame, text="Exit %", variable=self.show_exit_prog_var, command=self._mark_plot_dirty).pack(anchor="w")

        mode_frame = ttk.Frame(plot_controls)
        mode_frame.grid(row=0, column=1, padx=(0, 20), sticky="nw")
        ttk.Label(mode_frame, text="View mode").pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Rolling window", value="rolling", variable=self.mode_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Full history", value="full", variable=self.mode_var, command=self._mark_plot_dirty).pack(anchor="w")
        ttk.Checkbutton(mode_frame, text="Auto-scroll to newest", variable=self.auto_scroll_var, command=self._on_auto_scroll_toggle).pack(anchor="w")

        config_frame = ttk.Frame(plot_controls)
        config_frame.grid(row=0, column=2, sticky="nw")

        ttk.Label(config_frame, text="Window [s]").grid(row=0, column=0, sticky="w")
        ttk.Entry(config_frame, textvariable=self.window_seconds_var, width=10).grid(row=0, column=1, padx=(6, 0), sticky="w")

        ttk.Label(config_frame, text="History points").grid(row=1, column=0, pady=(4, 0), sticky="w")
        ttk.Entry(config_frame, textvariable=self.max_points_var, width=10).grid(row=1, column=1, padx=(6, 0), pady=(4, 0), sticky="w")

        action_row = ttk.Frame(config_frame)
        action_row.grid(row=2, column=0, columnspan=2, pady=(8, 0), sticky="w")
        ttk.Button(action_row, text="Apply View", command=self._apply_plot_config).pack(side="left", padx=(0, 6))
        ttk.Button(action_row, text="Clear Plot", command=self._clear_plot).pack(side="left")

        ttk.Checkbutton(config_frame, text="Auto Temp Y", variable=self.temp_auto_y_var).grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Label(config_frame, text="Temp Y min/max").grid(row=4, column=0, sticky="w")
        temp_y_row = ttk.Frame(config_frame)
        temp_y_row.grid(row=4, column=1, padx=(6, 0), sticky="w")
        ttk.Entry(temp_y_row, textvariable=self.temp_ymin_var, width=6).pack(side="left")
        ttk.Label(temp_y_row, text=" / ").pack(side="left")
        ttk.Entry(temp_y_row, textvariable=self.temp_ymax_var, width=6).pack(side="left")

        ttk.Checkbutton(config_frame, text="Auto PWM Y", variable=self.pwm_auto_y_var).grid(row=5, column=0, sticky="w", pady=(6, 0))
        ttk.Label(config_frame, text="PWM Y min/max").grid(row=6, column=0, sticky="w")
        pwm_y_row = ttk.Frame(config_frame)
        pwm_y_row.grid(row=6, column=1, padx=(6, 0), sticky="w")
        ttk.Entry(pwm_y_row, textvariable=self.pwm_ymin_var, width=6).pack(side="left")
        ttk.Label(pwm_y_row, text=" / ").pack(side="left")
        ttk.Entry(pwm_y_row, textvariable=self.pwm_ymax_var, width=6).pack(side="left")

        offset_wrap = ttk.Frame(plot_controls)
        offset_wrap.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        offset_wrap.columnconfigure(1, weight=1)
        ttk.Label(offset_wrap, text="History scroll").grid(row=0, column=0, sticky="w")
        self.offset_scale = ttk.Scale(offset_wrap, from_=0.0, to=0.0, variable=self.offset_var, command=self._on_offset_change)
        self.offset_scale.grid(row=0, column=1, padx=(8, 0), sticky="ew")

        plot_frame = ttk.LabelFrame(self.content, text="Live Graph", padding=10)
        plot_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.figure = Figure(figsize=(10.5, 4.8), dpi=100)
        self.ax_temp = self.figure.add_subplot(111)
        self.ax_pwm = self.ax_temp.twinx()

        self.canvas_plot = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas_plot.draw()
        self.canvas_plot.get_tk_widget().pack(fill="both", expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas_plot, plot_frame, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(fill="x")

        log_frame = ttk.LabelFrame(self.content, text="Serial Log", padding=10)
        log_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(log_frame, wrap="word", height=10)
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_scroll.set)

    def _bind_scroll_handlers(self) -> None:
        self.main_canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.main_canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mouse_wheel)

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        if event.delta == 0:
            return
        direction = -1 if event.delta > 0 else 1
        self.main_canvas.yview_scroll(direction, "units")

    def _on_shift_mouse_wheel(self, event: tk.Event) -> None:
        if event.delta == 0:
            return
        direction = -1 if event.delta > 0 else 1
        self.main_canvas.xview_scroll(direction, "units")

    def _on_content_configure(self, _event: tk.Event) -> None:
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.main_canvas.itemconfigure(self.canvas_window, width=max(event.width, 980))

    def _param_row(self, parent: tk.Widget, row: int, name: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=name, width=10).grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(parent, textvariable=variable, width=18).grid(row=row, column=1, sticky="w", pady=2)
        ttk.Button(parent, text=f"Set {name}", command=lambda: self._set_param(name, variable)).grid(
            row=row, column=2, sticky="w", padx=(8, 0), pady=2
        )

    def _live_row(self, parent: tk.Widget, row: int, label: str, variable: tk.StringVar) -> None:
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
            self.awaiting_handshake = True
            self.handshake_ok = False
            self.handshake_deadline = time.monotonic() + 2.5
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
        self.awaiting_handshake = False
        self.handshake_ok = False
        self.status_var.set("Disconnected")
        self._append_log("Disconnected")
        self._stop_csv_logging()

    def _on_close(self) -> None:
        self._save_state()
        self._stop_csv_logging()
        self._disconnect()
        self.main_canvas.unbind_all("<MouseWheel>")
        self.main_canvas.unbind_all("<Shift-MouseWheel>")
        self.root.destroy()

    def _default_csv_path(self) -> Path:
        logs_dir = Path(__file__).resolve().parents[1] / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        return logs_dir / f"serial_{stamp}.csv"

    def _start_csv_logging(self) -> None:
        if self.csv_logging_enabled:
            return

        if not self.serial_conn or not self.serial_conn.is_open:
            messagebox.showerror("Not Connected", "Connect to ESP32 before starting CSV logging.")
            return

        path = self._default_csv_path()
        fieldnames = [
            "timestamp_iso",
            "elapsed_s",
            "raw_temp_c",
            "temp_filtered_c",
            "temp_smooth_c",
            "pwm",
            "p_term",
            "i_term",
            "d_term",
            "pid_out",
            "pid_bias",
            "setpoint_bias_c",
            "setpoint_c",
            "effective_setpoint_c",
            "fan_speed_pct",
            "fan_pwm_raw",
            "mode",
            "state",
            "manual_pwm_cmd",
            "hold_pwm",
            "enter_progress_pct",
            "exit_progress_pct",
            "abs_error_c",
            "run_state",
            "fan_inverted",
        ]

        try:
            self.csv_file = open(path, "w", newline="", encoding="utf-8")
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
            self.csv_writer.writeheader()
            self.csv_file.flush()
        except OSError as exc:
            self.csv_file = None
            self.csv_writer = None
            messagebox.showerror("CSV Error", f"Could not open CSV file:\n{path}\n\n{exc}")
            return

        self.csv_path = path
        self.csv_start_monotonic = time.monotonic()
        self.csv_logging_enabled = True
        self.csv_status_var.set(f"CSV: On ({path.name})")
        self._append_log(f"CSV logging started: {path}")

    def _stop_csv_logging(self) -> None:
        if self.csv_file:
            try:
                self.csv_file.flush()
                self.csv_file.close()
            except OSError:
                pass
        if self.csv_logging_enabled and self.csv_path:
            self._append_log(f"CSV logging stopped: {self.csv_path}")
        self.csv_logging_enabled = False
        self.csv_file = None
        self.csv_writer = None
        self.csv_path = None
        self.csv_status_var.set("CSV: Off")

    def _write_csv_row(self, row: dict[str, object]) -> None:
        if not self.csv_logging_enabled or not self.csv_writer or not self.csv_file:
            return
        try:
            self.csv_writer.writerow(row)
            self.csv_file.flush()
        except OSError as exc:
            self._append_log(f"CSV write error: {exc}")
            self._stop_csv_logging()

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
        if key in {"SPBIAS", "SP", "ALPHA", "MAXSTEP", "ENTERCNT", "EXITCNT", "FAN", "MANPWM"}:
            self._sync_slider_from_entry(key)

        value = variable.get().strip()
        if not value:
            messagebox.showerror("Missing Value", f"Enter a value for {key}.")
            return
        self._save_state()
        self._send_command(f"SET {key} {value}")

    def _on_fan_slider(self, _value: str) -> None:
        self.fan_var.set(f"{self.fan_slider_var.get():.1f}")

    def _on_manpwm_slider(self, _value: str) -> None:
        self.manpwm_var.set(f"{self.manpwm_slider_var.get():.2f}")

    def _on_spbias_slider(self, _value: str) -> None:
        self.spbias_var.set(f"{self.spbias_slider_var.get():.2f}")

    def _on_sp_slider(self, _value: str) -> None:
        self.sp_var.set(f"{self.sp_slider_var.get():.2f}")

    def _on_alpha_slider(self, _value: str) -> None:
        self.alpha_var.set(f"{self.alpha_slider_var.get():.3f}")

    def _on_maxstep_slider(self, _value: str) -> None:
        self.maxstep_var.set(f"{int(round(self.maxstep_slider_var.get()))}")

    def _on_entercnt_slider(self, _value: str) -> None:
        self.entercnt_var.set(f"{int(round(self.entercnt_slider_var.get()))}")

    def _on_exitcnt_slider(self, _value: str) -> None:
        self.exitcnt_var.set(f"{int(round(self.exitcnt_slider_var.get()))}")

    def _sync_slider_from_entry(self, key: str) -> None:
        if key == "SPBIAS":
            try:
                value = float(self.spbias_var.get().strip())
            except ValueError:
                value = 0.0
            value = max(-200.0, min(200.0, value))
            self.spbias_var.set(f"{value:.2f}")
            self.spbias_slider_var.set(value)
            return

        if key == "SP":
            try:
                value = float(self.sp_var.get().strip())
            except ValueError:
                value = 70.0
            value = max(-20.0, min(400.0, value))
            self.sp_var.set(f"{value:.2f}")
            self.sp_slider_var.set(value)
            return

        if key == "ALPHA":
            try:
                value = float(self.alpha_var.get().strip())
            except ValueError:
                value = 0.25
            value = max(0.001, min(1.0, value))
            self.alpha_var.set(f"{value:.3f}")
            self.alpha_slider_var.set(value)
            return

        if key == "MAXSTEP":
            try:
                value = int(round(float(self.maxstep_var.get().strip())))
            except ValueError:
                value = 15
            value = max(0, min(255, value))
            self.maxstep_var.set(f"{value}")
            self.maxstep_slider_var.set(float(value))
            return

        if key == "ENTERCNT":
            try:
                value = int(round(float(self.entercnt_var.get().strip())))
            except ValueError:
                value = 16
            value = max(1, min(400, value))
            self.entercnt_var.set(f"{value}")
            self.entercnt_slider_var.set(float(value))
            return

        if key == "EXITCNT":
            try:
                value = int(round(float(self.exitcnt_var.get().strip())))
            except ValueError:
                value = 8
            value = max(1, min(400, value))
            self.exitcnt_var.set(f"{value}")
            self.exitcnt_slider_var.set(float(value))
            return

        if key == "FAN":
            try:
                value = float(self.fan_var.get().strip())
            except ValueError:
                value = 0.0
            value = max(0.0, min(100.0, value))
            self.fan_var.set(f"{value:.1f}")
            self.fan_slider_var.set(value)
            return

        if key == "MANPWM":
            try:
                value = float(self.manpwm_var.get().strip())
            except ValueError:
                value = 0.0
            value = max(0.0, min(255.0, value))
            self.manpwm_var.set(f"{value:.2f}")
            self.manpwm_slider_var.set(value)

    def _apply_all(self) -> None:
        self._set_param("KP", self.kp_var)
        self._set_param("KI", self.ki_var)
        self._set_param("KD", self.kd_var)
        self._set_param("BIAS", self.bias_var)
        self._set_param("SPBIAS", self.spbias_var)
        self._set_param("SP", self.sp_var)
        self._set_param("ALPHA", self.alpha_var)
        self._set_param("MAXSTEP", self.maxstep_var)
        self._set_param("ENTERCNT", self.entercnt_var)
        self._set_param("EXITCNT", self.exitcnt_var)
        self._set_param("FAN", self.fan_var)
        self._set_param("MANPWM", self.manpwm_var)
        self._set_fan_inversion()
        self._set_mode()

    def _set_mode(self) -> None:
        value = self.ctrl_mode_var.get().strip().upper()
        if value not in {"AUTO", "MANUAL", "SMART"}:
            messagebox.showerror("Invalid MODE", "Mode must be AUTO, MANUAL, or SMART.")
            return
        self._save_state()
        self._send_command(f"SET MODE {value}")

    def _set_fan_inversion(self) -> None:
        value = "1" if self.fan_inv_var.get() else "0"
        self._save_state()
        self._send_command(f"SET FANINV {value}")

    def _run_on(self) -> None:
        self._send_command("SET RUN ON")

    def _run_off(self) -> None:
        self._send_command("SET RUN OFF")

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

            if self.msg_queue.qsize() < self.max_queue_items:
                self.msg_queue.put(("line", line))
            elif self.msg_queue.qsize() == self.max_queue_items:
                self.msg_queue.put(("log", "Warning: input flood detected, dropping lines to keep UI responsive."))

    def _drain_queue(self) -> None:
        try:
            processed = 0
            while processed < 300:
                kind, payload = self.msg_queue.get_nowait()
                processed += 1
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
        if line.startswith("CFG ") or line.startswith("Rawtemp "):
            self.handshake_ok = True
            self.awaiting_handshake = False

        telemetry = TELEMETRY_RE.search(line)
        if telemetry:
            raw = float(telemetry.group(1))
            temp = float(telemetry.group(2))
            smooth = float(telemetry.group(3))
            pwm = float(telemetry.group(4))
            p_term = float(telemetry.group(5) or 0.0)
            i_term = float(telemetry.group(6) or 0.0)
            d_term = float(telemetry.group(7) or 0.0)
            out = float(telemetry.group(8) or pwm)
            bias = float(telemetry.group(9) or 0.0)
            spbias = float(telemetry.group(10) or 0.0)
            sp = float(telemetry.group(11))
            effsp = float(telemetry.group(12) or sp + spbias)
            fan_speed = float(telemetry.group(13))
            fan_pwm = float(telemetry.group(14))
            ctrl_mode = telemetry.group(15) or self.ctrl_mode_var.get().strip().upper() or "AUTO"
            ctrl_state = telemetry.group(16) or ("MANUAL" if ctrl_mode == "MANUAL" else "PID")
            manpwm_text = telemetry.group(17) or self.manpwm_var.get().strip() or "0"
            holdpwm_text = telemetry.group(18) or "0"
            enter_prog_text = telemetry.group(19) or "0"
            exit_prog_text = telemetry.group(20) or "0"
            abs_err_text = telemetry.group(21) or "0"
            run_state = telemetry.group(22) or "ON"
            fan_inv_state = telemetry.group(23) or ("1" if self.fan_inv_var.get() else "0")
            try:
                manpwm = float(manpwm_text)
            except ValueError:
                manpwm = 0.0
            try:
                holdpwm = float(holdpwm_text)
            except ValueError:
                holdpwm = 0.0
            try:
                enter_prog = float(enter_prog_text)
            except ValueError:
                enter_prog = 0.0
            try:
                exit_prog = float(exit_prog_text)
            except ValueError:
                exit_prog = 0.0
            try:
                abs_err = float(abs_err_text)
            except ValueError:
                abs_err = 0.0

            self.raw_temp_var.set(f"{raw:.2f}")
            self.temp_var.set(f"{temp:.2f}")
            self.smooth_var.set(f"{smooth:.2f}")
            self.bias_live_var.set(f"{bias:.2f}")
            self.spbias_live_var.set(f"{spbias:.2f}")
            self.sp_live_var.set(f"{sp:.2f}")
            self.effsp_live_var.set(f"{effsp:.2f}")
            self.pwm_var.set(f"{pwm:.0f}")
            self.p_term_var.set(f"{p_term:.2f}")
            self.i_term_var.set(f"{i_term:.2f}")
            self.d_term_var.set(f"{d_term:.2f}")
            self.out_var.set(f"{out:.2f}")
            self.fan_speed_var.set(f"{fan_speed:.1f}")
            self.fan_pwm_var.set(f"{fan_pwm:.0f}")
            self.mode_live_var.set(ctrl_mode)
            self.state_live_var.set(ctrl_state)
            self.manpwm_live_var.set(f"{manpwm:.0f}")
            self.holdpwm_live_var.set(f"{holdpwm:.2f}")
            self.enter_prog_live_var.set(f"{enter_prog:.1f}")
            self.exit_prog_live_var.set(f"{exit_prog:.1f}")
            self.abs_err_live_var.set(f"{abs_err:.2f}")
            self.run_live_var.set(run_state)
            self.fan_inv_live_var.set("Yes" if fan_inv_state == "1" else "No")

            now_iso = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="milliseconds")
            self._write_csv_row(
                {
                    "timestamp_iso": now_iso,
                    "elapsed_s": f"{max(0.0, time.monotonic() - self.csv_start_monotonic):.3f}",
                    "raw_temp_c": raw,
                    "temp_filtered_c": temp,
                    "temp_smooth_c": smooth,
                    "pwm": int(round(pwm)),
                    "p_term": p_term,
                    "i_term": i_term,
                    "d_term": d_term,
                    "pid_out": out,
                    "pid_bias": bias,
                    "setpoint_bias_c": spbias,
                    "setpoint_c": sp,
                    "effective_setpoint_c": effsp,
                    "fan_speed_pct": fan_speed,
                    "fan_pwm_raw": int(round(fan_pwm)),
                    "mode": ctrl_mode,
                    "state": ctrl_state,
                    "manual_pwm_cmd": manpwm,
                    "hold_pwm": holdpwm,
                    "enter_progress_pct": enter_prog,
                    "exit_progress_pct": exit_prog,
                    "abs_error_c": abs_err,
                    "run_state": run_state,
                    "fan_inverted": 1 if fan_inv_state == "1" else 0,
                }
            )

            next_t = 0.0 if not self.times else self.times[-1] + 0.5
            self.times.append(next_t)
            self.raw_values.append(raw)
            self.temp_values.append(temp)
            self.smooth_values.append(smooth)
            self.sp_values.append(sp)
            self.pwm_values.append(pwm)
            self.p_term_values.append(p_term)
            self.i_term_values.append(i_term)
            self.d_term_values.append(d_term)
            self.out_values.append(out)
            self.holdpwm_values.append(holdpwm)
            self.enter_prog_values.append(enter_prog)
            self.exit_prog_values.append(exit_prog)
            self.fan_pwm_values.append(fan_pwm)

            self._trim_history()
            self._sync_offset_scale()
            self._mark_plot_dirty()
            return

        cfg = CFG_RE.search(line)
        if cfg:
            self.kp_var.set(cfg.group(1))
            self.ki_var.set(cfg.group(2))
            self.kd_var.set(cfg.group(3))
            self.bias_var.set(cfg.group(4))
            self.spbias_var.set(cfg.group(5))
            self.sp_var.set(cfg.group(6))
            self.alpha_var.set(cfg.group(7))
            self.maxstep_var.set(cfg.group(8))
            self.entercnt_var.set(cfg.group(9))
            self.exitcnt_var.set(cfg.group(10))
            self.fan_var.set(cfg.group(11))
            self.fan_inv_var.set(cfg.group(12) == "1")
            self.ctrl_mode_var.set(cfg.group(13))
            self.manpwm_var.set(cfg.group(14))
            self.run_live_var.set(cfg.group(15))
            self.fan_inv_live_var.set("Yes" if cfg.group(12) == "1" else "No")
            self._sync_slider_from_entry("SPBIAS")
            self._sync_slider_from_entry("SP")
            self._sync_slider_from_entry("ALPHA")
            self._sync_slider_from_entry("MAXSTEP")
            self._sync_slider_from_entry("ENTERCNT")
            self._sync_slider_from_entry("EXITCNT")
            self._sync_slider_from_entry("FAN")
            self._sync_slider_from_entry("MANPWM")
            self._save_state()

    def _append_log(self, text: str) -> None:
        self.log_text.insert("end", text + "\n")
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > self.max_log_lines:
            remove_until = line_count - self.max_log_lines
            self.log_text.delete("1.0", f"{remove_until + 1}.0")
        self.log_text.see("end")

    def _check_handshake(self) -> None:
        if self.awaiting_handshake and time.monotonic() > self.handshake_deadline:
            self._append_log("No valid HeatsinkLab telemetry detected on this port.")
            messagebox.showwarning(
                "Wrong Port",
                "Connected port does not look like the ESP32 controller.\nSelect another COM port.",
            )
            self._disconnect()
        self.root.after(300, self._check_handshake)

    def _mark_plot_dirty(self) -> None:
        self.plot_dirty = True

    def _refresh_plot_if_needed(self) -> None:
        if self.plot_dirty:
            self._render_plot()
            self.plot_dirty = False
        self.root.after(250, self._refresh_plot_if_needed)

    def _apply_plot_config(self) -> None:
        self._trim_history()
        self._sync_offset_scale()
        self._mark_plot_dirty()

    def _on_auto_scroll_toggle(self) -> None:
        self._sync_offset_scale()
        self._mark_plot_dirty()

    def _on_offset_change(self, _value: str) -> None:
        if not self.auto_scroll_var.get():
            self._mark_plot_dirty()

    def _clear_plot(self) -> None:
        self.times.clear()
        self.raw_values.clear()
        self.temp_values.clear()
        self.smooth_values.clear()
        self.sp_values.clear()
        self.pwm_values.clear()
        self.p_term_values.clear()
        self.i_term_values.clear()
        self.d_term_values.clear()
        self.out_values.clear()
        self.holdpwm_values.clear()
        self.enter_prog_values.clear()
        self.exit_prog_values.clear()
        self.fan_pwm_values.clear()
        self.offset_var.set(0.0)
        self._sync_offset_scale()
        self._mark_plot_dirty()

    def _trim_history(self) -> None:
        try:
            keep = int(float(self.max_points_var.get().strip()))
        except ValueError:
            return

        keep = max(100, min(200000, keep))
        if len(self.times) <= keep:
            return

        drop = len(self.times) - keep
        del self.times[:drop]
        del self.raw_values[:drop]
        del self.temp_values[:drop]
        del self.smooth_values[:drop]
        del self.sp_values[:drop]
        del self.pwm_values[:drop]
        del self.p_term_values[:drop]
        del self.i_term_values[:drop]
        del self.d_term_values[:drop]
        del self.out_values[:drop]
        del self.holdpwm_values[:drop]
        del self.enter_prog_values[:drop]
        del self.exit_prog_values[:drop]
        del self.fan_pwm_values[:drop]

    def _sync_offset_scale(self) -> None:
        if len(self.times) < 2:
            self.offset_scale.configure(from_=0.0, to=0.0)
            self.offset_var.set(0.0)
            return

        end_t = self.times[-1]
        try:
            window = float(self.window_seconds_var.get().strip())
        except ValueError:
            window = 120.0
        window = max(5.0, window)

        max_start = max(0.0, end_t - window)
        self.offset_scale.configure(from_=0.0, to=max_start)

        if self.auto_scroll_var.get():
            self.offset_var.set(max_start)
        else:
            current = self.offset_var.get()
            if current > max_start:
                self.offset_var.set(max_start)

    def _render_plot(self) -> None:
        self.ax_temp.clear()
        self.ax_pwm.clear()

        if not self.times:
            self.ax_temp.set_title("No telemetry yet")
            self.ax_temp.set_xlabel("Time [s]")
            self.ax_temp.set_ylabel("Temperature [C]")
            self.ax_pwm.set_ylabel("PWM")
            self.canvas_plot.draw_idle()
            return

        t = self.times
        raw = self.raw_values
        temp = self.temp_values
        smooth = self.smooth_values
        sp = self.sp_values
        pwm = self.pwm_values
        p_term = self.p_term_values
        i_term = self.i_term_values
        d_term = self.d_term_values
        out = self.out_values
        holdpwm = self.holdpwm_values
        enter_prog = self.enter_prog_values
        exit_prog = self.exit_prog_values
        fan_pwm = self.fan_pwm_values

        x_min, x_max = t[0], t[-1]
        mode = self.mode_var.get()
        if mode == "rolling":
            try:
                window = float(self.window_seconds_var.get().strip())
            except ValueError:
                window = 120.0
            window = max(5.0, window)

            if self.auto_scroll_var.get():
                x_max = t[-1]
                x_min = max(t[0], x_max - window)
            else:
                x_min = self.offset_var.get()
                x_max = x_min + window
                if x_max > t[-1]:
                    x_max = t[-1]
                    x_min = max(t[0], x_max - window)

        def latest_in_window(values: list[float]) -> float | None:
            for idx in range(len(t) - 1, -1, -1):
                if x_min <= t[idx] <= x_max:
                    return values[idx]
            return values[-1] if values else None

        if self.show_raw_var.get():
            v = latest_in_window(raw)
            label = f"Raw {v:.2f}" if v is not None else "Raw"
            self.ax_temp.plot(t, raw, color="#1f77b4", linewidth=1.0, label=label)
        if self.show_temp_var.get():
            v = latest_in_window(temp)
            label = f"Temp {v:.2f}" if v is not None else "Temp"
            self.ax_temp.plot(t, temp, color="#2ca02c", linewidth=1.2, label=label)
        if self.show_smooth_var.get():
            v = latest_in_window(smooth)
            label = f"Smooth {v:.2f}" if v is not None else "Smooth"
            self.ax_temp.plot(t, smooth, color="#d62728", linewidth=1.5, label=label)
        if self.show_sp_var.get():
            v = latest_in_window(sp)
            label = f"SP {v:.2f}" if v is not None else "SP"
            self.ax_temp.plot(t, sp, color="#9467bd", linewidth=1.2, linestyle="--", label=label)
        if self.show_pwm_var.get():
            v = latest_in_window(pwm)
            label = f"PWM {v:.0f}" if v is not None else "PWM"
            self.ax_pwm.plot(t, pwm, color="#ff7f0e", linewidth=1.2, label=label)
        if self.show_fan_pwm_var.get():
            v = latest_in_window(fan_pwm)
            label = f"Fan PWM {v:.0f}" if v is not None else "Fan PWM"
            self.ax_pwm.plot(t, fan_pwm, color="#17becf", linewidth=1.2, linestyle="--", label=label)
        if self.show_p_var.get():
            v = latest_in_window(p_term)
            label = f"P {v:.2f}" if v is not None else "P"
            self.ax_pwm.plot(t, p_term, color="#8c564b", linewidth=1.2, linestyle="-.", label=label)
        if self.show_i_var.get():
            v = latest_in_window(i_term)
            label = f"I {v:.2f}" if v is not None else "I"
            self.ax_pwm.plot(t, i_term, color="#bcbd22", linewidth=1.2, linestyle="-.", label=label)
        if self.show_d_var.get():
            v = latest_in_window(d_term)
            label = f"D {v:.2f}" if v is not None else "D"
            self.ax_pwm.plot(t, d_term, color="#7f7f7f", linewidth=1.2, linestyle="-.", label=label)
        if self.show_out_var.get():
            v = latest_in_window(out)
            label = f"PID OUT {v:.2f}" if v is not None else "PID OUT"
            self.ax_pwm.plot(t, out, color="#e377c2", linewidth=1.2, linestyle="--", label=label)
        if self.show_holdpwm_var.get():
            v = latest_in_window(holdpwm)
            label = f"HOLD PWM {v:.2f}" if v is not None else "HOLD PWM"
            self.ax_pwm.plot(t, holdpwm, color="#ff1493", linewidth=1.2, linestyle=":", label=label)
        if self.show_enter_prog_var.get():
            v = latest_in_window(enter_prog)
            label = f"ENTER % {v:.1f}" if v is not None else "ENTER %"
            self.ax_pwm.plot(t, enter_prog, color="#005f73", linewidth=1.2, linestyle="-", label=label)
        if self.show_exit_prog_var.get():
            v = latest_in_window(exit_prog)
            label = f"EXIT % {v:.1f}" if v is not None else "EXIT %"
            self.ax_pwm.plot(t, exit_prog, color="#ca6702", linewidth=1.2, linestyle="-", label=label)

        self.ax_temp.set_xlabel("Time [s]")
        self.ax_temp.set_ylabel("Temperature [C]")
        self.ax_pwm.set_ylabel("PWM")
        self.ax_temp.yaxis.set_label_position("left")
        self.ax_temp.yaxis.tick_left()
        self.ax_pwm.yaxis.set_label_position("right")
        self.ax_pwm.yaxis.tick_right()

        if self.temp_auto_y_var.get():
            self.ax_temp.relim()
            self.ax_temp.autoscale_view(scalex=False, scaley=True)
        else:
            try:
                tmin = float(self.temp_ymin_var.get().strip())
                tmax = float(self.temp_ymax_var.get().strip())
                if tmax > tmin:
                    self.ax_temp.set_ylim(tmin, tmax)
            except ValueError:
                pass

        if self.pwm_auto_y_var.get():
            self.ax_pwm.relim()
            self.ax_pwm.autoscale_view(scalex=False, scaley=True)
        else:
            try:
                pmin = float(self.pwm_ymin_var.get().strip())
                pmax = float(self.pwm_ymax_var.get().strip())
                if pmax > pmin:
                    self.ax_pwm.set_ylim(pmin, pmax)
            except ValueError:
                pass

        self.ax_temp.grid(alpha=0.25)
        self.ax_temp.set_xlim(x_min, x_max)

        temp_handles, temp_labels = self.ax_temp.get_legend_handles_labels()
        pwm_handles, pwm_labels = self.ax_pwm.get_legend_handles_labels()
        all_handles = temp_handles + pwm_handles
        all_labels = temp_labels + pwm_labels
        if all_handles:
            self.ax_temp.legend(all_handles, all_labels, loc="upper left", ncols=3)

        self.canvas_plot.draw_idle()


def main() -> None:
    root = tk.Tk()
    ttk.Style(root).theme_use("clam")
    PIDGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
