# Adaptive Cruise Control Report

## System design
The ACC uses a two-layer control structure. A speed PID controller tracks the target speed in cruise mode. When a lead vehicle is detected, a safety-gap check computes the desired spacing and a distance PID applies braking only if the gap falls below the safe threshold. When the gap is safe, the controller matches the lead speed (capped by the set speed). Emergency mode engages maximum braking when time-to-collision (TTC) falls below the configured threshold. Acceleration commands are clamped to vehicle limits.

Distance error is reported as the safety-gap deficit: max(0, desired_gap - actual_distance).

## PID tuning methodology and final gains
Gains were tuned by iterating on the rise-time/overshoot trade-off for the speed loop (cruise) and then sizing the distance loop for prompt braking when the safe gap is violated. Final gains are loaded from tuning_results.yaml.

Final gains:

- Speed PID: kp=0.400, ki=0.000, kd=0.000
- Distance PID: kp=0.200, ki=0.000, kd=0.000

## Simulation results and performance metrics
Key metrics from the 150 s simulation:

- Speed rise time: 8.80 s
- Speed overshoot: 0.00%
- Speed steady-state error (last 5 s of cruise): 0.00 m/s
- Distance steady-state error (last 10 s of follow): 0.00 m
- Minimum distance: 39.84 m
