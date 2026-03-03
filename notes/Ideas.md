## PID GUI Ideas (Student Lab Focus)

1. Experiment Presets
- Save/load full test setups (SP, mode, gains, fan, thresholds, y-scale).
- One-click presets like `Step Response`, `Disturbance Test`, `Manual Bias Find`.

2. Guided Lab Mode
- Wizard flow: `Connect -> Preheat -> Run -> Disturb -> Analyze -> Save`.
- Lock irrelevant controls per step to reduce mistakes.

3. Auto Test Scripts
- Scripted sequences:
  - Setpoint steps (`30 -> 60 -> 80 C`)
  - Fan disturbance pulse
  - Hold test (steady-state)
- Write phase markers to CSV.

4. Performance Metrics Auto-Compute
- Show `rise time`, `settling time`, `overshoot`, `steady-state error`, `IAE/ISE`.
- Compute metrics per phase and export.

5. Cursor/Probe Tool
- Click graph to read exact values at time `t`.
- Delta mode between two points: `ΔT`, `ΔPWM`, `Δt`, slope.

6. Annotation Markers
- Buttons to add markers (`Fan ON`, `Heatsink Changed`, `Mode Switch`) to CSV/log.
- Draw vertical marker lines with labels on graph.

7. Safety Layer
- Configurable max-temp cutoff, max-PWM duration, sensor-fault lockout.
- Big status indicator: `SAFE / RUNNING / FAULT`.

8. Heatsink Comparison View
- Overlay multiple runs from CSV.
- Normalize time to event (e.g., step start).
- Compare key metrics side by side.

9. Student Report Export
- Generate PDF/HTML report with:
  - Graphs
  - Config used
  - Metrics
  - Student notes
  - Pass/fail checks

10. PID Learning Overlay
- Show `P`, `I`, `D`, and output decomposition with hints:
  - High overshoot: lower `Kp` or raise `D`
  - Steady-state offset: increase `Ki` or bias

11. Access Levels
- `Student mode`: limited controls.
- `Instructor mode`: full tuning, thresholds, scripting.

12. Scoring/Checklist
- Define rubric targets (e.g., overshoot < 5%, settling < 120s).
- Auto-score each run for objective grading.

## Suggested Next Two

1. Add phase markers + annotations in CSV/graph.
2. Add automatic rise/settling/overshoot metrics panel.
