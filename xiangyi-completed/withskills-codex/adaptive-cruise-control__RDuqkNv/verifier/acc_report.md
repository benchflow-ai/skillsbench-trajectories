# ACC Simulation Report

## System design
- Two PID loops: speed control in cruise mode and distance control in follow mode.
- Mode logic: cruise when no lead, follow when lead present, emergency braking when TTC is below threshold.
- Safety features: time headway gap policy, minimum standstill gap, TTC-based emergency deceleration, and acceleration limits.

## PID tuning methodology and final gains
- Manual tuning based on rise time, overshoot, and steady-state error targets using repeated 150 s simulations.
- Speed PID: kp=0.3000, ki=0.0000, kd=0.0200.
- Distance PID: kp=0.7000, ki=0.0000, kd=0.2000.

## Simulation results and performance metrics
- Speed rise time (10-90%): 9.80 s
- Speed overshoot: 4.48%
- Speed steady-state error: 0.16 m/s
- Distance steady-state error: 1.71 m
- Distance steady-state error evaluated during closing phases (TTC defined).
- Minimum following distance: 17.50 m
