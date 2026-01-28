# AC-OPF Base Case Solver Implementation Plan

## Objective
Solve an AC-feasible optimal power flow problem for a 300-bus, 69-generator power system and generate a structured JSON report with solution results.

## Input Data
- **Network file**: `/root/network.json` (MATPOWER format)
  - 300 buses with voltage bounds (0.94-1.06 pu)
  - 69 generators with quadratic cost functions
  - 411 transmission branches with MVA limits
  - baseMVA = 100.0
- **Math model**: `/root/math-model.md` (complex-number AC-OPF formulation)
- **Branch flows utility**: `/root/.claude/skills/ac-branch-pi-model/scripts/branch_flows.py`

## Available Tools
- **Python 3.12** installed, but NO optimization libraries yet
- **Branch power flow calculator** already developed and available
- **Math model** fully documented in markdown

## Implementation Strategy

### Phase 1: Install Dependencies
Install required packages:
- **CasADi** (nonlinear optimization modeling)
- **IPOPT** (interior-point solver)
- **NumPy** (numerical computations)
- **SciPy** (utilities)
- **Pandas** (data handling)

### Phase 2: Build AC-OPF Solver
Create `/root/acopf_solver.py` with:

1. **Data Parsing**
   - Load network.json and parse bus, gen, branch, gencost data
   - Map MATPOWER format → math model variables
   - Extract generator cost coefficients (quadratic: c2, c1, c0)

2. **CasADi Model Construction**
   - Decision variables:
     - Generator complex power: `S_g[k]` = P_g + jQ_g for each generator
     - Bus complex voltages: `V[i]` = |V_i| e^(j*θ_i) for each bus
     - Branch power flows (computed deterministically from voltages)

   - Objective function:
     - Cost: Σ(c2*P_g² + c1*P_g + c0) for all generators

   - Constraints:
     - Slack bus angle: θ = 0 at reference bus
     - Generator bounds: S_g_min ≤ S_g ≤ S_g_max
     - Voltage bounds: v_min ≤ |V| ≤ v_max
     - Power flow equations (nodal balance):
       - Use branch_flows.py to compute P_ij, Q_ij for each branch
       - Bus injection balance: ΣS_g - ΣS_d - S_shunt = ΣS_branch
     - Branch MVA limits: |S_ij|, |S_ji| ≤ RATE_A
     - Branch current limits: |S_ij| ≤ |V_i| * I_max
     - Angle difference bounds: θ_min ≤ θ_i - θ_j ≤ θ_max

3. **Solver Configuration**
   - Use IPOPT with tight tolerances (1e-6 for feasibility)
   - Set reasonable iteration limits
   - Configure output verbosity

### Phase 3: Solution Post-Processing
Create functions to:
1. Extract all solution values (P_g, Q_g, |V|, θ)
2. Compute branch flows using branch_flows.py at the optimal point
3. Calculate losses (sum of P_ij + P_ji for all branches)
4. Identify most loaded 20 branches by loading percentage
5. Verify feasibility (check all constraint violations)

### Phase 4: Report Generation
Create `/root/report.json` with structure:
```json
{
  "summary": {
    "total_cost_per_hour": <float>,
    "total_load_MW": <float>,
    "total_load_MVAr": <float>,
    "total_generation_MW": <float>,
    "total_generation_MVAr": <float>,
    "total_losses_MW": <float>,
    "solver_status": "optimal" | "suboptimal" | "infeasible"
  },
  "generators": [
    {
      "id": <bus_id>,
      "bus": <bus_num>,
      "pg_MW": <P_g>,
      "qg_MVAr": <Q_g>,
      "pmin_MW": <P_min>,
      "pmax_MW": <P_max>,
      "qmin_MVAr": <Q_min>,
      "qmax_MVAr": <Q_max>
    },
    ...
  ],
  "buses": [
    {
      "id": <bus_id>,
      "vm_pu": <|V|>,
      "va_deg": <θ_degrees>,
      "vmin_pu": <V_min>,
      "vmax_pu": <V_max>
    },
    ...
  ],
  "most_loaded_branches": [
    {
      "from_bus": <F_BUS>,
      "to_bus": <T_BUS>,
      "loading_pct": <100*max(|S_ij|, |S_ji|)/RATE_A>,
      "flow_from_MVA": <|S_ij|*baseMVA>,
      "flow_to_MVA": <|S_ji|*baseMVA>,
      "limit_MVA": <RATE_A*baseMVA>
    },
    ... (top 20 by loading_pct)
  ],
  "feasibility_check": {
    "max_p_mismatch_MW": <max P balance error>,
    "max_q_mismatch_MVAr": <max Q balance error>,
    "max_voltage_violation_pu": <max V bounds violation>,
    "max_branch_overload_MVA": <max MVA overload>
  }
}
```

## Critical Files to Create/Modify
1. **`/root/acopf_solver.py`** (main solver implementation)
2. **`/root/report.json`** (output report)

## Verification Plan
1. Check that solver converges to an optimal solution
2. Verify all constraints are satisfied (feasibility check ≈ 0)
3. Validate that total generation ≥ total load (accounting for losses)
4. Spot-check branch flows against math model equations
5. Confirm report JSON matches required schema
6. Review most-loaded branches are reasonable (match network congestion patterns)

## Notes
- The branch_flows.py script from the AC-branch-pi-model skill handles all complex power flow calculations
- Will need to convert network data from MATPOWER format during parsing
- CasADi allows us to use symbolic differentiation for efficient NLP solution
- IPOPT is a robust interior-point NLP solver suitable for OPF problems
