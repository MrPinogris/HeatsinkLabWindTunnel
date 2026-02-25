# Serial CSV Logger

Use this script to read ESP32 serial output and store parsed telemetry in CSV.

## Install dependency

```powershell
pip install pyserial
```

## Run

```powershell
python tools/serial_to_csv.py --port COM5 --baud 115200
```

Replace `COM5` with your ESP32 port.

By default, CSV files are written to `logs/serial_YYYYMMDD_HHMMSS.csv`.

You can choose a custom file path:

```powershell
python tools/serial_to_csv.py --port COM5 --output logs/my_run.csv
```
