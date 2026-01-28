# ACC Report

## System design
- Modes: cruise (no lead), follow (lead present), emergency (TTC below threshold).
- Safety: time-headway-based desired gap, minimum gap enforcement, emergency braking on TTC.
- Control: PID for speed control and PID for distance control, conservative accel blending in follow.

## PID tuning methodology and final gains
- Approach: manual tuning to reach max accel early for rise time, then reduce overshoot and steady-state error.
- Speed PID: kp=0.4, ki=0.0, kd=0.0.
- Distance PID: kp=0.5, ki=0.0, kd=0.1.

## Simulation results and performance metrics
- Speed rise time (10–90%): 8.80s.
- Speed overshoot: 0.00%
- Speed steady-state error (last 5s pre-lead): 0.003 m/s.
- Distance steady-state error (steady follow window): 0.463 m.
- Minimum following distance: 7.670 m.
