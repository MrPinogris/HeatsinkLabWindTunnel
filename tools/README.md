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
- Connect to COM port and tune `KP`, `KI`, `KD`, `SP`, `ALPHA`, `MAXSTEP`, `FAN`
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

## Firmware serial commands

The ESP32 supports:

- `GET`
- `SET KP <value>`
- `SET KI <value>`
- `SET KD <value>`
- `SET SP <value>`
- `SET ALPHA <value>`
- `SET MAXSTEP <value>`
- `SET FAN <value>`

Example:

```text
SET KP 10.0
SET KI 0.8
SET KD 0.1
SET SP 75
SET FAN 40
GET
```

## Note

Only one program can use the same COM port at a time.
If GUI is connected, CSV logger cannot connect to that port simultaneously.
