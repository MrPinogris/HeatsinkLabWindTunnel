# Todo

## Hardware

- [ ] **Documentation** — complete hardware component list and datasheets
- [ ] **Architecture** — all sensors should be easily implementable; string output updated automatically when new sensors are added
    - [ ] **Implementation** of humidity sensor
        - [x] EZO-HUM I²C probe implemented and tested
        - [ ] Make expandable for additional humidity sensors
    - [x] **Implementation** of temperature sensor
        - [x] MAX6675 K-type thermocouple implemented and tested
        - [ ] Make expandable (inlet/outlet air temp sensors)
    - [x] **Implementation** of pressure sensor
        - [x] Sensirion SDP510 differential pressure implemented (replaced SDP2000-L analog)
        - [ ] Second pressure channel pending hardware
    - [ ] **Implementation** of airflow / anemometer sensor
        - [ ] Select sensor (hot-wire, Pitot, or ultrasonic)
        - [ ] Implement and test
- [x] **Architecture** — firmware telemetry string is read by server.py even as new sensors are added
    - [x] ExtSensorRegistry provides named slots — backend TELEM_RE regex accepts new named fields
- [ ] **Sensor validation** — test INA226 power measurement accuracy under load; investigate possible power losses through MOSFET resistance

## PCB

- [ ] **Design** PCB to replace dev-board wiring
    - [ ] Define standard expansion connector type and pinout (power, GND, data lines)
    - [ ] Reserve at least 2 spare expansion headers for future sensors
    - [ ] Document connector electrical limits (voltage, current, max sensor load)
    - [ ] Create sensor slot map (I²C, SPI, analog, UART) with address-conflict rules
    - [ ] Add jumper / DIP options for configurable I²C addressing
    - [ ] Add test points for power rails and sensor data lines
    - [ ] Define software sensor-configuration table format (type, bus, address, label)
    - [ ] Validate full expansion flow with one mock sensor before PCB release
    - [ ] Implement PCB and verify all connections

## Software — Firmware (`src/`)

- [x] Refactor serial communication into SerialProtocol.cpp
- [x] Refactor sensor reads into SensorManager.cpp
- [x] Modular architecture with classes (PIDController, SensorManager, ExtSensorRegistry)
- [x] SMART mode: PID until stable, then lock equilibrium PWM
- [x] SMART HOLD: fix stuck-on-SP-change bug
- [x] INA226 power monitoring integrated into telemetry
- [x] SDP510 differential pressure integrated into telemetry
- [x] EZO-HUM humidity probe integrated into telemetry
- [x] Fan power MOSFET (GPIO 10) for complete fan cut-off
- [x] FANPWR serial command (`SET FANPWR ON/OFF`)
- [x] Thermocouple fault detection → immediate heater cut
- [x] Stuck-sensor watchdog → heater cut

## Software — Backend (`tools/web_gui/server.py`)

- [x] FastAPI + WebSocket server on port 8765
- [x] TELEM_RE regex parses all telemetry fields including sensors
- [x] CSV logger with schema_version header (current: v4)
- [x] Humidity and pressure fields in CSV_FIELDS
- [x] Pressure zero / tare endpoint (`/api/pressure_tare`)
- [x] Ambient temperature endpoint (`/api/ambient`)
- [x] Virtual MCU simulator (VIRTUAL port)
- [x] Fan power state tracked in VirtualMCU
- [x] Run ID and Heatsink ID in CSV header metadata
- [ ] Post-test auto shutdown (`SET RUN OFF` on test completion) — **P0 safety item**
- [ ] Guided connection wizard with handshake progress indicator
- [ ] Startup sensor health check (INA226 + thermocouple validation)

## Software — Frontend (`tools/web_gui/static/index.html`)

- [x] Real-time Chart.js dual-axis graph (temperature + PWM)
- [x] PID parameter tuning sliders
- [x] AUTO / MANUAL / SMART mode selection
- [x] INA226 current, voltage, power readout
- [x] Tester mode with automated temperature stepping (SMART mode)
- [x] Tester: Fan ON / Fan OFF condition selector (uses GPIO 10 MOSFET)
- [x] Tester: per-temperature fan and condition recorded in Results CSV
- [x] Tester: ambient temperature auto-fill from main panel
- [x] Tester: humidity_pct column in Results CSV
- [x] Results table with EqPWM, Power_W, R_th, k per step
- [x] Expert / Student mode toggle
- [x] Performance metrics (rise time, settle time, overshoot, IAE)
- [x] Graph cursor / crosshair probe tool
- [x] CSV column customisation dialog with Power Query formula
- [x] Phase markers (📌 Marker button → chart + CSV annotation)
- [x] Presets (save / load / delete named configurations)
- [x] Pressure sensor tare / reset zero UI
- [x] Run ID and Heatsink ID fields (mirrored between Normal and Tester panels)
- [ ] Temperature range / batch entry (start, stop, step → generate list) — **P1**
- [ ] Auto result download on test completion — **P1**
- [ ] Safety layer: persistent SAFE / RUNNING / FAULT status indicator — **P0**
- [ ] Post-test auto shutdown UI confirmation — **P0**
- [ ] Guided connection wizard — **P1**
- [ ] Startup sensor health check display — **P1**

## Release / Deployment

- [ ] Dual-file release build: GUI installer (.bat / .exe) + pre-compiled firmware binary (.bin)
- [ ] Version number in GUI footer and firmware CFG output for mismatch detection
- [ ] Lab technician setup guide (no dev tools required)
