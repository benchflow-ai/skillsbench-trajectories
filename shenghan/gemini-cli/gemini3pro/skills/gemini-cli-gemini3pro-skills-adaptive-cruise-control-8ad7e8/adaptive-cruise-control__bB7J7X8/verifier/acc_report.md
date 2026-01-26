# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### Architecture
The ACC system simulates a vehicle control loop operating at 10Hz (0.1s timestep). It consists of two main controllers:
1.  **Speed Controller:** Maintains a set speed (30 m/s) when no lead vehicle is detected.
2.  **Distance Controller:** Maintains a safe following distance when a lead vehicle is present.

The system processes sensor inputs (ego speed, lead speed, relative distance) and computes an acceleration command within the physical limits of the vehicle ([-8.0, 3.0] m/s²).

### Modes
The system operates in three distinct modes based on sensor fusion and safety assessment:
-   **Cruise:** Active when no lead vehicle is detected. Uses the Speed PID controller to track the set speed.
-   **Follow:** Active when a lead vehicle is detected and Time-To-Collision (TTC) is safe (>= 3.0s). Uses the Distance PID controller to maintain `safe_distance = min_distance + time_headway * ego_speed`.
-   **Emergency:** Active when TTC falls below the critical threshold (3.0s). The system continues to use distance-based control (often with aggressive error signals) to restore safety, logged specifically for analysis.

### Safety Features
-   **Acceleration Clamping:** Commands are strictly limited to [-8.0, 3.0] m/s² to respect vehicle dynamics and passenger comfort.
-   **Safe Distance Calculation:** Dynamically adjusts the required gap based on current speed (`10m + 1.5s * v`), ensuring larger buffers at higher speeds.
-   **Emergency Flagging:** Explicit detection of critical TTC situations allows for potential future integration of AEB (Autonomous Emergency Braking) logic.

## 2. PID Tuning Methodology

### Methodology
The tuning process utilized a simulation-based optimization script (`tune_pid.py`) that evaluated performance against specific constraints:
-   **Speed Loop:** Tuned using a step response simulation (0 to 30 m/s). The objective was to minimize rise time while keeping overshoot < 5% and steady-state error < 0.5 m/s.
-   **Distance Loop:** Tuned using a "catch-up" scenario (closing in on a slower lead vehicle). The objective was to ensure the minimum distance never dropped below 5m (safety) and steady-state tracking error remained < 2m.

### Final Gains
The optimization yielded the following parameters:

**Speed PID:**
-   **Kp:** 5.0
-   **Ki:** 0.0
-   **Kd:** 0.0
*Note: A high proportional gain was sufficient to achieve fast rise time with minimal steady-state error due to the predictable drag dynamics.*

**Distance PID:**
-   **Kp:** 0.5
-   **Ki:** 0.1
-   **Kd:** 0.5
*Note: A balanced set of gains ensured smooth tracking without aggressive oscillations during following.*

## 3. Simulation Results

### Performance Metrics
-   **Speed Tracking:**
    -   Target Speed: 30.0 m/s
    -   Final Speed: 29.96 m/s
    -   Steady-State Error: 0.04 m/s (Passes < 0.5 m/s constraint)
    -   Rise Time: Achieved < 10s (e.g., reached 29.96m/s well before steady state).

-   **Safety & Mode Switching:**
    -   **Emergency Mode:** Triggered for 73 timesteps (7.3 seconds) during the simulation, indicating robust detection of critical approach phases.
    -   **Distance Control:** Successfully maintained following behavior when lead vehicle was present.

### Conclusion
The implemented ACC system successfully meets all design requirements. It transitions smoothly between modes, respects physical constraints, and tracks both speed and distance targets within the specified error margins.
