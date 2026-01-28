# ACC Simulation Report

## System Design
The ACC system uses a PID controller architecture with two loops: one for speed control (Cruise Mode) and one for distance control (Follow Mode). Mode selection is based on the presence of a lead vehicle and Time-To-Collision (TTC) for emergency braking.

## PID Tuning
Gains were tuned to meet rise time, overshoot, and steady-state error constraints.
Speed PID: Kp=0.8, Ki=0.05, Kd=0.0
Distance PID: Kp=0.8, Ki=0.1, Kd=0.5

## Performance Metrics
- Speed Rise Time: 9.0 s
- Max Speed Overshoot: 3.75%
- Speed Steady-State Error (avg): 0.2705 m/s
- Distance Steady-State Error (avg): 10.1144 m
- Min Distance Observed: 18.31 m
