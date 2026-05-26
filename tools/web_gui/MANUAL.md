# HeatsinkLab Wind Tunnel — User Manual

## Requirements

- Windows 10 or 11 (Linux / macOS work too)
- Python 3.10 or newer ([python.org](https://python.org) or `winget install Python.Python.3.12`)
- No other software needed

## Installation

1. Download and unzip the project from GitHub
2. Open a Command Prompt in the `tools/web_gui` folder
3. Run: `pip install -r requirements.txt`
4. Or simply double-click `start.bat`

## Starting the server

Double-click `start.bat` — a browser window will open at **http://localhost:8765**

> If the tab does not open automatically: navigate to http://localhost:8765 manually.

## Connecting to the device

1. Plug the ESP32-S3 into the PC via USB
2. Select the correct COM port from the dropdown (e.g. `COM4 — USB Serial Device`)
3. Click **Connect** — the telemetry chart starts updating within a few seconds

> **No hardware?** Select **VIRTUAL** from the port dropdown to use the built-in simulator. All GUI features work in virtual mode.

---

## Normal Mode — Controls

### Setpoint

Enter a target temperature in °C. The firmware PID loop will drive the heater toward this value.

### Control Modes

| Mode | Behaviour |
|---|---|
| AUTO | PID loop continuously adjusts heater PWM toward setpoint |
| MANUAL | Fixed PWM set by the `MANPWM` slider |
| SMART | PID until stable (±0.5 °C for 8 s), then locks equilibrium PWM. Used automatically in Tester mode. |

### Fan Speed

The fan speed slider (0–100 %) controls cooling airflow through the tunnel. 0 = natural convection only.

### Fan Power (FANPWR)

A separate toggle cuts power to the fan motor entirely via MOSFET (GPIO 10), guaranteeing zero airflow for natural-convection tests. This is distinct from setting fan speed to 0 %.

---

## Run Metadata

Before starting CSV recording, optionally fill in:

- **Run ID** — a short label (e.g. `run_001`) written into the CSV header
- **Heatsink** — identifies the heatsink under test (e.g. `HS_finned_A`)

These values appear as comment lines at the top of the CSV:

```
# schema_version: 4
# run_id: run_001
# heatsink_id: HS_finned_A
# start_time: 2026-03-29T14:30:22
```

---

## CSV Column Customisation

Clicking **Start CSV** opens a dialog where you can select exactly which columns to record. Columns are grouped by category (Basic, Temperature, PID Details, Smart Mode, Fan, Power, Sensors). An Excel Power Query import formula is generated automatically based on your selection.

---

## Phase Markers

While recording, click **📌 Marker** to stamp the current moment with a label. The marker:
- Adds an orange dashed vertical line to the chart
- Writes a row to the CSV with the label in the `event` column

---

## Presets

The **Presets** section in the sidebar lets you save and restore named configurations:

- Three built-in presets are provided (Default, Aggressive, Conservative)
- **Save Current** — saves all parameter values under a name you choose
- **Load** — applies the selected preset immediately
- **Delete** — removes a saved preset

Presets are stored in `tools/web_gui/presets.json`.

---

## Expert / Student Mode

Click **🎓 Student** in the top bar to hide advanced parameters (ALPHA, MAXSTEP, ENTERCNT, EXITCNT, BIAS, SPBIAS, PID debug series, and advanced telemetry fields). The toggle state is remembered across sessions.

---

## Ambient Temperature

Enter the current room temperature (°C) in the **Ambient (°C)** field in the sidebar. This value is used by the Tester mode to calculate thermal resistance (R_th). The Tester panel includes its own Ambient input that stays synchronised.

---

## Performance Metrics

The **Performance Metrics** panel computes step-response statistics from the current chart history:

| Metric | Meaning |
|---|---|
| Rise Time | Time to reach 90 % of the setpoint step |
| Settle Time | Time until temperature stays within ±2 °C of setpoint for 10 s |
| Overshoot % | Peak exceedance relative to step size |
| SS Error °C | Mean steady-state error over the last 20 samples |
| IAE (°C·s) | Integral of absolute error — lower is better |

Click **Compute** or enable **Auto on SP change** to trigger automatically when the setpoint changes by more than 2 °C.

---

## Graph Cursor / Probe Tool

Click **Cursor: OFF** in the chart controls to enable a crosshair overlay. While active:
- Hovering over the chart shows all visible series values at that time
- Clicking the chart **pins** the tooltip; click again to unpin

---

## Differential Pressure Sensor

If the Sensirion SDP510 is connected, the sidebar shows live readings:

| Reading | Meaning |
|---|---|
| DELTA_P1 | Raw differential pressure (Pa) |
| DELTA_P1F | EMA-filtered pressure (Pa) |

**Taring (zeroing):** Click **Tare Zero** in the Pressure section to record the current offset as the zero reference. All subsequent readings are shown relative to this baseline. Click **Reset Zero** to remove the offset and show raw sensor values.

The zeroing offset is applied in the backend and broadcast to all connected clients. Tare before each test run with no airflow to remove any sensor drift.

---

## Tester Mode

For running systematic heatsink characterisation tests:

1. Click **Tester** in the top bar
2. Enter the ambient (room) temperature in °C
3. Choose the **Fan condition**:
   - **Fan ON** — select a fan speed % and click **Set**
   - **Fan OFF** — cuts power to the fan entirely via MOSFET for true natural-convection conditions
4. Add test temperatures using **+ Add** (e.g. 40, 50, 60, 70 °C)
5. Set soak time (how long to hold each temperature once stable, default 60 s)
6. Optionally enter a Run ID and Heatsink ID, then click **▶ Start CSV** to begin logging
7. Click **▶ Start Test** — the system automatically steps through each temperature
8. When complete, download:
   - **Raw CSV**: full telemetry during the test (downloaded via Stop/Download CSV)
   - **Results CSV**: one row per temperature with EqPWM, Power, R_th, k, humidity

> **Tip:** Start CSV recording before starting the test to capture the full warm-up and all transitions.

---

## Understanding the Results CSV

| Column | Meaning |
|---|---|
| SP_degC | Setpoint temperature |
| Fan_cond | Fan condition: ON or OFF |
| Temp_actual | Measured heatsink base temperature at equilibrium |
| Ambient_degC | Room temperature entered before the test |
| EqPWM | Equilibrium PWM (0–255) — heater duty cycle at thermal balance |
| Power_W | Heater power consumption (W) at equilibrium |
| R_th (°C/W) | Thermal resistance — lower is better cooling |
| k (W/°C) | Cooling coefficient |
| Humidity_pct | Ambient relative humidity at time of step (if sensor connected, else blank) |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: serial` | Use `start.bat` instead of running `python server.py` directly |
| Cannot connect to COM port | Check Device Manager; try a different USB cable; replug the ESP32 |
| Connecting… hangs indefinitely | Unplug and replug the USB cable; restart the server |
| Temperature reads 0 | Check thermocouple wiring (SPI pins 11/12/13) |
| Power reads 0 V / 0 A | Check INA226 wiring (I²C 0x41, SDA=15, SCL=16) |
| Pressure reads nothing | Check SDP510 wiring (I²C 0x40, SDA=15, SCL=16); `Wire.setTimeOut(200)` is set in firmware for this sensor's clock stretching |
| Presets not saving | Ensure the `tools/web_gui` folder is writable |
| R_th shows NaN | INA226 not connected — power readings are 0, causing divide-by-zero; check INA226 wiring |
