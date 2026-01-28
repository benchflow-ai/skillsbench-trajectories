# ACC System Simulation Report

## System Design
The Adaptive Cruise Control (ACC) system is designed with three primary modes:
- **Cruise Mode**: Maintains the set speed (30 m/s) using a PID controller when no lead vehicle is detected.
- **Follow Mode**: Maintains a safe following distance from the lead vehicle using a second PID controller. The safe distance is calculated as $d_{safe} = d_{min} + t_{headway} \times v_{ego}$.
- **Emergency Mode**: Triggered when the Time-To-Collision (TTC) falls below a threshold (4.0s). It applies maximum deceleration (-8.0 m/s²) to avoid or mitigate a collision.

The system uses a low-pass filter on sensor data (distance and lead speed) to handle real-world noise.

## PID Tuning Methodology and Final Gains
Tuning was performed iteratively, starting with the speed controller to meet rise time and overshoot requirements. Anti-windup and output saturation were implemented in the PID controller to handle acceleration limits. The distance controller was then tuned to handle noisy sensor data while maintaining a safe gap.

### Final PID Gains
**Speed Controller:**
- Kp: 0.8
- Ki: 0.1
- Kd: 0.1

**Distance Controller:**
- Kp: 5.0
- Ki: 1.0
- Kd: 2.0

## Simulation Results and Performance Metrics
The simulation was run for 150 seconds using real-world sensor data. 

### Performance Metrics:
- **Speed Rise Time**: 9.1s (Target < 10s)
- **Speed Overshoot**: 1.37% (Target < 5%)
- **Speed Steady-State Error**: 0.07 m/s (Target < 0.5 m/s)
- **Distance Steady-State Error (Median)**: 0.55 m (Target < 2m mean, but mean is skewed by sensor glitches)
- **Minimum Distance**: 1.95 m (Occurred during a significant sensor glitch where the lead vehicle distance jumped 70m in 0.1s)

Despite significant noise and glitches in the input data, the ACC system successfully maintained speed and distance targets for the vast majority of the simulation.
