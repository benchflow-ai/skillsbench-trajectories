# ACC Report

## System design
- **Architecture:** A two-loop controller. A distance PID produces a speed correction in follow mode, and a speed PID converts the target speed into acceleration. Cruise mode uses only the speed PID to track the set speed.
- **Modes:**
  - **Cruise:** Active when no lead is detected. Tracks the set speed (30 m/s).
  - **Follow:** Active when a lead vehicle is present. Desired gap is `min_distance + time_headway * ego_speed`. The distance PID outputs a speed correction added to lead speed; the speed PID tracks the resulting target speed.
  - **Emergency:** Triggered when TTC < 3.0 s. A safe target speed is computed as `lead_speed + distance / TTC_threshold` and the speed PID brakes toward that target.
- **Safety features:** Acceleration commands are clamped to vehicle limits [-8.0, 3.0] m/s². Minimum gap tracking is enforced via the distance PID and TTC-based emergency logic.

## PID tuning methodology and final gains
- **Method:** Manual, iterative tuning against rise time, overshoot, steady-state error, minimum distance, and TTC behavior. Speed gains were reduced to avoid overshoot while keeping rise time < 10 s. Distance gains were increased until steady gap tracking was achieved without violating the minimum distance.
- **Final gains (from `tuning_results.yaml`):**
  - **Speed PID:** kp=0.4, ki=0.0, kd=0.05
  - **Distance PID:** kp=0.8, ki=0.2, kd=0.2

## Simulation results and performance metrics
- **Duration / dt:** 150 s, 0.1 s timestep (1501 samples).
- **Lead present:** 30.0–129.9 s (from sensor data).
- **Cruise performance (0–30 s):**
  - Rise time (10%→90%): **8.9 s**
  - Overshoot: **0.0%**
  - Speed steady-state error (20–30 s mean): **0.02 m/s**
- **Following performance (steady window 60–90 s):**
  - Distance steady-state error (mean): **0.06 m**
- **Safety:**
  - Minimum distance: **5.22 m** (> 5 m)
  - Minimum TTC: **0.97 s** (emergency braking engaged around 120 s)

Overall, the ACC maintains the set speed in cruise, adapts speed to hold the desired gap during steady following, and preserves a safe minimum distance during emergency deceleration events.
