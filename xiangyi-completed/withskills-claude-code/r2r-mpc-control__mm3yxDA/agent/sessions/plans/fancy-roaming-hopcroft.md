# MPC Controller Implementation Plan for Roll-to-Roll Web Handling

## Task Overview
Implement a Model Predictive Control (MPC) controller for a 6-section Roll-to-Roll (R2R) web handling system that must stabilize tensions during a step change in section 3 from 20N to 44N at t=0.5s. The controller must run successfully for at least 5 seconds and generate required output files.

## System Dynamics Summary
- **State (12D):** `x = [T1, T2, T3, T4, T5, T6, v1, v2, v3, v4, v5, v6]`
- **Control (6D):** `u = [u1, u2, u3, u4, u5, u6]` (motor torques)
- **Key Parameters:** EA=2400, J=0.95, R=0.04, fb=10.0, L=1.0, v0=0.01 (inlet velocity)
- **Reference Change:** T_ref_initial=[28,36,20,40,24,32] → T_ref_final=[28,36,44,40,24,32] at t=0.5s

## Implementation Plan

### Phase 1: Linearization of Dynamics at Initial Operating Point (CRITICAL)

**Objective:** Derive a linear state-space model around the initial steady-state operating point

**Approach:**
1. Extract initial reference state from simulator:
   - T_ref_0 = [28, 36, 20, 40, 24, 32]
   - Compute v_ref_0 using the simulator's `_compute_velocities()` function
   - x_ref_0 = [T_ref_0, v_ref_0]

2. Compute Jacobian matrices (A, B) at this operating point:
   - **A matrix (12×12):** Partial derivatives of dynamics w.r.t. state
   - **B matrix (12×6):** Partial derivatives of dynamics w.r.t. control inputs
   - Use the dynamics equations from r2r_simulator.py (lines 125-134)

3. Linearized state-space model:
   ```
   dx/dt = A*x + B*u
   x_discrete(k+1) = A_d*x_discrete(k) + B_d*u_discrete(k)
   ```
   where A_d, B_d are obtained via Euler discretization with dt=0.01

**Critical Details:**
- Linearize around x_ref_0 (steady-state before t=0.5s)
- The inlet velocity v0 is a boundary condition (included in tension dynamics)
- The outlet tension is zero (boundary condition in velocity dynamics)
- Carefully implement partial derivatives for coupling terms in dynamics

**Output from Phase 1:**
- A_matrix (12×12): Linearized continuous-time state transition
- B_matrix (12×6): Linearized continuous-time input matrix
- Discretized versions for MPC

---

### Phase 2: MPC Controller Design

**Objective:** Design a finite-horizon LQR-based MPC controller

**Approach:**

#### 2.1 Cost Function Definition
```
J = sum_{k=0}^{N-1} [ (x_k - x_ref)^T Q (x_k - x_ref) + u_k^T R u_k ] + (x_N - x_ref)^T Q_f (x_N - x_ref)
```

**Cost Matrix Design:**
- **Q (12×12):** State cost - diagonal matrix
  - Tension components (Q[0:6,0:6]): Set relatively high (e.g., 100) to penalize tension deviations
  - Velocity components (Q[6:12,6:12]): Set lower (e.g., 0.1) to allow velocity transients
  - Example: `Q_diag = [100, 100, 100, 100, 100, 100, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]`

- **R (6×6):** Control cost - diagonal matrix
  - Penalize large motor torques to ensure smooth control
  - Example: `R_diag = [0.033, 0.033, 0.033, 0.033, 0.033, 0.033]`
  - These values prevent aggressive control inputs while allowing effective tension tracking

- **Q_f:** Terminal cost = Q (standard approach for stability)

#### 2.2 Prediction Horizon
- **N (prediction horizon):** Set to 9 steps (90 ms ahead)
  - Balances computational efficiency with forward-looking control
  - Constraint: 3 ≤ N ≤ 30 per requirements

#### 2.3 LQR Gain Computation
- Compute infinite-horizon LQR gain K (6×12 matrix) using the discretized A_d, B_d
- K will be used as a stabilizing feedback gain: u = -K(x - x_ref) + u_ref
- Use scipy.linalg.solve_discrete_are() or similar to solve the algebraic Riccati equation

#### 2.4 MPC Implementation Strategy
- **Approach:** Time-varying reference tracking with finite-horizon optimization
- At each timestep k:
  1. Get current measurement x(k) from simulator (with measurement noise)
  2. Get reference trajectory (x_ref, u_ref) for the current time from simulator
  3. Compute optimal control using:
     - Option A: Full finite-horizon MPC (if time allows)
     - Option B: LQR gain with time-varying reference (faster, simpler)
     - Recommend Option B for simplicity and speed
  4. Apply control u(k) to simulator
  5. Log state, reference, and control for analysis

---

### Phase 3: Controller Implementation in Python

**File to Create:** `mpc_controller.py`

**Core Components:**

```python
class MPCController:
    def __init__(self, sim_config, horizon_N=9, Q_diag=None, R_diag=None):
        # Load system parameters from config
        # Compute A, B matrices (linearized dynamics)
        # Compute LQR feedback gain K
        # Store cost matrices

    def linearize_dynamics(self, x_ref, u_ref):
        # Compute Jacobian matrices at operating point
        # Return A, B matrices

    def compute_lqr_gain(self, A_d, B_d):
        # Solve discrete-time algebraic Riccati equation
        # Return K (6×12)

    def step(self, x_measurement, x_ref, u_ref):
        # x_measurement: current state (12D, with noise)
        # x_ref: reference state (12D)
        # u_ref: reference control (6D)
        # Return u: optimal control input (6D)

        # Simple implementation: u = u_ref - K(x - x_ref)
```

**Integration Points:**
- Must accept measurements with noise
- Must track time-varying references from simulator
- Must respect control bounds if needed (optional for first version)
- Output control must work directly with simulator.step(u)

---

### Phase 4: Simulation Loop and Logging

**File to Create:** `run_mpc.py`

**Simulation Parameters:**
- Duration: At least 5 seconds (500 timesteps at dt=0.01)
- Timestep: dt=0.01s (from system_config.json)
- Initial state: T_ref_initial, computed v_ref_initial

**Logging Structure:**
- Create a log entry at each timestep with:
  - `time`: Current simulation time (s)
  - `tensions`: [T1, T2, T3, T4, T5, T6] (N)
  - `velocities`: [v1, v2, v3, v4, v5, v6] (m/s)
  - `control_inputs`: [u1, u2, u3, u4, u5, u6] (N·m)
  - `references`: [T1_ref, T2_ref, T3_ref, T4_ref, T5_ref, T6_ref, v1_ref, v2_ref, v3_ref, v4_ref, v5_ref, v6_ref]

**Key Events to Capture:**
- t ∈ [0, 0.5s]: System with initial reference
- t ∈ [0.5s, 5.0s]: System responding to step change in section 3 reference (20N → 44N)

---

### Phase 5: Performance Metrics Computation

**File to Create:** `compute_metrics.py`

**Metrics to Compute:**

1. **Steady-State Error (SSE):**
   - Compute mean absolute error for each tension during [4.0s, 5.0s] window (steady-state phase)
   - Compare against final reference tensions
   - Report: Overall mean SSE (target: < 2.0N)
   - Report: Per-section SSE to identify problematic sections

2. **Settling Time:**
   - For section 3 (where step change occurs):
     - Define settled when deviation from final reference stays within ±5% for 0.5s continuously
     - Target: < 4.0s
   - Compute settling time as first time this condition is met

3. **Tension Bounds:**
   - `max_tension`: Maximum tension across all timesteps and sections
   - `min_tension`: Minimum tension across all timesteps and sections
   - Target: 5.0N ≤ tensions ≤ 50.0N (avoid safety violations)
   - Flag if constraints are violated

4. **Transient Overshoot (additional metric):**
   - For section 3: Maximum overshoot above final reference during transient
   - For section 3: Any undershoot below final reference
   - Useful for tuning Q and R matrices

---

### Phase 6: Output File Generation

**Required Files:**

#### 1. `controller_params.json`
- Stores all controller design parameters and matrices
- Includes: horizon_N, Q_diag, R_diag, K_lqr (feedback gain), A_matrix, B_matrix
- Format: JSON with float arrays for matrices

#### 2. `control_log.json`
- Stores simulation trajectory data
- Format: `{ "phase": "control", "data": [...] }`
- Each entry includes: time, tensions, velocities, control_inputs, references
- Must span at least 5 seconds

#### 3. `metrics.json`
- Stores computed performance metrics
- Includes: steady_state_error, settling_time, max_tension, min_tension

---

## Implementation Sequence

1. **Create mpc_controller.py**
   - Implement system parameter loading
   - Implement linearization (compute Jacobians analytically or numerically)
   - Implement LQR gain computation
   - Test with simple control law

2. **Create run_mpc.py**
   - Initialize simulator
   - Initialize controller
   - Run 500 timesteps (5 seconds)
   - Log all data at each step
   - Save control_log.json

3. **Create compute_metrics.py**
   - Load control_log.json
   - Compute all metrics
   - Save metrics.json

4. **Verify outputs**
   - Check controller_params.json exists and is valid
   - Check control_log.json has 500+ entries
   - Check metrics.json meets performance targets
   - Validate against system_config.json constraints

---

## Critical Implementation Notes

1. **Linearization:**
   - Must compute at initial operating point (T_ref_initial)
   - Use finite differences if analytical derivatives are complex
   - Validate against nonlinear simulator for small perturbations

2. **LQR Gain:**
   - Use scipy's `solve_discrete_are()` for accuracy
   - Ensure closed-loop eigenvalues are stable (|λ| < 1 for discrete system)
   - K matrix should be 6×12

3. **Reference Tracking:**
   - Simulator provides x_ref and u_ref at each timestep via `get_reference()`
   - Controller should blend reference control with feedback correction:
     - `u = u_ref - K(x - x_ref)`

4. **Measurement Noise:**
   - Simulator adds Gaussian noise (σ=0.01) to all 12 states
   - Controller should still work despite noise
   - No need for observer/filter initially

5. **Stability:**
   - MPC with LQR gain should be guaranteed stable if Q, R chosen appropriately
   - Q and R provided in template should work; may need tuning
   - Test for divergence and adjust Q/R if needed

6. **Simulation Accuracy:**
   - Euler integration is simple but adequate for dt=0.01
   - No need to modify simulator; just use it as-is
   - Ensure controller runs faster than simulator timesteps

---

## Success Criteria

- ✅ controller_params.json generated with valid matrices
- ✅ control_log.json contains 500+ timesteps (5+ seconds)
- ✅ No errors during 5-second simulation run
- ✅ Tensions remain within safe bounds [5.0N, 50.0N]
- ✅ Settling time < 4.0s for section 3 step change
- ✅ Steady-state error (section 3) < 2.0N after settling
- ✅ metrics.json reports all metrics correctly

---

## Dependencies & Tools
- NumPy (matrix operations)
- SciPy (solve_discrete_are for LQR)
- JSON (I/O)
- Python 3.6+

