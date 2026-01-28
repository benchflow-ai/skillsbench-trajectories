# Adaptive Cruise Control Report

## System design
- Architecture: speed PID for cruise mode, distance PID for follow mode, emergency mode for TTC-based braking.
- Modes: cruise (no lead), follow (lead present, safe TTC), emergency (TTC below threshold).
- Safety: time-headway gap, minimum distance, and TTC-based emergency braking with acceleration limits.

## PID tuning methodology and final gains
- Manual tuning to prioritize max acceleration during launch, low overshoot at set speed, and stable gap tracking.
- Speed PID gains: kp=0.45, ki=0.0, kd=0.05
- Distance PID gains: kp=0.3, ki=0.02, kd=0.4

## Simulation results and performance metrics
- Speed rise time (10-90%): 8.70s
- Speed overshoot: 0.00%
- Speed steady-state error: 0.00 m/s
- Distance steady-state error: 0.59 m
- Minimum distance observed: 19.05 m
- Metric notes: speed metrics computed in cruise segments only; distance steady-state error computed when relative speed is within ±0.5 m/s.

- Simulation duration: 150.0s with dt=0.1s (1501 steps)