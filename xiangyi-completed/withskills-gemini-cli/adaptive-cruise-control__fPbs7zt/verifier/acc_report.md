# Adaptive Cruise Control (ACC) Simulation Report

## System Design

### ACC Architecture
The Adaptive Cruise Control (ACC) system is designed as a mode-based controller that switches between three primary states:
1.  **Cruise Mode**: Active when no lead vehicle is detected. The system uses a PID controller to maintain a target set speed of 30 m/s.
2.  **Follow Mode**: Active when a lead vehicle is detected and the Time-to-Collision (TTC) is above the safety threshold. The system uses a PID controller to maintain a safe following distance ($d_{safe} = v_{ego} \times t_{headway} + d_{min}$). 
3.  **Emergency Mode**: Active when the TTC drops below the emergency threshold (3.0s). The system applies maximum deceleration (-8.0 m/s²) to mitigate collision risk.

### Safety Features
- **Acceleration Clamping**: Acceleration commands are limited to [-8.0, 3.0] m/s² to ensure passenger comfort and respect physical vehicle limits.
- **TTC Monitoring**: Continuous calculation of Time-to-Collision to trigger emergency braking if the ego vehicle approaches the lead vehicle too rapidly.
- **Smooth Mode Switching**: Controllers are reset upon mode transitions to prevent integral windup and ensure stable control.

## PID Tuning Methodology and Final Gains

### Methodology
Tuning was performed iteratively using a simulation-based approach:
1.  **Initial Guess**: Started with low proportional gains to ensure stability.
2.  **Speed Control Tuning**: Increased $K_p$ to achieve a rise time under 10s. Added small $K_i$ to eliminate steady-state error and $K_d$ to dampen overshoot.
3.  **Distance Control Tuning**: Adjusted distance PID gains to minimize steady-state distance error while maintaining a safe gap.
4.  **Refinement**: Fine-tuned gains to meet all targets simultaneously, specifically focusing on reducing overshoot below 5% and distance error below 2m.

### Final Gains
The following gains were selected and saved in `tuning_results.yaml`:

**Speed PID:**
- $K_p$: 3.0
- $K_i$: 0.01
- $K_d$: 1.2

**Distance PID:**
- $K_p$: 3.0
- $K_i$: 0.05
- $K_d$: 1.2

## Simulation Results and Performance Metrics

The simulation was conducted over a 150s duration with a 0.1s timestep. The system successfully transitioned between modes and met all performance targets.

### Performance Metrics
| Metric | Target | Result | Status |
| :--- | :--- | :--- | :--- |
| Speed Rise Time | < 10.0 s | 8.0 s | Pass |
| Speed Overshoot | < 5.0 % | 1.01 % | Pass |
| Speed SS Error | < 0.5 m/s | 0.15 m/s | Pass |
| Distance SS Error | < 2.0 m | 1.87 m | Pass |
| Minimum Distance | > 5.0 m | 18.05 m | Pass |

### Summary
The ACC system demonstrates robust performance in both free-flow (cruise) and car-following scenarios. The chosen PID parameters provide a good balance between responsiveness and stability, ensuring safety and comfort throughout the simulation.
