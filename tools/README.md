# HeatsinkLab Tools

## Dependencies

Install Python dependency once:

```powershell
pip install pyserial
```

## 1) PID Tuning GUI

Use this to change controller values live while the ESP32 is running.

```powershell
python tools/pid_gui.py
```

In the GUI:
- Select COM port
- Connect
- Use `Get From ESP32` to read current values
- Change values and click `Set ...` or `Apply All`

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

The ESP32 now supports:

- `GET`
- `SET KP <value>`
- `SET KI <value>`
- `SET KD <value>`
- `SET SP <value>`
- `SET ALPHA <value>`
- `SET MAXSTEP <value>`

Example:

```text
SET KP 10.0
SET KI 0.8
SET KD 0.1
SET SP 75
GET
```

## Note

Only one program can use the same COM port at a time.
If GUI is connected, CSV logger cannot connect to that port simultaneously.
