# Adaptive Cruise Control (ACC) Simulation Report

## 1. System Design

### ACC Architecture

The ACC system is composed of three modules:

- **PIDController** (`pid_controller.py`): A discrete-time PID controller with anti-windup clamping. Implements proportional, integral, and derivative terms with output saturation and integral back-calculation to prevent windup.

- **AdaptiveCruiseControl** (`acc_system.py`): The core ACC logic that manages two PID controllers (speed and distance) and selects the operating mode based on sensor inputs.

- **Simulation** (`simulation.py`): Reads vehicle parameters and tuned PID gains from YAML files, loads lead vehicle data from `sensor_data.csv`, and runs the 150-second kinematic simulation producing `simulation_results.csv`.

### Operating Modes

| Mode | Condition | Behavior |
|------|-----------|----------|
| **Cruise** | No lead vehicle detected | Speed PID maintains set speed (30 m/s) |
| **Follow** | Lead vehicle present, TTC >= 3.0s | Distance PID maintains safe following distance; speed PID acts as upper limiter |
| **Emergency** | TTC < 3.0s | Maximum braking applied (-8.0 m/s^2); PID states reset |

### Safety Features

1. **Time-to-Collision (TTC) monitoring**: TTC is computed each timestep as `distance / (ego_speed - lead_speed)` when closing. Emergency braking activates when TTC < 3.0s.

2. **Safe following distance**: Computed as `speed * time_headway + min_distance` (i.e., `v * 1.5 + 10.0`), ensuring both a speed-proportional gap and a minimum standstill distance.

3. **Acceleration limits**: All commands are clamped to [-8.0, 3.0] m/s^2, matching physical vehicle constraints.

4. **Anti-windup**: PID integral term is rolled back when output saturates, preventing integral buildup during sustained saturation (e.g., during max-acceleration cruise ramp-up).

5. **Non-negative speed constraint**: Vehicle speed is clamped to >= 0 m/s after each kinematic update.

## 2. PID Tuning Methodology

### Approach

Manual tuning following the Ziegler-Nichols-inspired methodology:

1. **Speed PID** — tuned first in isolation (cruise mode, t=0-30s):
   - Set Ki=Kd=0, increased Kp until the controller saturated at max_accel (3.0 m/s^2) for most of the ramp, achieving fast rise time.
   - Added Ki=0.3 to eliminate steady-state error.
   - Added Kd=0.1 for minor overshoot reduction.

2. **Distance PID** — tuned for follow mode (t=30-130s):
   - The distance PID is the primary controller in follow mode, with the speed PID acting only as an upper speed limiter.
   - Kp=0.8 provides responsive gap correction.
   - Ki=0.15 eliminates steady-state distance error.
   - Kd=0.4 damps oscillations from noisy lead vehicle speed.

### Final Gains

| Controller | Kp | Ki | Kd |
|------------|-----|------|------|
| Speed PID | 2.0 | 0.30 | 0.10 |
| Distance PID | 0.8 | 0.15 | 0.40 |

### Design Decisions

- **Follow mode blending**: The distance PID output is used directly in follow mode. The speed PID only intervenes when the ego vehicle is at or above the set speed (30 m/s), preventing the ego from exceeding the cruise target while allowing the distance controller to close gaps by accelerating.

- **Emergency mode resets**: Both PID controllers are reset upon entering emergency mode. This prevents stale integral terms from causing inappropriate commands when transitioning back to follow mode after an emergency braking event.

## 3. Simulation Results

### Scenario Timeline

| Phase | Time Range | Description |
|-------|-----------|-------------|
| Cruise ramp-up | 0.0 – 30.0s | Ego accelerates from 0 to 30 m/s, no lead vehicle |
| Follow entry | 30.0 – 35.0s | Lead vehicle appears at ~25 m/s, ego decelerates to match |
| Steady follow | 35.0 – 100.0s | Ego follows lead at ~25 m/s, maintaining safe distance (~47m) |
| Speed-up follow | 100.0 – 119.9s | Lead gradually increases speed; ego tracks |
| Emergency braking | 120.0 – 121.5s | Lead brakes hard; TTC drops below 3.0s; ego applies max deceleration |
| Recovery | 121.5 – 130.0s | Both vehicles accelerate; gap reopens |
| Cruise resume | 130.0 – 150.0s | Lead disappears; ego resumes cruise at 30 m/s |

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed rise time (to 90%) | < 10.0s | 9.0s | PASS |
| Speed overshoot | < 5.0% | 0.33% | PASS |
| Speed steady-state error | < 0.5 m/s | 0.010 m/s | PASS |
| Distance steady-state error | < 2.0m | 0.111m | PASS |
| Minimum distance | > 5.0m | 18.89m | PASS |
| Control duration | 150.0s | 150.0s | PASS |

### Key Observations

1. **Cruise control**: The ego vehicle reaches 27.0 m/s (90% of target) in 9.0s, constrained primarily by the max acceleration limit of 3.0 m/s^2. Overshoot is negligible at 0.33%. Steady-state error of 0.010 m/s is eliminated by the integral term.

2. **Following distance**: During steady-state follow (t=40-50s), the actual distance tracks the desired distance (ego_speed * 1.5 + 10.0) with an average error of only 0.111m, well below the 2.0m target.

3. **Emergency response**: At t=120.0s, the lead vehicle's speed drops sharply (from ~20 m/s to ~5 m/s), causing TTC to fall to 2.59s (below the 3.0s threshold). The ACC immediately applies maximum braking (-8.0 m/s^2). The minimum gap during the emergency is 18.89m, providing a substantial safety margin above the 5.0m floor.

4. **Cruise recovery**: After the lead vehicle disappears at t=130.0s, the ego vehicle smoothly accelerates back to 30.0 m/s within ~2 seconds and maintains that speed with minimal oscillation through the end of the simulation.
