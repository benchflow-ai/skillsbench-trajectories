# ACC Simulation Report

## System design
- Modes: cruise (speed hold), follow (gap control), emergency (TTC-based braking).
- Safety: TTC threshold triggers max deceleration; accel commands are bounded by vehicle limits.
- Gap policy: desired gap = min_distance + time_headway * ego_speed.
- Lead distance initializes from sensor data when a lead vehicle first appears, then evolves with relative speed.

## PID tuning methodology and final gains
Gains loaded from tuning_results.yaml and applied at runtime.

Final gains:
- Speed PID: kp=0.3, ki=0.0, kd=0.0
- Distance PID: kp=0.1, ki=0.1, kd=0.05

## Simulation results and performance metrics
- Speed rise time (10-90%): 9.70s
- Speed overshoot: 2.83%
- Speed steady-state error (last 10s): -0.01 m/s
- Distance steady-state error (last 10s w/lead): -1.47 m
- Minimum distance observed: 18.87 m
