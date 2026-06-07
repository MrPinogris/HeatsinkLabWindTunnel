# HeatsinkLab Carrier Board — KiCad Project

Open `heatsinklab.kicad_pro` in KiCad 8.

## Files
- `heatsinklab.kicad_pro` — project settings and net classes
- `heatsinklab.kicad_sch` — full schematic
- `heatsinklab.kicad_pcb` — PCB layout (160 mm × 120 mm)

## After opening in KiCad

1. **Schematic**: Run *Tools → Update PCB from Schematic* to sync any edits.
2. **PCB**: Run the DRC, then route the remaining ratsnest connections.  
   Use the **Zone** tool (copper pour) for the GND plane.
3. **Footprints**: All standard KiCad 8 library footprints — no custom libs needed.

## Net classes (already configured)

| Class | Track width | Applies to |
|-------|-------------|------------|
| Default | 0.25 mm | GPIO signals, I2C, SPI |
| Power | 2.0 mm | +12V, GND, HEATER*, FAN_PWR* |

## Heater path warning

The +12V → Q1 → INA226 → J2 trace carries up to ~3–5 A.  
Route it as a **wide copper pour zone** (≥5 mm) or solder wire on top of the copper tape.

## Board dimensions

160 mm × 120 mm, 4× M3 mounting holes at corners.

## Component placement (as placed in PCB file)

| Ref | Component | XY (mm) |
|-----|-----------|---------|
| J1  | PWR_IN 2p | 12, 15 |
| J2  | HEATER_OUT 2p | 12, 35 |
| J4  | FAN_OUT 2p | 12, 50 |
| J5  | FAN_PWM 2p | 12, 65 |
| J6  | THERMO 5p | 148, 15 |
| J7  | INA226 4p | 148, 40 |
| J8  | SDP510 4p | 148, 60 |
| J9  | EZO-HUM 4p | 148, 80 |
| J10 | EXT1 4p | 148, 100 |
| Q1  | IRLZ44N Heater | 50, 30 |
| Q2  | IRLZ44N Fan | 50, 55 |
| R1  | 4.7k SDA pull-up | 120, 38 |
| R2  | 4.7k SCL pull-up | 120, 48 |
| R3  | 10k Q1 gate pull-down | 35, 30 |
| R4  | 10k Q2 gate pull-down | 35, 55 |
| U1  | ESP32-S3 dev board header | 80, 60 |
