# HeatsinkLab Wind Tunnel

ESP32-S3 based heatsink thermal characterisation platform. A ceramic heater drives the heatsink under test to a series of set-point temperatures while a controlled fan provides forced convection through the wind tunnel. All sensor data streams to a browser-based GUI; results are saved automatically as a CSV.

---

## System Architecture

```
┌──────────────────────────────────┐
│  Firmware (C++ / ESP32-S3)       │  src/  — stable, treat as black box
│  · PID heater + fan control      │
│  · MAX6675 thermocouple (SPI)    │
│  · INA226 power monitor (I²C)    │
│  · SDP510 diff. pressure (I²C)   │
│  · EZO-HUM humidity probe (I²C)  │
│  · Serial command interface      │
└────────────┬─────────────────────┘
             │ USB Serial 115 200 baud
┌────────────▼─────────────────────┐
│  Backend  (Python / FastAPI)     │  tools/web_gui/server.py
│  · WebSocket server :8765        │
│  · Telemetry parser              │
│  · CSV logger                    │
│  · Virtual MCU simulator         │
└────────────┬─────────────────────┘
             │ WebSocket
┌────────────▼─────────────────────┐
│  Frontend (HTML / JS / CSS)      │  tools/web_gui/static/index.html
│  · Chart.js real-time graphs     │
│  · PID tuning controls           │
│  · Tester workflow (automated)   │
│  · CSV export                    │
└──────────────────────────────────┘
```

---

## Hardware

### Component Summary

| Component | Part | Interface | I²C Address |
|---|---|---|---|
| MCU | ESP32-S3 DevKit-C1 | — | — |
| Temperature sensor | MAX6675 thermocouple module | SPI | — |
| Power monitor | INA226 (A0 → VCC) | I²C | 0x41 |
| Differential pressure | Sensirion SDP510 | I²C | 0x40 |
| Humidity probe | EZO-HUM (Atlas Scientific) | I²C | 0x6F |
| Heater switch | MOSFET module (PWM gate) | GPIO 4 | — |
| Fan PWM | MOSFET / driver module | GPIO 5 | — |
| Fan power cut-off | MOSFET module (digital gate) | GPIO 10 | — |

### ESP32-S3 Pin Assignments

| GPIO | Function | Notes |
|---|---|---|
| 4 | Heater MOSFET gate | PWM 500 Hz, 8-bit (0–255) |
| 5 | Fan PWM signal | PWM 500 Hz, 8-bit |
| 10 | Fan power MOSFET gate | HIGH = powered, LOW = fully off |
| 11 | MAX6675 SO (MISO) | SPI |
| 12 | MAX6675 CS | SPI |
| 13 | MAX6675 SCK | SPI |
| 15 | I²C SDA | Shared bus: INA226, SDP510, EZO-HUM |
| 16 | I²C SCL | Shared bus |

---

## Wiring

### Power Distribution

```
12 V Lab PSU (+) ─────┬──────────────────── Heater MOSFET IN+
                      └──────────────────── Fan MOSFET IN+
12 V Lab PSU (−) ─────┬──────────────────── Heater MOSFET IN−
                      ├──────────────────── Fan MOSFET IN−
                      └──────────────────── ESP32 GND (common)
```

### Heater Power Path

```
12 V (+) → Heater MOSFET IN+
           Heater MOSFET OUT+ → Heater element (+)
           Heater element (−) → INA226 IN+
                                INA226 IN−  → Heater MOSFET OUT−
12 V (−) → Heater MOSFET IN−  (common GND)

ESP GPIO 4  → Heater MOSFET signal
ESP GND     → Heater MOSFET signal GND
```

INA226 shunt is wired in series with the heater so it measures heater current directly.

### Fan Power Path

```
12 V (+) → Fan MOSFET (power cut-off) IN+
           Fan MOSFET OUT+ → Fan (+) / PWM driver IN+
12 V (−) → Fan MOSFET IN−  (common GND)

ESP GPIO 5  → Fan PWM signal
ESP GPIO 10 → Fan power MOSFET gate  (HIGH = fan enabled, LOW = fully off)
ESP GND     → Fan MOSFET signal GND
```

### MAX6675 Thermocouple (SPI)

| MAX6675 Pin | Connects to |
|---|---|
| VCC | ESP32 3.3 V |
| GND | ESP32 GND |
| SCK | GPIO 13 |
| CS  | GPIO 12 |
| SO  | GPIO 11 |

### INA226 Power Monitor (I²C, 0x41)

| INA226 Pin | Connects to |
|---|---|
| VCC | ESP32 3.3 V |
| GND | ESP32 GND |
| SDA | GPIO 15 |
| SCL | GPIO 16 |
| A0  | 3.3 V (sets address to 0x41) |
| A1  | GND |
| IN+ | Heater element output |
| IN− | Heater MOSFET drain |
| ALE | Not connected |

### Sensirion SDP510 Differential Pressure (I²C, 0x40)

| SDP510 Pin | Connects to |
|---|---|
| VCC | ESP32 3.3 V |
| GND | ESP32 GND |
| SDA | GPIO 15 (shared I²C bus) |
| SCL | GPIO 16 (shared I²C bus) |

Sensor is mounted across the wind tunnel to measure pressure drop (Pa) between inlet and outlet.

### EZO-HUM Humidity Probe (I²C, 0x6F)

| EZO-HUM Pin | Connects to |
|---|---|
| VCC (red) | ESP32 3.3 V |
| GND (black) | ESP32 GND |
| SDA (green) | GPIO 15 (shared I²C bus) |
| SCL (white) | GPIO 16 (shared I²C bus) |
| AUTO (blue) | Not connected |

> **First-time setup:** Factory default is UART mode (blinking green LED).
> Send `I2C,111\r` at 9600 baud over UART once, then power-cycle until LED is solid blue (I²C mode).

---

## Physical Assembly

See `docs/media/` for annotated photos of the physical build. Key assembly features:

- **Wind tunnel inlet** — Fan with a hexagonal (honeycomb) grid immediately downstream to break up turbulence and produce laminar airflow through the tunnel.
- **Fan guard** — A protective shield covers the fan face to prevent contact injury during operation.
- **Heater module** — Ceramic PTC heater element topped with a copper spreader plate. The thermocouple is inserted into a precision-drilled hole in the copper plate to measure the heatsink base temperature accurately. The heatsink under test clips onto the copper plate.
- **Dev board** — All MOSFET switching modules, the INA226, and the ESP32-S3 DevKit are mounted on the dev board. The connector row (left to right) carries: humidity sensor, differential pressure sensor, and fan motor.
- **Expansion** — One additional MOSFET module on the left of the fan motor connector provides the independent power cut-off for the fan (GPIO 10), allowing the fan to be fully de-energised for natural-convection tests.

---

## Flashing the Firmware

Requires [PlatformIO](https://platformio.org/) (VS Code extension or CLI).

```bash
pio run -t upload      # Build and flash to connected ESP32-S3
pio run                # Build only (no upload)
```

> The firmware source is under `src/` and is considered stable. Do not modify it without reviewing `CLAUDE.md` first.

---

## Web GUI

### Requirements

- Windows 10/11 (Linux/macOS also supported)
- Python 3.10 or newer

### Install & Run

```bash
cd tools/web_gui
pip install -r requirements.txt
python server.py
```

Browser opens automatically at **http://localhost:8765**.

**Quickstart (Windows):** double-click `tools/web_gui/start.bat` — installs dependencies and launches the server.

### Testing without hardware

Select **VIRTUAL** from the port dropdown to use the built-in firmware simulator. No ESP32 required.

---

## Control Modes

| Mode | Behaviour |
|---|---|
| AUTO | PID loop continuously drives heater PWM toward setpoint |
| MANUAL | Fixed PWM set directly by the `MANPWM` parameter |
| SMART | PID until stable (±0.5 °C for 8 s), then locks the equilibrium PWM — used for automated Tester mode |

---

## Serial Command Reference

Commands are sent from the backend to the ESP32 over USB serial (115 200 baud):

| Command | Range | Description |
|---|---|---|
| `SET KP <f>` | float | PID proportional gain |
| `SET KI <f>` | float | PID integral gain |
| `SET KD <f>` | float | PID derivative gain |
| `SET BIAS <f>` | −255 to 255 | PID output bias |
| `SET SPBIAS <f>` | float | Setpoint offset bias |
| `SET SP <f>` | −20 to 400 °C | Temperature setpoint |
| `SET ALPHA <f>` | 0.001 to 1.0 | EMA filter coefficient |
| `SET MAXSTEP <n>` | int | Maximum PWM change per cycle |
| `SET FAN <n>` | 0 to 100 | Fan speed % |
| `SET FANINV <0/1>` | 0 or 1 | Invert fan PWM polarity |
| `SET FANPWR <ON/OFF>` | ON / OFF | Fan power MOSFET enable |
| `SET MODE <m>` | AUTO/MANUAL/SMART | Control mode |
| `SET MANPWM <f>` | 0 to 255 | Manual PWM value |
| `SET RUN <ON/OFF>` | ON / OFF | Enable / disable heater |
| `GET` | — | Print current configuration |

All parameters are bounds-checked in firmware before acceptance.

---

## Telemetry Output

The firmware emits one telemetry line per control cycle over serial. Example fields:

```
Rawtemp <°C>  Temp: <°C>  Smooth: <°C>  PWM: <0-255>
P: <f>  I: <f>  D: <f>  OUT: <f>  BIAS: <f>  SPBIAS: <f>
SP: <°C>  EFFSP: <°C>  FAN: <%>  FANPWM: <raw>
MODE: <AUTO|MANUAL|SMART>  STATE: <PID|HOLD|MANUAL>
MANPWM: <f>  HOLDPWM: <f>  ENTPROG: <%>  EXTPROG: <%>  EABS: <°C>
RUN: <ON|OFF>  FANINV: <0|1>
V: <V>  I: <A>  W: <W>  EQPWM: <0-255>  FANPWR: <ON|OFF>
HUMIDITY: <%>  HUM_TEMP: <°C>
DELTA_P1: <Pa>  DELTA_P1F: <Pa>  DELTA_P2: <Pa>  DELTA_P2F: <Pa>
```

---

## CSV Schema

Raw telemetry is logged to `logs/serial_<timestamp>.csv`. Schema version 4.

```
timestamp_iso, elapsed_s, raw_temp_c, temp_filtered_c, temp_smooth_c,
pwm, p_term, i_term, d_term, pid_out, pid_bias, setpoint_bias_c,
setpoint_c, effective_setpoint_c, fan_speed_pct, fan_pwm_raw, fan_power,
mode, state, manual_pwm_cmd, hold_pwm, enter_progress_pct,
exit_progress_pct, abs_error_c, run_state, fan_inverted,
vin, iin, pin, eq_pwm,
delta_p1, delta_p1f, delta_p2, delta_p2f,
humidity_pct, hum_temp_c,
event
```

Results CSV (one row per test temperature):

```
timestamp, run_id, heatsink_id, sp_temp, temp, amb_temp,
pwm_heater, fan_cmd, fan_pwm, airspeed, delta_p1, delta_p2,
humidity_pct, vin, iin, pin, mode, state, event
```

---

## Future Sensors

The system is designed for zero-disruption sensor additions. The `ExtSensorRegistry` in firmware provides named slots; the backend `TELEM_RE` regex accepts new named fields without breaking the existing parser.

| Sensor | CSV Fields | Status |
|---|---|---|
| Airspeed / anemometer | `airspeed` (m/s) | Planned — hardware not yet wired |
| Differential pressure (second port) | `delta_p2`, `delta_p2f` (Pa) | Parser ready; physical port mapped to 0 |
| Ambient humidity (additional) | `humidity_pct` | EZO-HUM implemented; Sensirion variant planned |

See `CLAUDE.md` for the 4-step pattern to add any new sensor without breaking existing data flows.

---

## Repository Structure

```
HeatsinkLabWindTunnel/
├── src/                        Firmware (C++ / PlatformIO)
│   ├── main.cpp                Setup, loop, control FSM
│   ├── PIDController.cpp/h     PID controller
│   ├── SensorManager.cpp/h     Sensor reads, EMA, glitch reject
│   ├── SerialProtocol.cpp/h    Serial command handler + telemetry emitter
│   ├── ExtSensorRegistry.cpp/h Named slot registry for future sensors
│   └── SystemState.h           Shared state struct + ControlMode enum
├── tools/web_gui/
│   ├── server.py               FastAPI backend + WebSocket + CSV logger
│   ├── static/index.html       Single-file browser GUI
│   ├── requirements.txt        Python dependencies
│   ├── start.bat               Windows one-click launcher
│   └── MANUAL.md               User-facing operating manual
├── docs/
│   ├── hardware.md             Detailed hardware reference (this thesis)
│   ├── Connections.txt         Raw wiring connection list
│   ├── media/                  Annotated build photographs
│   └── Todo.md                 Development task list
├── notes/
│   └── Ideas.md                Feature backlog with prioritisation scores
├── platformio.ini              PlatformIO build configuration
└── CLAUDE.md                   AI agent working instructions
```
