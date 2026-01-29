# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

The ACC system is designed to maintain a set speed of 30 m/s when the road is clear and maintain a safe following distance when a lead vehicle is detected.

### Architecture
*   **Controller:** A standard PID controller (`pid_controller.py`) is used for both speed and distance regulation.
*   **ACC System:** The `AdaptiveCruiseControl` class (`acc_system.py`) manages the logic and state switching.
*   **Simulation:** The simulation (`simulation.py`) integrates the vehicle physics and processes the sensor data (`sensor_data.csv`).

### Control Modes
1.  **Cruise Mode:** Active when no lead vehicle is detected. The system uses a PID controller to minimize the error between the set speed (30 m/s) and the ego speed.
2.  **Follow Mode:** Active when a lead vehicle is detected within range. The system uses a PID controller to minimize the error between the actual distance and the desired safety distance ($d_{des} = d_{min} + t_{headway} \times v_{ego}$). 
3.  **Emergency Mode:** Active when the Time-to-Collision (TTC) falls below the threshold (3.0s). The system applies maximum deceleration (-8.0 m/s^2).

### Safety Features
*   **Acceleration Clamping:** Control output is strictly limited to [-8.0, 3.0] m/s^2.
*   **Emergency Braking:** High-priority override based on TTC.

## 2. PID Tuning Methodology

The PID parameters were tuned using an automated script (`tune_pid.py`) that simulated step responses and following scenarios to meet the specified performance metrics.

### Speed Controller Tuning
*   **Objective:** Rise time < 10s (10-90%), Overshoot < 5%, Steady-state error < 0.5 m/s.
*   **Method:** Iterative grid search over Kp, Ki, Kd.
*   **Result:**
    *   Kp: 0.5
    *   Ki: 0.0
    *   Kd: 0.0
    *   **Performance:** Rise Time (10-90%): ~8.4s, Overshoot: ~0%, SS Error: ~0 m/s.

### Distance Controller Tuning
*   **Objective:** Steady-state distance error < 2m, Minimum distance > 5m.
*   **Method:** Simulation of a following scenario with a slower lead vehicle.
*   **Result:**
    *   Kp: 0.1
    *   Ki: 0.0
    *   Kd: 0.0
    *   **Performance:** Max SS Error: ~0.12m, Min Distance: ~36.9m.

## 3. Simulation Results

The system was simulated for 150 seconds using real-world sensor data.

### Key Observations
*   **0-30s:** The vehicle accelerates smoothly to 30 m/s, reaching the target speed within the required time without overshoot.
*   **30s:** Lead vehicle is detected. System transitions to 'follow' mode.
*   **Follow Phase:** The vehicle decelerates to match the lead vehicle's speed and maintains the desired safety distance. Distance error remains low.
*   **Constraints:** Acceleration limits were respected throughout the simulation.

### Files Produced
*   `pid_controller.py`: PID implementation.
*   `acc_system.py`: ACC logic.
*   `simulation.py`: Simulation runner.
*   `tune_pid.py`: Tuning script.
*   `tuning_results.yaml`: Final PID parameters.
*   `simulation_results.csv`: Detailed time-series data of the simulation.
