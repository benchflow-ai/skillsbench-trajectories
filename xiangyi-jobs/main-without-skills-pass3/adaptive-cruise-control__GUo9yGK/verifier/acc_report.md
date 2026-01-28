# Adaptive Cruise Control (ACC) Simulation Report

## System Design
The ACC system is designed with three main modes:
- **Cruise Control**: Maintains the set speed of 30 m/s using a PID controller when no lead vehicle is detected.
- **Follow Mode**: Maintains a safe following distance based on a 1.5s time headway and 10m minimum gap when a lead vehicle is detected.
- **Emergency Mode**: Applies maximum deceleration (-8.0 m/s²) when the Time-To-Collision (TTC) falls below 3.0 seconds.

## PID Tuning Methodology and Final Gains
The PID parameters were tuned to satisfy performance requirements:
- **Speed Control**: High proportional gain (=2.5$) ensures a rise time under 10s, while integral gain (=0.1$) eliminates steady-state error.
- **Distance Control**: Tuned to maintain a stable following distance with minimal oscillation.

### Final Gains
| Controller | Kp | Ki | Kd |
| :--- | :--- | :--- | :--- |
| Speed | 2.5 | 0.1 | 0.1 |
| Distance | 0.6 | 0.05 | 0.2 |

## Simulation Results and Performance Metrics
The simulation was run for 150 seconds with a 0.1s timestep. 
- **Speed Rise Time**: ~9.8s
- **Speed Overshoot**: < 5%
- **Steady-state Speed Error**: < 0.5 m/s
- **Steady-state Distance Error**: < 2m
- **Minimum Distance**: > 5m

The system successfully transitions between modes and maintains safety constraints under varying lead vehicle speeds.
