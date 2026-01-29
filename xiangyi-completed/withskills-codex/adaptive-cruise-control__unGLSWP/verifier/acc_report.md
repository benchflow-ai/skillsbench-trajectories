# Adaptive Cruise Control Report

## System design
- Two PID loops: speed control in cruise mode, distance control in follow/emergency modes.
- Mode logic: cruise when no lead vehicle or lead beyond detection range, follow when lead detected, emergency when TTC below threshold.
- Safety features: 1.5 s headway + 0.6 s adaptive buffer on max(ego, lead) speed, 10 m minimum gap, TTC threshold, acceleration clamping.
- Lead detection range: 55 m (beyond this, the system cruises at set speed).

## PID tuning methodology and final gains
- Manual tuning with bounded gains (kp in 0-10, ki/kd in 0-5), prioritizing rise time <10s and overshoot <5%.
- Speed PID gains: kp=0.35, ki=0.0, kd=0.2
- Distance PID gains: kp=2.0, ki=0.08, kd=0.8

## Simulation results and performance metrics
- Speed rise time (cruise segments): 9.800s
- Speed overshoot (cruise segments): 0.000%
- Speed steady-state error (cruise segments): 0.144 m/s
- Distance steady-state error (follow segments): 1.659 m
- Minimum observed distance: 29.291 m