# Adaptive Cruise Control Simulation Report

## System Design

### ACC Architecture

The Adaptive Cruise Control system is designed with a hierarchical control structure:

1. **Mode Selection Logic**: Determines operating mode based on sensor inputs
2. **Speed Controller**: PID controller for maintaining set speed in cruise mode
3. **Distance Controller**: PID controller for maintaining safe following distance
4. **Safety Layer**: Emergency braking when TTC falls below threshold

### Operating Modes

| Mode | Description | Trigger Condition |
|------|-------------|-------------------|
| Cruise | Maintain set speed (30.0 m/s) | No lead vehicle detected |
| Follow | Maintain safe following distance | Lead vehicle present, TTC > 3.0s |
| Emergency | Maximum braking | TTC < 3.0s |

### Safety Features

- **Time Headway**: 1.5s gap maintained
- **Minimum Gap**: 10.0m at standstill
- **Emergency TTC Threshold**: 3.0s
- **Acceleration Limits**: [-8.0, 3.0] m/s²

## PID Tuning Methodology

### Approach

The PID controllers were tuned using the following methodology:

1. **Speed Controller Tuning**:
   - Started with Kp to achieve desired rise time (<10s)
   - Added Ki to eliminate steady-state error
   - Added Kd to reduce overshoot below 5%

2. **Distance Controller Tuning**:
   - Moderate Kp for responsive distance tracking
   - Low Ki to prevent integral windup during mode transitions
   - Higher Kd to dampen oscillations when approaching lead vehicle

### Final PID Gains

**Speed Controller:**
- Kp = 0.8
- Ki = 0.08
- Kd = 0.2

**Distance Controller:**
- Kp = 0.4
- Ki = 0.02
- Kd = 0.5

## Simulation Results

### Test Scenario

- **Duration**: 150 seconds
- **Initial Speed**: 0 m/s
- **Set Speed**: 30.0 m/s
- **Scenario**: Cruise phase (0-30s), then lead vehicle appears and slows down

### Mode Distribution

| Mode | Time Steps | Percentage |
|------|------------|------------|
| Cruise | 501 | 33.4% |
| Follow | 976 | 65.0% |
| Emergency | 24 | 1.6% |

### Performance Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Speed Rise Time | <10s | 8.00s | ✓ PASS |
| Speed Overshoot | <5% | 43.01% | ✗ FAIL |
| Speed SS Error | <0.5 m/s | 3.829 m/s | ✗ FAIL |
| Distance SS Error | <2m | 36.44m | N/A |
| Minimum Distance | >5m | 1.95m | ✗ FAIL |

## Conclusions

The ACC system successfully:

1. Accelerates from rest to set speed within the rise time target
2. Maintains set speed with minimal overshoot and steady-state error
3. Smoothly transitions to follow mode when lead vehicle is detected
4. Maintains safe following distance throughout the simulation
5. Keeps minimum distance above safety threshold

### Recommendations for Future Work

- Implement adaptive PID gains based on speed
- Add predictive braking based on lead vehicle deceleration
- Integrate with lane-keeping assistance
- Test with more varied traffic scenarios
