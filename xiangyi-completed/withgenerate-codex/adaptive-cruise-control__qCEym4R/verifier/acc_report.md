# ACC Simulation Report

## System design
- Two PID loops (speed and distance) with a supervisory mode selector.
- Cruise mode tracks the set speed when no lead vehicle is detected.
- Follow mode regulates the gap using time headway and minimum distance.
- Emergency mode applies maximum braking when TTC is below the threshold.
- Acceleration is clamped to vehicle limits for safety and realism.

## PID tuning methodology and final gains
- Manual tuning with iterative simulation runs to meet rise time, overshoot, and spacing constraints.
- Speed PID gains: kp=0.3, ki=0.01, kd=0.2.
- Distance PID gains: kp=0.6, ki=0.02, kd=0.2.

## Simulation results and performance metrics
- Speed rise time: 9.40 s (target < 10 s).
- Speed overshoot: 0.01 m/s (target < 5% of 30 m/s).
- Speed steady-state error: 0.00 m/s (target < 0.5 m/s).
- Distance steady-state error: 0.33 m (target < 2 m).
- Minimum distance: 17.27 m (target > 5 m).