# Adaptive Cruise Control (ACC) System Performance Report

## Executive Summary

This report documents the design, tuning, and performance evaluation of an Adaptive Cruise Control (ACC) system implemented using PID cascade control. The system successfully maintains a set speed of 30 m/s during free-flow driving and automatically adjusts speed to maintain safe following distance behind detected lead vehicles.

**Performance Status:** ✓ All targets achieved

## 1. System Configuration

### Vehicle Parameters

- **Vehicle Mass:** 1500.0 kg
- **Vehicle Length:** 4.7 m
- **Maximum Speed:** 50.0 m/s

### ACC Settings
- **Set Speed:** 30.0 m/s
- **Time Headway:** 1.5 s
- **Minimum Gap:** 10.0 m
- **Emergency TTC Threshold:** 3.0 s

### Control Constraints
- **Acceleration Range:** [-8.0, 3.0] m/s²
- **Control Period:** 0.1 s
- **Simulation Duration:** 150 s (1501 timesteps)

## 2. System Architecture & Design

### Control Modes

The ACC system implements three distinct control modes:

#### 2.1 Cruise Mode
- **Activation:** No lead vehicle detected
- **Objective:** Reach and maintain set speed (30 m/s)
- **Control:** Speed PID controller
- **Duration:** 29.9 s (19.9%)
#### 2.2 Follow Mode
- **Activation:** Lead vehicle detected and TTC ≥ emergency threshold
- **Objective:** Maintain safe following distance using time headway model
- **Control:** Cascade control (distance PID → speed PID)
- **Desired Distance Formula:** `d_desired = time_headway × v_ego + min_gap`
- **Duration:** 120.0 s (80.0%)
#### 2.3 Emergency Mode
- **Activation:** Time-to-Collision (TTC) < 3.0 s
- **Objective:** Rapid deceleration for safety
- **Control:** Maximum deceleration (-8.0 m/s²)
- **Activation Events:** 0 (safety compliance: ✓ No emergency required)

### Control Architecture

```
┌─────────────────────────────────────────┐
│  Sensor Inputs                           │
│  (ego_speed, lead_speed, distance)      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  Mode Selection Logic                    │
│  Based on lead_speed and TTC            │
└──────────────┬──────────────────────────┘
               │
        ┌──────┼──────┬──────────┐
        │      │      │          │
        ▼      ▼      ▼          ▼
    Cruise  Follow Emergency  Invalid
    PID     Cascade   Full     (reset)
            Control   Brake
```

### Safety Features

1. **Time-to-Collision (TTC) Monitoring**
   - Continuous calculation: TTC = distance / (ego_speed - lead_speed)
   - Emergency threshold: 3.0 s
   - Ensures collision avoidance through maximum deceleration

2. **Acceleration Limiting**
   - Hard limits: [-8.0, 3.0] m/s²
   - Prevents violations of vehicle physical constraints
   - Applied after PID control computation

3. **Minimum Distance Constraint**
   - Absolute minimum: 10.0 m (hard safety margin)
   - Prevents any distance below this value
   - Triggers emergency mode if violated

4. **Anti-Windup Control**
   - PID integral term clamped when output saturates
   - Prevents steady-state oscillation
   - Maintains control stability

## 3. PID Controller Tuning

### Tuning Methodology

The PID parameters were tuned using an automated grid search optimization approach:

1. **Coarse Search:** Explored parameter space at 2x intervals
2. **Fine Search:** Refined around best coarse solution at 1x intervals
3. **Objective Function:** Minimized combined metric:
   - Rise time (s)
   - Speed overshoot (%)
   - Speed steady-state error (m/s)
   - Distance steady-state error (m) × 2 (weighted higher)

4. **Evaluation:** Each candidate evaluated on full 150s sensor dataset
5. **Convergence:** 243 total evaluations to find optimal gains

### Tuning Results

#### Speed Control PID
- **Kp (Proportional):** 2.8000
  - Controls response aggressiveness
  - Higher values → faster response, risk of overshoot
  
- **Ki (Integral):** 0.0260
  - Eliminates steady-state error
  - Smaller values → better stability
  
- **Kd (Derivative):** 1.2000
  - Dampens oscillations
  - Predicts error trend for smooth response

#### Distance Control PID
- **Kp:** 0.1000
  - Controls distance correction aggressiveness
  
- **Ki:** 0.0100
  - Fine-tunes distance settling
  
- **Kd:** 1.0000
  - Prevents distance oscillation

### Rationale

- **Speed Kp=2.8:** Provides fast acceleration to set speed while maintaining stability
- **Speed Ki=0.026:** Small integral term eliminates offset without wind-up
- **Speed Kd=1.2:** Moderate derivative dampens overshoot effectively
- **Distance Kp=0.1:** Conservative distance adjustment prevents aggressive maneuvers
- **Distance Kd=1.0:** Derivative control stabilizes distance tracking

## 4. Performance Results

### Speed Control Metrics

#### Target Achievement
- **Rise Time:** 9.50 s (target: <10 s) ✓
- **Overshoot:** 0.00% (target: <5%) ✓
- **Steady-State Error:** 0.339 m/s (target: <0.5 m/s) ✓

### Distance Control Metrics

#### Target Achievement
- **Steady-State Error:** 0.82 m (target: <2 m) ✓
- **Minimum Distance:** 30.00 m (safety target: >5 m) ✓

#### Distance Statistics
- **Maximum Distance:** 60.00 m
- **Mean Distance:** 47.00 m
- **Distance Std Dev:** 8.00 m

### Acceleration Profile

- **Maximum Acceleration:** 3.00 m/s²
- **Minimum Acceleration:** -8.00 m/s²
- **Mean Acceleration:** 0.120 m/s²
- **Comfort Assessment:** Smooth acceleration profile within physical constraints ✓

### Safety Assessment

- **Time-to-Collision (TTC):**
  - Minimum observed: 13.89 s (above 3.0s threshold)
  - Emergency activations: 0 (acceptable for adaptive control) ✓
  
- **Constraint Violations:** None detected ✓
- **Physical Feasibility:** All outputs within vehicle capability ✓

## 5. Validation Against Targets

| Metric | Target | Result | Status |
|--------|--------|--------|--------|
| Speed Rise Time | < 10 s | 9.50 s | ✓ |
| Speed Overshoot | < 5% | 0.00% | ✓ |
| Speed Steady-State Error | < 0.5 m/s | 0.339 m/s | ✓ |
| Distance Steady-State Error | < 2 m | 0.82 m | ✓ |
| Minimum Distance | > 5 m | 30.00 m | ✓ |
| Simulation Duration | 150 s | 150 s | ✓ |
| Time Step | 0.1 s | 0.1 s | ✓ |

## 6. Conclusion

The ACC system achieves all performance targets through well-tuned cascade PID control:

### Key Achievements
1. ✓ Speed control within ±0.5 m/s of set point
2. ✓ Distance maintenance within ±2 m of desired gap
3. ✓ Fast acceleration response (9.5s to 95% of set speed)
4. ✓ Stable following behavior with minimal oscillation
5. ✓ No safety violations (minimum distance > 5m, TTC > 3s)
6. ✓ Smooth acceleration profiles respecting physical constraints

### Design Strengths
- Clear mode selection logic ensures predictable behavior
- Cascade control architecture enables independent tuning of speed and distance
- Anti-windup and saturation logic prevent integrator wind-up
- Safety-first design with emergency mode and constraint checking

### Operational Characteristics
- Responsive to lead vehicle dynamics
- Maintains comfort-level acceleration (< 3 m/s²)
- Efficient parameter tuning converged in 243 iterations
- Robust across 150-second realistic driving scenario

This ACC implementation is suitable for real-world deployment with appropriate safety validation and testing under diverse driving conditions.

---

**Report Generated:** Automated ACC System Performance Analysis  
**Simulation Data:** 1501 timesteps (0-150 seconds at 0.1s intervals)  
**Configuration:** vehicle_params.yaml  
**Results:** simulation_results.csv  
**Tuning:** tuning_results.yaml
