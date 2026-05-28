# HeatsinkLab Wind Tunnel — Student Guide

**Thermal Characterisation of Heatsinks**

---

> **Safety — read before touching anything**
>
> - The ceramic heater element and copper spreader plate reach high temperatures during a test. **Never touch the copper plate during or after a test** — it stays hot for several minutes after shutdown.
> - **Never turn on the lab power supply until the very last step.** All cables must be connected first.
> - If the temperature on the screen climbs unexpectedly or the system behaves oddly, click **Stop** immediately and call the lab supervisor.

---

## Part 1 — Hardware Setup

Follow these steps every time you set up the wind tunnel for a new test session.

---

### Step 1 — Mount the heatsink onto the heater module

Clip the heatsink under test firmly onto the copper spreader plate on the heater module. Press it flat — a loose heatsink gives inaccurate results.

![Install heatsink onto heater module](./media/guide/hw-01.jpeg)
![Heatsink correctly installed on heater module](./media/guide/hw-02.jpeg)

---

### Step 2 — Insert the heater module into the wind tunnel

Slide the heater module into the opening in the wind tunnel. Route the heater wire harness out through the side cutout in the plexiglass channel.

![Heater module placed into wind tunnel](./media/guide/hw-03.jpeg)

---

### Step 3 — Insert the thermocouple

Push the thermocouple probe firmly all the way into the drilled hole in the copper plate. It must be fully seated to read temperature accurately.

![Installing thermocouple into copper plate](./media/guide/hw-04.jpeg)
![Thermocouple correctly installed](./media/guide/hw-05.jpeg)

---

### Step 4 — Mount the PCB

Place the control PCB onto the heater plate module.

> **Important:** Place the isolating pad between the metal frame and the PCB before setting it down. Skipping this can cause a short circuit.

![PCB mounted onto heater plate module](./media/guide/hw-06.jpeg)

---

### Step 5 — Connect the pressure sensor cable to the sensor

The cable connector is keyed with a white tape marker. Match the white tape on the cable to the white tape mark on the pressure sensor — **direction matters**.

![Connecting cable to pressure sensor (white tape alignment)](./media/guide/hw-07.jpeg)
![Pressure sensor cable correctly connected](./media/guide/hw-08.jpeg)

---

### Step 6 — Connect the pressure sensor tubes to the wind tunnel

The silicone tubes are colour-coded. Match each tube colour to the corresponding port on the wind tunnel.

![Pressure sensor tubes connected to wind tunnel](./media/guide/hw-09.jpeg)
![Other view — colour-coded tubes](./media/guide/hw-10.jpeg)

---

### Step 7 — Connect the pressure sensor cable to the PCB

Plug the P1 connector into the P1 socket on the PCB. The white tape marker must face the same direction on both ends.

![P1 cable ready to connect to PCB (white tape alignment)](./media/guide/hw-11.jpeg)
![P1 cable correctly connected to PCB](./media/guide/hw-12.jpeg)

---

### Step 8 — Connect the heater plate cable to the PCB

The heater plate wire harness has a matching socket on the PCB. Press it in until it clicks.

![Heater plate cable ready to connect](./media/guide/hw-13.jpeg)
![Heater plate cable correctly connected to PCB](./media/guide/hw-14.jpeg)

---

### Step 9 — Connect the motor (fan) cable to the PCB

The fan motor cable also uses the white tape alignment rule. M1 on the cable connects to M1 on the PCB.

![Motor cable ready — white tape alignment, M1 to M1](./media/guide/hw-15.jpeg)
![Motor cable correctly connected](./media/guide/hw-16.jpeg)

---

### Step 10 — Connect the humidity sensor cable to the PCB

![Humidity sensor cable correctly connected to PCB](./media/guide/hw-17.jpeg)

---

### Step 11 — Verify all connectors

Step back and look at the PCB. Every connector should be fully seated. Compare with the photo below.

![All sensor cables correctly connected](./media/guide/hw-18.jpeg)

---

### Step 12 — Verify lab power supply voltage

Turn on the lab power supply briefly and confirm the display reads **12 V**. Then **turn it off again** — do not leave it on while connecting the remaining cables.

![Power supply showing 12 V — turn off before proceeding](./media/guide/hw-19.jpeg)

---

### Step 13 — Connect the power cable to the PCB

With the power supply off, plug the power cable into the PCB power connector.

![Installing power cable to PCB](./media/guide/hw-20.jpeg)
![Power cable correctly connected](./media/guide/hw-21.jpeg)

---

### Step 14 — Connect the USB-C cable to the ESP32

The USB-C port is on the ESP32 board mounted on the PCB. Connect the cable from the bench to the ESP32.

![USB-C cable connected to ESP32](./media/guide/hw-22.jpeg)

---

### Step 15 — Connect USB-C to the PC, then turn on the power supply

Plug the other end of the USB-C cable into the lab PC.

**Only now** switch on the lab power supply. Powering the rig is always the final step.

![USB-C into PC — then turn on lab power (LAST step)](./media/guide/hw-23.jpeg)

---

## Part 2 — Software Guide

---

### Step 1 — Launch the software

Double-click the **HEATSINK TESTER** shortcut on the lab PC desktop. A browser tab opens automatically at `localhost:8765`.

![Lab PC desktop with HEATSINK TESTER shortcut](./media/guide/sw-01.png)
![HEATSINK TESTER shortcut close-up](./media/guide/sw-02.png)
![HeatsinkLab Wind Tunnel GUI opens in browser](./media/guide/sw-03.png)

---

### Step 2 — Refresh the port list

After plugging in the USB cable, click the **⟳ refresh button** next to the port dropdown. The ESP32 will appear as a new COM port in the list.

![Press the refresh button after plugging in the ESP32](./media/guide/sw-04.png)

---

### Step 3 — Select the COM port

Open the port dropdown and select the entry labelled **"COM3 — USB Serial Device"** (the number may be different on your PC).

![Port dropdown open — select the USB Serial Device entry](./media/guide/sw-05.png)

---

### Step 4 — Click Connect

With the COM port selected, click **Connect**. Wait a few seconds until the status shows:

> ✅ **Connected - Device OK** &nbsp;·&nbsp; *Device verified — ready to test.*

![COM port selected, ready to click Connect](./media/guide/sw-06.png)
![Device connected and verified — test configuration visible](./media/guide/sw-07.png)

---

### Step 5 — Enter the Heatsink ID

In the **Heatsink ID** field, type the code written on your heatsink sample (for example `HS-01-fin-array`). This label is saved in the results file so you can identify the data later.

*(Refer to screenshot above — Heatsink ID field is directly below the connection panel.)*

---

### Step 6 — Set the temperature range

In the **Test Configuration** panel, enter:

| Field | Meaning | Example |
|---|---|---|
| **Start (°C)** | Lowest test temperature | `40` |
| **Stop (°C)** | Highest test temperature | `80` |
| **Step (°C)** | Gap between steps | `10` |

The preview chips (e.g. `40°C  50°C  60°C  70°C  80°C`) show exactly which temperatures will be tested.

*(Refer to screenshot above.)*

---

### Step 7 — Select wind speeds

Tick the fan speed percentages you want to include in the test. Common choices:

- **Fan OFF** — natural convection, no airflow
- **0%, 25%, 50%, 75%, 100%** — forced convection at different speeds

You can tick multiple speeds; the system will run a full temperature sweep at each selected speed automatically.

*(Refer to screenshot above.)*

---

### Step 8 — Start the test

Click the large **▶ START TEST** button. The system takes over completely from this point.

A **Test in Progress** panel appears showing:
- Current fan speed and step number
- Current status (e.g. *"Heating to 40°C…"*)
- Live readouts: **Temperature**, **Setpoint**, **Power (W)**, **Eq. PWM**, and **R_th (°C/W)**
- A real-time temperature chart

![Test in progress — live data panel and chart](./media/guide/sw-08.png)

---

### Step 9 — Wait — do not touch anything

The system works through each temperature step on its own:

1. Heats to the target temperature
2. Waits until the temperature is stable (±0.5 °C)
3. Holds for the soak period
4. Records the result
5. Moves to the next step

Typical test duration: **10–30 minutes** depending on how many steps and fan speeds are selected.

---

### Step 10 — Download the results

When all steps are complete, a **Results** table appears at the bottom of the page showing one row per temperature step.

Click **↓ Results CSV** to save the summary to your PC.

> Also save **↓ Raw CSV** if you need the full telemetry log for detailed analysis.

![Results table with download buttons](./media/guide/sw-09.png)

---

### Step 11 — Remove the heatsink and repeat

1. Wait for the temperature readout to drop below **35 °C** before handling any components.
2. Unclip the tested heatsink from the copper plate.
3. Mount the next heatsink (back to Part 1, Step 1).
4. Return to **Part 2, Step 5** — enter the new Heatsink ID and start the next test.

> **Do not disconnect the USB or restart the software** between back-to-back tests on the same session.

---

## Troubleshooting

| Symptom | What to try |
|---|---|
| COM port doesn't appear in the dropdown after plugging in USB | Press the **⟳ refresh** button; try a different USB port on the PC |
| "Connecting…" hangs indefinitely | Unplug and replug the USB cable; close and reopen the browser tab |
| Temperature reads 0 °C | Check the thermocouple plug is fully seated in the PCB connector |
| Power reads 0 W | Check the heater plate cable connector on the PCB |
| Pressure reads nothing | Check the P1 cable at both ends; white tape must align on both connectors |
| R_th shows NaN | Power reading is 0 (divide by zero) — see "Power reads 0 W" above |
| HEATSINK TESTER shortcut does nothing | Call the lab supervisor — the server may need to be restarted |
