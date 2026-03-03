# HeatsinkLab Tools

## Dependencies

Install Python dependencies once:

```powershell
pip install pyserial matplotlib
```

## 1) PID Tuning GUI + Live Graph

Run:

```powershell
python tools/pid_gui.py
```

Features:
- Connect to COM port and tune `KP`, `KI`, `KD`, `BIAS`, `SPBIAS`, `SP`, `ALPHA`, `MAXSTEP`, `FAN`
- `BIAS` is output-bias, `SPBIAS` is setpoint-bias
- ESP32 persists those settings in NVS, so values survive reset/power-cycle
- GUI remembers the last parameter values between restarts (`tools/pid_gui_state.json`)
- Live telemetry display
- Fan control with reversed hardware logic (`255=off`, `0=full`) wrapped as user `FAN` percent (`0=off`, `100=full`)
- Live graph with toggleable series:
  - Raw Temp
  - Temp
  - Smooth
  - SP
  - PWM
  - Fan PWM
- Rolling window mode or full history mode
- Adjustable rolling window length (seconds)
- Adjustable retained history points
- History scroll slider for viewing older data
- Auto-scroll toggle to follow newest data or stay on historical view
- Zoom/pan/back/home controls using the matplotlib toolbar
- Scrollable full GUI layout for smaller monitors
- Integrated CSV logger (`Start CSV` / `Stop CSV`) while GUI is connected

In the GUI:
- Use `Get From ESP32` to read current firmware values
- Use `Apply All` or individual `Set ...` buttons
- Use `Apply View` after changing plot settings

## 2) Serial to CSV Logger

Use this to save telemetry for plotting later.

```powershell
python tools/serial_to_csv.py --port COM5 --baud 115200
```

Default CSV output:
- `logs/serial_YYYYMMDD_HHMMSS.csv`

Custom output file:

```powershell
python tools/serial_to_csv.py --port COM5 --output logs/my_run.csv
```

## CSV Schema v2 (Upgrade-Proof Baseline)

Use a versioned schema so future sensors can be added without breaking analysis scripts.

Core metadata fields:
- `schema_version` (example: `2.0`)
- `timestamp_iso`
- `elapsed_s`
- `run_id`
- `heatsink_id`
- `event_tag` (optional marker/annotation)

Current control + thermal fields:
- `raw_temp_c`
- `temp_filtered_c`
- `temp_smooth_c`
- `setpoint_c`
- `effective_setpoint_c`
- `setpoint_bias_c`
- `pwm`
- `p_term`
- `i_term`
- `d_term`
- `pid_out`
- `pid_bias`
- `mode`
- `state`
- `manual_pwm_cmd`
- `hold_pwm`
- `enter_progress_pct`
- `exit_progress_pct`
- `abs_error_c`
- `run_state`

Fan/airflow command fields:
- `fan_speed_pct`
- `fan_pwm_raw`
- `fan_inverted`

Future sensor placeholders (keep columns present, allow empty values until hardware is added):
- `power_v`
- `power_a`
- `power_w`
- `delta_p_pa`
- `airspeed_mps`

Recommended interpretation:
- Empty/NaN future sensor columns mean "sensor not installed or not active in this run".
- Keep column names stable across firmware/gui updates.
- If a breaking change is required, increment `schema_version`.

Minimal compatibility rule:
- New columns may be added at the end.
- Existing column semantics should not change without schema version bump.

## Firmware serial commands

The ESP32 supports:

- `GET`
- `SET KP <value>`
- `SET KI <value>`
- `SET KD <value>`
- `SET BIAS <value>`
- `SET SPBIAS <value>`
- `SET SP <value>`
- `SET ALPHA <value>`
- `SET MAXSTEP <value>`
- `SET ENTERCNT <value>`
- `SET EXITCNT <value>`
- `SET FAN <value>`
- `SET FANINV <0|1>`
- `SET MODE <AUTO|MANUAL|SMART>`
- `SET MANPWM <value>`
- `SET RUN <ON|OFF>`

Example:

```text
SET KP 10.0
SET KI 0.8
SET KD 0.1
SET BIAS 18
SET SPBIAS -2.5
SET SP 75
SET FAN 40
SET MODE SMART
GET
```

## Note

Only one process can use one COM port at a time.
- If GUI is connected, use the GUI integrated CSV logger.
- Use `serial_to_csv.py` when running headless (without GUI).
