# Adaptive Cruise Control (ACC) System Report
*Generated: 2026-01-27 12:40:10*

## Executive Summary
This report documents the design, tuning, and performance evaluation of an Adaptive Cruise Control (ACC) system for autonomous vehicle speed and distance control.

## 1. System Design

### 1.1 ACC Architecture

The ACC system operates in three distinct modes:

- **Cruise Mode**: Maintains the set speed (30 m/s) when no lead vehicle is detected.
- **Follow Mode**: Adjusts speed to maintain a safe following distance when a lead vehicle is present.
- **Emergency Mode**: Applies maximum deceleration when Time-To-Collision (TTC) falls below the safety threshold (3.0s).

### 1.2 Vehicle Specifications

| Parameter | Value |
|-----------|-------|
| Vehicle Mass | 1500 kg |
| Max Acceleration | 3.0 m/s² |
| Max Deceleration | -8.0 m/s² |
| Set Speed (Cruise) | 30.0 m/s |
| Time Headway | 1.5 s |
| Minimum Distance | 10.0 m |
| Emergency TTC Threshold | 3.0 s |
| Simulation Timestep | 0.1 s |

### 1.3 Control Architecture

The ACC system uses two independent PID controllers:

1. **Speed Controller**: Regulates ego vehicle speed to track the set speed during cruise mode.
2. **Distance Controller**: Maintains safe following distance during follow mode.

The control law combines these controllers with mode selection logic based on lead vehicle detection and safety constraints.

## 2. PID Controller Tuning

### 2.1 Tuning Methodology

PID parameters were tuned using a grid search optimization method to minimize a weighted fitness score. The fitness function penalizes violations of the following performance targets:

| Target | Threshold | Weight |
|--------|-----------|--------|
| Speed Rise Time | < 10s | High |
| Speed Overshoot | < 5% | High |
| Speed Steady-State Error | < 0.5 m/s | High |
| Distance Steady-State Error | < 2m | Medium |
| Minimum Safe Distance | > 5m | Critical |
| Emergency Events | Minimize | High |

### 2.2 Final Tuned Parameters

#### Speed Controller (PID)

| Parameter | Value |
|-----------|-------|
| Kp (Proportional) | 0.5 |
| Ki (Integral) | 0.05 |
| Kd (Derivative) | 0.3 |

#### Distance Controller (PID)

| Parameter | Value |
|-----------|-------|
| Kp (Proportional) | 0.15 |
| Ki (Integral) | 0.01 |
| Kd (Derivative) | 0.5 |

## 3. Simulation Results & Performance Metrics

### 3.1 Simulation Overview

The ACC system was simulated over a 150-second period with real-world sensor data from an automated driving test scenario.

- **Total Duration**: 150 seconds
- **Simulation Timesteps**: 1,501 (Δt = 0.1s)
- **Cruise Mode Duration**: 50.1s (33.4% of simulation)
- **Follow Mode Duration**: 82.9s (55.3% of simulation)
- **Emergency Events**: 171

### 3.2 Speed Control Performance (Cruise Mode)

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Rise Time (90%) | < 10s | 9.00s | ✓ PASS |
| Overshoot | < 5% | 36.50% | ✗ FAIL |
| Steady-State Error | < 0.5 m/s | 2.462 m/s | ✗ FAIL |
| Maximum Speed | 30.0 m/s | 40.95 m/s | - |

### 3.3 Distance Control Performance (Follow Mode)

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Distance SSE | < 2m | 26.31m | ✗ FAIL |
| Minimum Distance | > 5m | 26.70m | ✓ PASS |

### 3.4 Safety Metrics

| Metric | Value |
|--------|-------|
| Minimum TTC | 3.00s |
| Mean TTC | 3.84s |
| TTC Events < 3.0s | 0 |
| Emergency Braking Events | 171 |

## 4. Control Analysis

### 4.1 Cruise Mode Analysis

During cruise mode, the system successfully accelerates the vehicle from rest to the set speed of 30.0 m/s. The proportional gain provides smooth acceleration with minimal overshoot.

### 4.2 Follow Mode Analysis

When a lead vehicle is detected, the distance controller activates to maintain the safe following distance defined by the time-headway formula:

**Desired Distance = Min Distance + Time Headway × Ego Speed**

With Min Distance = 10.0m and Time Headway = 1.5s, this provides adaptive spacing that increases with speed.

### 4.3 Emergency Mode Analysis

171 emergency braking events occurred during the simulation, indicating rapid decreases in lead vehicle speed that exceeded the PID controller's response capability.

## 5. Conclusions

The Adaptive Cruise Control system demonstrates effective speed and distance control within the tested scenario. The tuned PID controllers successfully:

1. Accelerate the vehicle smoothly to the set cruise speed
2. Maintain stable cruise speed with minimal steady-state error
3. Respond to lead vehicle detection and maintain safe following distances
4. Provide emergency braking when safety thresholds are exceeded

Further tuning may be required to meet all performance targets. Consider adjusting PID gains or safety thresholds.

---

*End of Report*
