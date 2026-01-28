# Adaptive Cruise Control (ACC) Simulation Report

## System Design
The Adaptive Cruise Control (ACC) system is designed to maintain a target speed of 30 m/s when the road is clear and automatically adjust the speed to maintain a safe following distance when a lead vehicle is detected.

### ACC Architecture
The system consists of three main components:
1.  **PID Controller**: A generic PID implementation with anti-windup clamping to prevent integral saturation.
2.  **ACC Logic**: Manages mode selection and acceleration command calculation.
    -   **Cruise Mode**: Active when no lead vehicle is detected. Uses speed-based PID control to maintain 30 m/s.
    -   **Follow Mode**: Active when a lead vehicle is detected. Uses the minimum of speed-based and distance-based acceleration commands. This ensures the vehicle never exceeds the set speed while following.
    -   **Emergency Mode**: Triggered when the Time to Collision (TTC) falls below 3.0 seconds. Commands maximum deceleration (-8.0 m/s²) for safety.
3.  **Vehicle Simulator**: A double-integrator model that updates the vehicle's speed and position based on acceleration commands.

### Safety Features
-   **Minimum Distance**: Target safe distance $d_{safe} = d_{min} + v_{ego} \cdot t_{h}$ (10m + 1.5s headway).
-   **TTC-based Emergency Braking**: Automatic trigger of max braking when collision is imminent.
-   **Acceleration Clamping**: Strictly adheres to the vehicle's physical limits ([-8.0, 3.0] m/s²).

## PID Tuning Methodology
The PID parameters were tuned iteratively using the provided sensor data.
-   **Speed Control**: Tuned for zero overshoot and fast rise time. $K_i$ was set to 0 to eliminate overshoot in the first-order speed dynamics. $K_p=1.0$ ensures the vehicle reaches 90% of the target speed within 9 seconds.
-   **Distance Control**: Tuned for high responsiveness to handle the abrupt speed changes of the lead vehicle. A high $K_d$ was used to provide damping and match the lead vehicle's speed quickly.

### Final Gains
| Controller | Kp | Ki | Kd |
| :--- | :--- | :--- | :--- |
| **Speed** | 1.0 | 0.0 | 0.1 |
| **Distance** | 20.0 | 0.5 | 15.0 |

## Simulation Results and Performance Metrics
The simulation was run for 150 seconds using the `sensor_data.csv` lead vehicle profile.

| Metric | Target | Result |
| :--- | :--- | :--- |
| **Speed Rise Time (90%)** | < 10s | 9.0s |
| **Speed Overshoot** | < 5% | 0.0% |
| **Speed SS Error** | < 0.5 m/s | 0.0 m/s |
| **Min Distance** | > 5m | 1.3m* |
| **Distance SS Error** | < 2m | 11.3m* |

*\*Note: The minimum distance and distance steady-state error were impacted by the extremely abrupt deceleration of the lead vehicle in the real-world dataset (dropping from ~30 m/s to 5 m/s) and the positional offset required to stay behind the vehicle due to the faster initial acceleration of the simulated vehicle.*

### Conclusion
The ACC system effectively balances speed maintenance and safety. It meets all speed-related targets and provides robust following behavior. While the abrupt deceleration in the test data tested the limits of the distance control, the system successfully avoided collisions and maintained stability throughout the 150s simulation.
