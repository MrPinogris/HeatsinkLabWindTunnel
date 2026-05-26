# HeatsinkLab Wind Tunnel — Hardware Reference

This document is the complete hardware reference for the HeatsinkLab Wind Tunnel platform. It covers all components, connections, I²C bus layout, power distribution, and physical assembly details.

For photos of the physical build see `docs/media/`.

---

## Bill of Materials

| Qty | Component | Part / Variant | Role |
|---|---|---|---|
| 1 | Microcontroller | ESP32-S3 DevKit-C1 | Main controller, USB serial, WiFi (reserved) |
| 1 | Thermocouple module | MAX6675 breakout (K-type) | Heatsink base temperature measurement |
| 1 | Thermocouple | K-type, 1 m, with stainless probe | Inserted into copper spreader plate |
| 1 | Power monitor | INA226 breakout (A0 → VCC, addr 0x41) | Heater current, voltage, and power measurement |
| 1 | Differential pressure sensor | Sensirion SDP510 (I²C, addr 0x40) | Airflow differential pressure across tunnel |
| 1 | Humidity probe | Atlas Scientific EZO-HUM (I²C, addr 0x6F) | Ambient relative humidity and temperature |
| 2 | MOSFET switch module | Generic PWM MOSFET module (e.g. BTS7960 or IRF520) | Heater power switching (PWM), Fan power cut-off |
| 1 | Fan | 12 V DC brushless fan with PWM input | Forced convection through wind tunnel |
| 1 | Ceramic PTC heater | 12 V ceramic heater plate | Heat source for heatsink under test |
| 1 | Copper spreader plate | Custom machined, with thermocouple hole | Uniform heat distribution onto heatsink |
| 1 | Hexagonal grid / honeycomb | 3D printed or purchased | Laminar flow conditioning at fan inlet |
| 1 | Fan guard / shield | 3D printed or purchased | User safety — prevents finger contact with fan |
| 1 | Lab power supply | 12 V DC, ≥ 5 A | Power for heater and fan |
| — | Dev board / perfboard | Custom | Mounts MOSFET modules, ESP32, and connectors |

---

## ESP32-S3 Pin Assignments

| GPIO | Function | Direction | Notes |
|---|---|---|---|
| 4 | Heater MOSFET gate | Output | PWM 500 Hz, 8-bit (0–255). LEDC channel. |
| 5 | Fan PWM signal | Output | PWM 500 Hz, 8-bit. LEDC channel. Fan driver PWM input. |
| 10 | Fan power MOSFET gate | Output | HIGH = fan powered, LOW = fan fully off. Digital only. |
| 11 | MAX6675 SO (MISO) | Input | SPI — thermocouple serial data |
| 12 | MAX6675 CS | Output | SPI — chip select (active LOW) |
| 13 | MAX6675 SCK | Output | SPI — clock |
| 15 | I²C SDA | Bidirectional | Shared bus: INA226, SDP510, EZO-HUM |
| 16 | I²C SCL | Output | Shared bus |

---

## I²C Bus Map

All three I²C sensors share GPIO 15 (SDA) and GPIO 16 (SCL). Address conflicts are avoided by hardware configuration:

| Device | Address | How set |
|---|---|---|
| INA226 power monitor | 0x41 | A0 pin wired to VCC (≠ default 0x40) |
| Sensirion SDP510 pressure | 0x40 | Fixed in silicon — not configurable |
| EZO-HUM humidity probe | 0x6F | Factory default I²C address (after mode switch) |

> **Note:** `Wire.setTimeOut(200)` is set in firmware. The SDP510 uses I²C clock-stretching during measurement (up to 80 ms); the extended timeout prevents false read errors.

---

## Power Distribution

```
12 V Lab PSU (+) ────┬──── Heater MOSFET IN+
                     └──── Fan MOSFET (power cut-off) IN+

12 V Lab PSU (−) ────┬──── Heater MOSFET IN−
                     ├──── Fan MOSFET IN−
                     └──── ESP32 GND  ←── common ground reference
```

### Heater Circuit (PWM controlled via GPIO 4)

```
12 V (+) → Heater MOSFET IN+
           Heater MOSFET OUT+ ──→ Heater element (+)
           Heater element (−) ──→ INA226 IN+  [shunt resistor]
                                  INA226 IN−  ──→ Heater MOSFET OUT−
12 V (−) → Heater MOSFET IN−  (common GND)

GPIO 4  → Heater MOSFET signal
ESP GND → Heater MOSFET signal GND
```

The INA226 shunt is placed in series with the heater element, measuring current flow through it directly.

### Fan Circuit (PWM via GPIO 5, power enable via GPIO 10)

```
12 V (+) → Fan power MOSFET IN+
           Fan power MOSFET OUT+ ──→ Fan supply (+)
12 V (−) → Fan power MOSFET IN−  (common GND)

GPIO 5  → Fan PWM signal (speed control)
GPIO 10 → Fan power MOSFET gate  (HIGH = on, LOW = fully off)
ESP GND → Fan MOSFET signal GND
```

GPIO 10 allows the fan to be completely de-energised for natural-convection tests, regardless of the PWM duty cycle.

---

## Sensor Wiring

### MAX6675 Thermocouple Module

| MAX6675 Pin | Wire colour (typical) | Connects to |
|---|---|---|
| VCC | Red | ESP32 3.3 V |
| GND | Black | ESP32 GND |
| SCK | Yellow | GPIO 13 |
| CS  | Orange | GPIO 12 |
| SO  | Green | GPIO 11 |

The K-type thermocouple probe tip is inserted into the precision hole in the copper spreader plate. The copper plate sits on top of the ceramic heater; the heatsink under test is clamped onto the top face of the copper plate.

### INA226 Power Monitor

| INA226 Pin | Connects to | Notes |
|---|---|---|
| VCC | ESP32 3.3 V | |
| GND | ESP32 GND | |
| SDA | GPIO 15 | Shared I²C bus |
| SCL | GPIO 16 | Shared I²C bus |
| A0  | ESP32 3.3 V | Sets address to 0x41 |
| A1  | ESP32 GND | |
| IN+ | Heater element output | High side of shunt |
| IN− | Heater MOSFET drain | Low side of shunt |
| ALE | Not connected | |
| VBS | Not connected | |

Firmware configuration: 1024-sample averaging, 8.3 ms conversion time per channel, calibrated for the installed shunt resistor value.

### Sensirion SDP510 Differential Pressure

| SDP510 Pin | Connects to | Notes |
|---|---|---|
| VDD | ESP32 3.3 V | |
| GND | ESP32 GND | |
| SDA | GPIO 15 | Shared I²C bus |
| SCL | GPIO 16 | Shared I²C bus |

The sensor is mounted so that Port 1 faces the upstream side (fan outlet) and Port 2 faces downstream (heatsink outlet) of the tunnel, measuring the net pressure drop. Range: ±500 Pa. Scale factor: 60 counts/Pa.

### EZO-HUM Humidity Probe (Atlas Scientific)

| EZO-HUM Pin | Wire colour | Connects to | Notes |
|---|---|---|---|
| VCC | Red | ESP32 3.3 V | |
| GND | Black | ESP32 GND | |
| SDA | Green | GPIO 15 | Shared I²C bus |
| SCL | White | GPIO 16 | Shared I²C bus |
| AUTO | Blue | Not connected | Leave floating |

> **One-time I²C mode activation:** Factory default is UART mode (LED blinks green).
> Connect to a USB-UART adapter, open a serial terminal at 9600 baud, send `I2C,111\r`,
> then power-cycle. The LED turns solid blue confirming I²C mode. Address 0x6F.

---

## Connector Layout on Dev Board

From the Connections.txt wiring document (left to right on the sensor connector rail):

```
[ Humidity sensor ]  [ Pressure sensor ]  [ Fan motor ]
      Left                 Middle              Right
```

Between the pressure sensor connector and the fan motor connector there is an additional MOSFET module for the fan power cut-off (GPIO 10). This module is not shown in all photos.

---

## Physical Assembly

### Wind Tunnel

- Fan is mounted at the inlet end of the tunnel
- A hexagonal (honeycomb) grid is placed directly in front of the fan blades to break up turbulence and produce laminar airflow
- A protective shield covers the fan face on the outside of the tunnel to prevent accidental contact

Photos in `docs/media/`:
- `Fan at beginning of windtunnel with hexagonal grid in front to get laminar windflow.HEIC`
- `fan at beginning of windtunnel and the protective outside shield visible (protection for user).HEIC`
- `fan at beginning of windtunnel seen from inside of the tunnel and the hexgrid also visible.HEIC`
- `full windtunnel (incomplete) no side panel attached yet.HEIC`

### Heater Module

The heater module is a layered assembly (bottom to top):
1. **Ceramic PTC heater plate** — 12 V, controlled via MOSFET
2. **Copper spreader plate** — sits directly on top of the ceramic heater, machined with a small blind hole in one edge for the thermocouple probe tip
3. **Thermocouple** — K-type probe inserted into the copper plate hole; measures the temperature at the base of the heatsink
4. **Heatsink under test** — clamped onto the top face of the copper plate

Photos in `docs/media/`:
- `heater module with only ceramic heater and ceramic heater visible.HEIC`
- `heater module with ceramic heater visible and the copper plate placed vertically to show where the hole for thermocouple when place horizontally.HEIC`
- `heater module where the copper plate that is on top of the ceramic heater is visible (thermocouple is placed inside this copper) bit no heatsinc attached.HEIC`
- `heater module but only copper plate visible and partially sticking out to show the thermocouple placed inside.HEIC`
- `fulle heater module without thermocouple inside yet.HEIC`
- `full heater module with heatsinc visible and thermocouple inside.HEIC`
- `Full heater module with heatsinc visible and thermocouple inside 2.HEIC`
- `Thermocouple that goes in the Copper plate of the heater module.HEIC`

### Dev Board

- ESP32-S3 DevKit-C1 mounted centrally
- Two MOSFET switch modules: one for heater (PWM), one for fan power cut-off (digital)
- INA226 breakout mounted near the heater MOSFET (shunt leads kept short)
- Sensor connector rail (left to right): humidity, pressure, fan motor

Photos in `docs/media/`:
- `Full devboard with esp(unfinished) missing 1 more mossfet module to the left for the power cutoff to fan.HEIC`
- `Full devboard without esp(unfinished) missing 1 more mossfet module to the left for the power cutoff to fan.HEIC`
- `power connector and PWM out module to Heateplate and part of USBC connection from ESP to PC.HEIC`
- `Left humidity sensor connector midle Preassure sensor connector right Motor connector (between P1 and M1 there's now a Mossfet module now that can cut power to M1 also but this is not in pic).HEIC`

### Sensors

Photos in `docs/media/`:
- `humididty sensor.HEIC` — EZO-HUM humidity probe
- `Pressure diff Sensor.HEIC` — Sensirion SDP510 differential pressure sensor

---

## Safety Notes

- Maximum operating temperature: 400 °C (firmware setpoint ceiling). Lab usage typically 40–120 °C.
- The ceramic heater element stays energised until `SET RUN OFF` is sent or the GUI disconnects. Never leave the system unattended with `RUN: ON`.
- If the thermocouple reads 0 °C, NaN, or produces a stuck-sensor fault, the firmware cuts heater power immediately.
- The INA226 must be wired and responding before starting a test. If power reads 0, R_th results will be invalid (NaN or ∞).
- Common GND between the lab PSU and the ESP32 is required for MOSFET gate signals to work correctly.

---

## Planned Hardware Additions

| Sensor | Interface | Purpose | Status |
|---|---|---|---|
| Second SDP510 port or anemometer | Analog / I²C | Direct airspeed measurement (m/s) | Not yet wired |
| Second differential pressure channel | I²C | Redundant or two-point pressure | Parser ready, hardware pending |
| Additional temperature sensors | SPI (additional MAX6675 slots) | Inlet / outlet air temperature | Not yet wired |

See `notes/Ideas.md` for feature backlog and prioritisation.
