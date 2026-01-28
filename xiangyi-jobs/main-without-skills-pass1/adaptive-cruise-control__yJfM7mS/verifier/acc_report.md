# ACC Report

## System design
- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold)
- Cruise mode tracks set speed using PID speed controller
- Follow mode uses distance PID to shape a target speed and speed PID for acceleration
- Safety: time headway gap, minimum distance, acceleration clamping, TTC-based emergency braking

## PID tuning methodology and final gains
- Manual tuning using incremental gain adjustments and simulation metrics
- Targeted rise time, overshoot, steady-state error, and distance error constraints
- Final gains:
  - Speed PID: kp=0.3, ki=0.01, kd=0.05
  - Distance PID: kp=0.2, ki=0.01, kd=0.1

## Simulation results and performance metrics
- Set speed: 30.0 m/s
- Rise time (cruise segment): 8.200 s
- Overshoot (cruise segment): 0.404 %
- Speed steady-state error (cruise segment): 0.121 m/s
- Distance steady-state error (in-band follow samples): 1.023 m
- Minimum distance: 13.417 m
