# ACC Report

## System design
- Architecture: PID-based speed control for cruise, PID-based distance control for follow, with emergency braking on low TTC.
- Modes: cruise when no lead vehicle, follow when lead present, emergency when TTC below threshold.
- Safety features: acceleration clamping, minimum speed clamp at 0 m/s, emergency deceleration.

## PID tuning methodology and final gains
- Manual tuning guided by rise time, overshoot, steady-state error, and distance error targets.
- Final speed PID gains: kp=0.5, ki=0.01, kd=0.2.
- Final distance PID gains: kp=0.25, ki=0.1, kd=0.2.

## Simulation results and performance metrics
- Speed metrics computed on the initial cruise segment (no lead vehicle).
- Distance metrics computed on the follow segment (lead present).
- Speed rise time: 8.500 s (target < 10 s).
- Speed overshoot: 0.010 % (target < 5%).
- Speed steady-state error: 0.000 m/s (target < 0.5 m/s).
- Distance steady-state error: 1.912 m (target < 2 m).
- Minimum distance: 16.168 m (target > 5 m).