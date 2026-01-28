# ACC Simulation Report

## System design
- Architecture: supervisory PID control; speed PID tracks set speed, distance PID applies braking when the gap shortfall (desired gap minus actual distance) is positive.
- Modes: cruise (no lead), follow (lead present), emergency (TTC < 3.0s).
- Safety features: time headway 1.5s, minimum gap 10.0m, acceleration limits from vehicle config.
- Distance error definition: desired gap minus actual distance; values are floored at 0 when the gap is safe.

## PID tuning methodology and final gains
- Manual tuning with step response checks for rise time, overshoot, and steady-state error while ensuring safe distance tracking during follow mode.
- Speed PID: kp=0.4, ki=0.0, kd=0.05
- Distance PID: kp=0.4, ki=0.0, kd=0.0

## Simulation results and performance metrics
- Control duration: 150s, timestep 0.1s, set speed 30.0 m/s.
- Speed rise time (0-90%): 9.90s
- Speed overshoot: 0.00%
- Speed steady-state error: 0.006 m/s
- Distance steady-state error: 0.000 m
- Minimum observed distance: 14.62 m
