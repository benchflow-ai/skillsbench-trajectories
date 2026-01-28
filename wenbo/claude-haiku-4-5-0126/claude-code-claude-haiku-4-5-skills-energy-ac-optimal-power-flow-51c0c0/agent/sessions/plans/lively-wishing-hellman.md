# AC OPF Implementation Plan

## Objective
Create an AC Optimal Power Flow (OPF) solver for a 300-bus, 69-generator, 411-branch power system network to find a least-cost operating point and generate a feasibility report.

## Key Requirements
1. Solve the AC OPF problem described in math-model.md using the network data from network.json
2. Minimize total generation cost (quadratic functions)
3. Enforce all AC power flow equations (complex nodal balance equations)
4. Respect generator power bounds, reactive power bounds, and costs
5. Enforce voltage magnitude constraints and angle difference limits
6. Check branch MVA/current thermal limits
7. Produce a detailed report in report.json with summary, generator states, bus states, branch loading, and feasibility verification

## Problem Formulation (from math-model.md)
- **Decision Variables**: Generator complex power (Sg_k), bus voltages (V_i), branch flows (S_ij)
- **Objective**: Minimize sum of c2*P^2 + c1*P + c0 for all generators
- **Constraints**:
  - Slack bus angle = 0
  - Generator bounds: Sg_k_min <= Sg_k <= Sg_k_max
  - Voltage bounds: V_min <= |V_i| <= V_max
  - AC nodal balance: sum of generation - load - shunt = sum of branch flows (complex equation)
  - AC branch power flow equations with transformer ratios
  - Branch thermal limits: |S_ij| <= S_ij_max and |S_ij| <= |V_i| * I_ij_max
  - Angle difference limits: Θ_diff_min <= angle(V_i*V_j*) <= Θ_diff_max

## Network Data Structure (from /root/network.json)
- 300 buses: 231 load buses (PQ), 68 generator buses (PV), 1 slack bus (V_angle=0)
- 69 generators: All in-service, quadratic cost functions
- 411 transmission lines: All in-service, 345 with transformer parameters
- 29 shunt devices for reactive power support
- Base MVA: 100

## Implementation Approach

### 1. **Technology Choice: CasADi + IPOPT**
- **Language**: Python 3
- **Solver Library**: CasADi for nonlinear optimization with IPOPT as backend solver
- **Rationale**:
  - CasADi is specialized for power systems optimization
  - Automatic differentiation for accurate gradients
  - IPOPT is robust NLP solver for AC OPF problems
  - No existing solver dependency issues

### 2. **Solution Architecture**

**Step A: Data Loading & Preprocessing** (parse_network_data function)
- Load network.json
- Extract bus, generator, branch, generator cost, and reserve data
- Build reverse maps: bus_index -> bus_number, gen_index -> gen_bus
- Identify slack bus (bus_type == 3)
- Convert all impedances/admittances to per-unit if needed
- Build branch information arrays

**Step B: Problem Setup** (build_opf_model function)
- Create CasADi symbolic variables:
  - Pg[i]: real power output for generator i (scalar)
  - Qg[i]: reactive power output for generator i (scalar)
  - Vm[i]: voltage magnitude at bus i (scalar, pu)
  - Va[i]: voltage angle at bus i (scalar, radians)
- Create complex voltage variables: V[i] = Vm[i] * exp(j*Va[i])
- Build complex branch power flow equations using π-model with transformer parameters

**Step C: Objective Function**
- Sum of generator cost functions: Σ(c2_k * Pg_k^2 + c1_k * Pg_k + c0_k)

**Step D: Constraints**
- Slack bus constraint: Va[slack] = 0
- Generator bounds:
  - Pg_min[i] <= Pg[i] <= Pg_max[i]
  - Qg_min[i] <= Qg[i] <= Qg_max[i]
- Voltage bounds:
  - V_min[i] <= Vm[i] <= V_max[i]
- AC Power Balance Equations (for each bus):
  - Real: Σ(Pg[i]) - Σ(Pd[i]) - Σ(Gs[i]*Vm[i]^2) = Σ(P_from_branches[i]) + Σ(P_to_branches[i])
  - Reactive: Σ(Qg[i]) - Σ(Qd[i]) + Σ(Bs[i]*Vm[i]^2) = Σ(Q_from_branches[i]) + Σ(Q_to_branches[i])
- Branch power flow (using complex equations from math-model.md):
  - P_from_ij = Re[(Y_series + Y_c_from)* * |V_i|^2 / |T_ij|^2 - Y_series* * V_i * V_j* / T_ij]
  - Q_from_ij = Im[(Y_series + Y_c_from)* * |V_i|^2 / |T_ij|^2 - Y_series* * V_i * V_j* / T_ij]
  - Similar for P_to_ij, Q_to_ij at the "to" bus
- Branch thermal limits (apparent power):
  - |S_ij| <= RATE_A for each branch
- Angle difference limits:
  - ANGMIN <= angle(V_i * conj(V_j)) <= ANGMAX

**Step E: Solver Configuration**
- Initialize with flat start (Vm=1.0 pu, Va=0 for all buses)
- Use IPOPT with appropriate tolerances
- Enable warm start from previous solutions if available
- Set solver options:
  - tol: 1e-6 (constraint feasibility)
  - acceptable_tol: 1e-4
  - max_iter: 200

**Step F: Post-Processing & Report Generation**
- Extract solution:
  - Generator outputs (Pg, Qg)
  - Bus voltages (Vm, Va)
  - Branch flows (from and to)
- Calculate totals and losses:
  - Total generation MW/MVAr
  - Total load MW/MVAr
  - Total losses = generation - load (by power balance)
  - Solver status
- Identify branch loading percentages (flow / rating)
- Sort and select most-loaded branches (top 20)
- Verify feasibility:
  - Check power balance at each bus
  - Check voltage violations
  - Check branch overloads

### 3. **Key Implementation Details**

**Complex Number Handling in CasADi:**
- Represent complex voltage V_i as pair (V_real, V_imag) or use magnitude/angle representation
- Use vectorized operations where possible
- For branch flows, explicitly compute real and imaginary parts

**Branch π-Model with Transformers:**
- For branch i-j with transformer ratio T_ij and phase shift θ_ij:
  - Series admittance Y_series = 1/(R + jX) (per-unit impedance inverse)
  - Shunt admittances Y_c_from (from side), Y_c_to (to side)
  - Accounting for tap ratio and phase shift in flow equations

**Numerical Stability:**
- Use per-unit system consistently
- Scale variables appropriately
- Handle tap ratios = 0 by treating as unit transformer
- Set realistic variable bounds to guide solver

**Warm Starting:**
- If previous solution exists, use it as initial point
- This speeds convergence for repeated solves

### 4. **Report Structure** (output as report.json)
```json
{
  "summary": {
    "total_cost_per_hour": <float>,
    "total_load_MW": <float>,
    "total_load_MVAr": <float>,
    "total_generation_MW": <float>,
    "total_generation_MVAr": <float>,
    "total_losses_MW": <float>,
    "solver_status": "optimal" | "suboptimal" | "infeasible" | "unbounded"
  },
  "generators": [
    {
      "id": <gen_id>,
      "bus": <bus_number>,
      "pg_MW": <float>,
      "qg_MVAr": <float>,
      "pmin_MW": <float>,
      "pmax_MW": <float>,
      "qmin_MVAr": <float>,
      "qmax_MVAr": <float>
    }
  ],
  "buses": [
    {
      "id": <bus_id>,
      "vm_pu": <float>,
      "va_deg": <float>,
      "vmin_pu": <float>,
      "vmax_pu": <float>
    }
  ],
  "most_loaded_branches": [
    {
      "from_bus": <int>,
      "to_bus": <int>,
      "loading_pct": <float>,
      "flow_from_MVA": <float>,
      "flow_to_MVA": <float>,
      "limit_MVA": <float>
    }
  ],
  "feasibility_check": {
    "max_p_mismatch_MW": <float>,
    "max_q_mismatch_MVAr": <float>,
    "max_voltage_violation_pu": <float>,
    "max_branch_overload_MVA": <float>
  }
}
```

## Critical Files to Create/Modify
- **Create**: `/root/acopf_solver.py` - Main AC OPF solver script
- **Create**: `/root/report.json` - Output report (generated by solver)

## Verification Strategy
1. **Run AC OPF Solver**: Execute `python3 /root/acopf_solver.py`
2. **Verify Output**:
   - report.json exists and contains valid JSON
   - Summary statistics are reasonable:
     - Generation ≈ Load + Losses (power balance)
     - All generator outputs within bounds
     - All voltages within limits
     - Branch flows below ratings
   - Feasibility check shows near-zero mismatches
   - Solver status is "optimal"
3. **Manual Checks**:
   - Total load matches network.json (23,525.85 MW + 7,787.97 MVAr)
   - Cost function is positive
   - Most-loaded branches have reasonable loading percentages

## Dependencies
- Python 3.8+
- json (built-in)
- numpy (for numerical operations)
- casadi (for optimization - will need to install)
- ipopt (solver backend - will be installed with casadi)

## Implementation Notes
- Use skill system for casadi-ipopt-nlp to handle NLP construction and solving
- Build the Jacobian and Hessian using CasADi's automatic differentiation
- Error handling for infeasible problems and solver failures
- Detailed logging for debugging convergence issues
