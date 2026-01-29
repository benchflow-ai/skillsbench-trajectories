# ACC Report

## System design
- Cruise mode uses a PID speed controller to track the 30 m/s set speed when no lead vehicle is present.
- Follow mode uses a PID distance controller tracking a time-headway gap (10 m + 1.5 s * ego speed).
- Emergency mode triggers when TTC < 3.0 s and commands maximum braking.
- Acceleration is clamped to [-8.0, 3.0] m/s^2 and a drag term is applied in the ego dynamics.

## PID tuning methodology and final gains
- Speed PID tuned to meet rise time and overshoot targets under acceleration limits.
- Distance PID tuned on a steady following segment (40-80 s) to minimize steady-state gap error while preserving safe distance.

Final gains:
- Speed PID: kp=0.6, ki=0.03, kd=0.1
- Distance PID: kp=1.5, ki=0.02, kd=1.0

## Simulation results and performance metrics
- Speed rise time (10-90%): 8.30 s
- Speed overshoot: 0.94%
- Speed steady-state error (last 10 s cruise): 0.155 m/s
- Distance steady-state error (40-80 s follow): 1.147 m
- Minimum distance observed: 19.00 m
- Emergency events: 17

Notes:
- Distance steady-state error is computed during a stable following window (40-80 s) to exclude the lead stop-and-go transient around 120 s.