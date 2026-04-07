# CLAUDE.md — HeatsinkLab Wind Tunnel

This file governs how Claude should work on this project, both in interactive and agent mode.

---

## Project Identity

**HeatsinkLab Wind Tunnel** is a student lab platform for characterising heatsink thermal performance. It controls a heater and fan via an ESP32-S3, measures temperature and power in real time, and streams telemetry to a browser-based GUI.

**Who uses this:** Engineering students (primary users) and instructors. Students have no expectation of technical knowledge about PID, firmware, or serial ports. The system involves a live heater element — physical safety is a real concern.

---

## End Goal

The final product must deliver this exact student experience:

```
1. Plug the ESP32 into the lab PC via USB
2. Open the GUI (double-click start.bat)
3. Follow the guided connection wizard — select port, click Connect, sensors verified automatically
4. Type a heatsink ID (e.g. "HS-01-fin-array")
5. Press ONE button: "Start Test"
6. Wait — the system steps through all temperatures, soaks, records results automatically
7. Results CSV downloads automatically when the test finishes
8. Remove heatsink, insert next one, repeat from step 4
```

Students must never need to:
- Know what PID is or touch any PID settings
- Manually add temperatures one by one
- Click "Download CSV" after the test
- Know what a COM port is beyond selecting it from a list
- Do anything after pressing Start Test except wait

---

## Software-First Development Philosophy

**All new features must be implemented in `server.py` and/or `index.html` (the backend and frontend).**

Firmware (`src/` folder) is considered **stable and locked**. Treat it as a black box that exposes:
- A serial command interface (`SET`, `GET`)
- A telemetry stream (parsed by `server.py`)

**Rules:**
- If a feature can be implemented in software OR firmware, always choose software.
- Never propose firmware changes for features that can live in the backend or frontend.
- Firmware changes require physical lab access to flash. Software changes deploy by restarting `server.py`.
- If a firmware change is genuinely unavoidable (new hardware sensor), flag it clearly and get explicit user confirmation before touching `src/`.

---

## Architecture (Three Tiers)

```
┌──────────────────────────────────┐
│  Firmware (C++ / ESP32-S3)       │  src/  ← STABLE / LOCKED — treat as black box
│  - PID heater + fan control      │  main.cpp · PIDController.cpp/h
│  - MAX6675 thermocouple (SPI)    │  SensorManager.cpp/h
│  - INA226 power monitor (I2C)    │  SerialProtocol.cpp/h
│  - Serial command interface      │  ExtSensorRegistry.cpp/h
│  - NVS config persistence        │  SystemState.h
└────────────┬─────────────────────┘
             │ USB Serial (115200 baud)
┌────────────▼─────────────────────┐
│  Backend (Python / FastAPI)      │  tools/web_gui/server.py  ← PRIMARY DEV TARGET
│  - WebSocket server :8765        │
│  - Serial telemetry parser       │
│  - CSV logging                   │
│  - Virtual MCU simulator         │
└────────────┬─────────────────────┘
             │ WebSocket
┌────────────▼─────────────────────┐
│  Frontend (HTML/JS/CSS)          │  tools/web_gui/static/index.html  ← PRIMARY DEV TARGET
│  - Chart.js real-time graphs     │
│  - PID tuning controls           │
│  - Tester workflow mode          │
│  - CSV export                    │
└──────────────────────────────────┘
```

---

## Key Files

| File | Role |
|------|------|
| `src/main.cpp` | Firmware: setup, loop, control FSM (SMART/AUTO/MANUAL), actuators — DO NOT TOUCH without confirmation |
| `src/PIDController.cpp/h` | PID controller class — DO NOT TOUCH without confirmation |
| `src/SensorManager.cpp/h` | MAX6675 + INA226 reads, EMA filter, glitch reject, stuck watchdog — DO NOT TOUCH without confirmation |
| `src/SerialProtocol.cpp/h` | Serial command handler, printConfig, emitTelemetry, NVS load/save — DO NOT TOUCH without confirmation |
| `src/ExtSensorRegistry.cpp/h` | Fixed-size slot registry for future extension sensors (airspeed, pressure, humidity) — add sensor slots here |
| `src/SystemState.h` | POD struct holding all shared config and runtime state; ControlMode enum |
| `tools/web_gui/server.py` | FastAPI backend, WebSocket, CSV logging — **primary development target** |
| `tools/web_gui/static/index.html` | Single-page frontend (all JS/CSS inline) — **primary development target** |
| `tools/web_gui/requirements.txt` | Python dependencies |
| `tools/web_gui/start.bat` | Windows quick-start launcher |
| `notes/Ideas.md` | Feature backlog with prioritisation scores |
| `README.md` | Hardware pinout, quick start |
| `tools/web_gui/MANUAL.md` | User-facing manual |

---

## Development Commands

### Backend / GUI
```bash
cd tools/web_gui
pip install -r requirements.txt
python server.py
# Opens http://localhost:8765
```

### Testing the GUI without hardware
The server has a virtual MCU simulator — connect to the "VIRTUAL" port option in the GUI dropdown. No ESP32 needed.

### Firmware (requires PlatformIO — only when explicitly needed)
```bash
pio run -t upload     # Build and flash to ESP32-S3
pio run               # Build only
```

---

## Control Modes (Firmware)

| Mode | Behaviour |
|------|-----------|
| AUTO | PID continuously drives heater PWM toward setpoint |
| MANUAL | Fixed PWM, direct control |
| SMART | PID until stable (±0.5°C / 8s), then locks PWM — **used for Tester mode** |

The Tester workflow always uses **SMART mode** because it reliably detects thermal equilibrium and locks the steady-state PWM needed for R_th calculation.

---

## Serial Command Protocol

Commands sent from backend → firmware over serial:

```
SET KP <float>        Proportional gain
SET KI <float>        Integral gain
SET KD <float>        Derivative gain
SET BIAS <float>      Output bias (-255 to 255)
SET SP <float>        Setpoint (-20 to 400°C)
SET ALPHA <float>     EMA filter (0.001 to 1.0)
SET FAN <0-100>       Fan speed %
SET MODE <AUTO|MANUAL|SMART>
SET RUN <ON|OFF>
GET                   Print current config
```

All parameters are bounds-checked in firmware before acceptance. The backend sends these via `sendCmd()` in `server.py`.

---

## Telemetry Format

The server parses telemetry lines from serial with a single `TELEM_RE` regex. Fields currently parsed include:
`timestamp`, `temp_filtered_c`, `pwm`, `p_term`, `i_term`, `d_term`, `pid_out`, `setpoint_c`, `mode`, `state`, `run_state`, `fan_speed_pct`, `vin`, `iin`, `pin`, `eq_pwm`, `enter_prog`, `exit_prog`, and more.

When firmware adds a new sensor, a named capture group must be added to `TELEM_RE` to parse it.

---

## Future Sensors & Extensibility

Three sensor types are planned for addition as hardware arrives. The system is designed to accommodate them without firmware restructuring.

**Planned sensors:**

| Sensor | CSV Fields | Interface | Status |
|--------|-----------|-----------|--------|
| Differential pressure | `delta_p1`, `delta_p2` (Pa) | I2C or analog | Not yet wired |
| Airspeed / anemometer | `airspeed` (m/s) | Analog / pulse | Not yet wired |
| Ambient humidity | `humidity_pct` (%) | I2C (e.g. SHT31) | Not yet wired |

The CSV target schema already has placeholders for `airspeed`, `delta_p1`, `delta_p2` — preserve them.

**4-step pattern to add any new sensor:**

**Step 1 — Firmware (`src/`)**
- Add a field to `CoreSensorData` in `SensorManager.h` (follow the inline comment guide there)
- Populate the field in `SensorManager::read()` in `SensorManager.cpp`
- In `main.cpp` `setup()`: call `extSensors.registerSensor("KEY", "unit")` and store the returned slot index
- In `main.cpp` `loop()`: call `extSensors.update(slotIndex, value)` each tick
- The new field will appear automatically in telemetry via `ExtSensorRegistry::emitAll()` — no format-string edits needed
- Add a `SET` command in `SerialProtocol.cpp` if the sensor needs runtime configuration (e.g. calibration offset)
- _This step requires physical access to flash the ESP32_

**Step 2 — Backend (`tools/web_gui/server.py`)**
- Add a named capture group to `TELEM_RE` for the new field
- Extract it in `_handle_line()` and add it to the `telemetry` WebSocket broadcast dict
- Add the field name to `CSV_FIELDS`
- Bump `schema_version`

**Step 3 — Frontend (`tools/web_gui/static/index.html`)**
- Receive the new field from the `"telemetry"` WebSocket message handler
- Add a readout element in the sidebar (and optionally a chart series)
- Include in Results CSV export if it's a per-run metric

**Step 4 — CSV backward compatibility**
- Old CSV files won't have the new column — that's fine if `schema_version` is present
- Update the Power Query import formula in `notes/Ideas.md` to include the new field
- Analysis scripts should check `schema_version` before expecting the new column

---

## Safety Rules for Claude (Agent Mode)

These rules apply whenever Claude works autonomously on this project.

### NEVER do without explicit user confirmation:
1. **Touch firmware** — Never edit files under `src/` (main.cpp, PIDController.cpp/h, SensorManager.cpp/h, SerialProtocol.cpp/h, SystemState.h). Never run `pio run -t upload`. Exception: `src/ExtSensorRegistry.cpp/h` may be edited to register new sensors when hardware arrives.
2. **Increase temperature limits** — The firmware accepts setpoints up to 400°C. Do not raise this ceiling.
3. **Remove or weaken safety checks** — Glitch rejection, stuck-sensor detection, anti-windup limits are safety features.
4. **Modify PWM slew-rate limiting** — `maxPwmStep` prevents abrupt heater jumps.
5. **Change heater-related pin assignments** — GPIO 4 (heater), GPIO 5 (fan). Wrong pins could cause fire.
6. **Disable the `SET RUN OFF` command** or any mechanism to cut heater power.
7. **Delete CSV log files** — These are student experiment records.
8. **Push to remote / create PRs** — Always confirm before pushing changes.

### Always do:
- Send `SET RUN OFF` at the end of any automated test sequence. Never leave the heater on unattended.
- Preserve the serial protocol structure (firmware and backend must stay in sync).
- Keep bounds-checking on all `SET` commands in firmware (if ever touching it).
- Maintain the virtual MCU simulator so the GUI works without hardware.
- When adding new telemetry fields: follow the 4-step sensor pattern above.
- When modifying CSV schema: keep `schema_version` logic intact and maintain backward compatibility.
- Keep `start.bat` working as the zero-friction Windows entry point.

---

## Code Style & Conventions

### Firmware (C++) — Locked, rarely touched
- 4-space indent, descriptive variable names
- No dynamic memory (`new`/`malloc`) — ESP32 heap fragmentation risk
- New NVS keys must have fallback defaults via `preferences.getFloat(..., default)`

### Backend (Python) — Primary target
- FastAPI async patterns throughout (`async def`, `await`)
- Single `TELEM_RE` regex — do not split into multiple passes
- New WebSocket message types: update both server send AND frontend receive handler
- CSV changes: bump `schema_version`, add field to `CSV_FIELDS`

### Frontend (JS/HTML) — Primary target
- All code lives in `index.html` — single file by design (easy distribution, no build step)
- Chart.js only — no new charting libraries
- New controls: follow existing sidebar panel pattern
- No npm/bundler/node_modules — plain HTML/JS; no build tooling ever

---

## Feature Backlog Priority

Refer to `notes/Ideas.md` for the full scored backlog. Scoring model:
```
Score = 2×Importance + 2×Necessity + 2×Dependency − Effort
```

**Current top priorities (software-only, sorted by score):**

| Score | Item | Why |
|-------|------|-----|
| 19 | Safety layer (SAFE/RUNNING/FAULT indicator + auto shutdown) | P0 — hardware safety |
| 17 | Post-test auto shutdown (`SET RUN OFF` on completion) | Heater must not stay on unattended |
| 16 | Temperature range / batch entry (start, stop, step) | Students can't add 10 temps one-by-one |
| 15 | Guided connection wizard with handshake progress | Students don't know what a COM port is |
| 15 | Airflow telemetry integration (when sensor arrives) | Core measurement for heatsink comparison |
| 14 | Auto result download on test completion | Students forget to click download |
| 13 | Startup sensor health check (INA226 + thermocouple) | Invalid data without power readings |
| 13 | Dual-file release build (installer + firmware binary) | Required for lab deployment |
| 12 | Heatsink ID input field | Students need to label their experiments |

---

## What to Ask Before Starting Any Feature

1. Does this touch firmware? → Stop and confirm with user first.
2. Can this be done in software instead of firmware? → If yes, do it in software.
3. Does this change the serial protocol? → Both `main.cpp` and `server.py` must change together.
4. Does this change CSV schema? → Must bump `schema_version`, keep backward compat.
5. Is this in the backlog? → Check `notes/Ideas.md` for acceptance criteria already written.
6. Does this affect student safety or leave the heater on? → Always confirm with user.

---

## Known Gaps (Do Not Silently "Fix")

These are known and intentional — do not add partial implementations without discussing scope first:

- **No independent safety watchdog MCU** — hardware gap, on the roadmap but requires physical build
- **Setpoint max is 400°C** — intentional ceiling for lab flexibility
- **No temperature batch entry** — students currently add temperatures one by one (backlog item)
- **No post-test auto shutdown** — heater stays on after test completes (backlog item, high priority)
- **No guided startup wizard** — connection is bare port dropdown, no wizard (backlog item)
- **Silent handshake** — no progress indicator during 2.5s connect wait (backlog item)
- **No student/instructor access levels** — all controls visible to everyone
- **No automated rise-time / settling-time metrics** — not computed yet
- **Results lost on page reload** — in-memory only, no server-side persistence of results table
