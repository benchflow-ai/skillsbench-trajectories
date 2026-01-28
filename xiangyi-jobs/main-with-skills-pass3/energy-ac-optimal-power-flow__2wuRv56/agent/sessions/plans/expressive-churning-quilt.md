# AC-OPF Base Case Planning Tool Implementation

## Problem Summary
Build an AC Optimal Power Flow (AC-OPF) solver for ISO operators to:
1. Find a least-cost, AC-feasible operating point for tomorrow's peak hour
2. Establish voltage profile and verify day-ahead market schedule feasibility
3. Generate a report.json with all operational data and feasibility metrics

**Network Data**: 300 buses, 69 generators, 411 branches
**Output Format**: JSON report with summary, generators, buses, loaded branches, and feasibility checks

## Implementation Approach

### Technology Choice
**Python with Pyomo + ipopt/Knitro** (or similar)

Why:
- AC-OPF is a nonlinear, non-convex constrained optimization problem
- Pyomo provides flexible algebraic modeling for power systems
- ipopt is a mature interior-point solver for such problems
- Python ecosystem has pypower, pandapower libraries for validation

Alternative considered: Julia/JuMP - excellent but less installed by default

### Architecture

**Phase 1: Problem Setup (ac_opf.py)**
- Parse network.json into structured format (buses, generators, branches, loads)
- Build Pyomo concrete model with:
  - Decision variables: generator power (P, Q), bus voltages (V magnitude and angle)
  - Objective: minimize cost = Σ(c2*P² + c1*P + c0)
  - Constraints:
    - Voltage magnitude bounds
    - Generator power bounds
    - Reference bus angle = 0
    - Power balance (AC power flow equations)
    - Branch power flow limits
    - Branch current limits
    - Voltage angle difference limits

**Phase 2: Solver Execution (ac_opf.py)**
- Initialize solver with default/warm-start from flat-start
- Solve the optimization problem
- Extract solution status and operation point

**Phase 3: Report Generation (report.py)**
- Extract solution values for:
  - Generator outputs (P, Q)
  - Bus voltages (magnitude, angle)
  - Branch flows
- Calculate derived metrics:
  - Total cost, load totals, generation totals, losses
  - Most-loaded branches (top 5-10)
  - Feasibility metrics: power mismatch, voltage violations, branch overloads
- Write report.json following provided schema

### Critical Implementation Details

**AC Power Flow Equations** (from math-model.md):
- Uses complex voltage variables V_i
- Branch flows: S_ij = (Y_ij + Y^c_ij)* |V_i|²/|T_ij|² - Y_ij* V_i V_j*/T_ij
- Power balance: ΣS_g - ΣS_d - Y_s*|V|² = ΣS_ij

**Data Structure** (from network.json column_info):
- bus: [bus_i, type, Pd, Qd, Gs, Bs, area, zone, V_m, V_a, V_base, V_max, V_min]
- gen: [bus, Pg, Qg, Qmax, Qmin, V_g, mBase, status, Pmax, Pmin, Pc1, Pc2, Qc1min, Qc1max, Qc2min, Qc2max, ramp_ag, ramp_10, ramp_30, ramp_q, apf]
- branch: [from_bus, to_bus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angle_min, angle_max]
- gencost: [type, startup, shutdown, n, c2, c1, c0]

**Report JSON Schema**:
- summary: cost, load MW/MVAr, generation MW/MVAr, losses, solver status
- generators: id, bus, pg_MW, qg_MVAr, limits
- buses: id, vm_pu, va_deg, voltage limits
- most_loaded_branches: top N by loading_pct (95%+ first)
- feasibility_check: power mismatch, voltage violations, overloads

### File Structure
```
/root/
  ac_opf.py          # Main solver: model building & execution
  report.py          # Report generation from solution
  run_opf.py         # Entry point: orchestrates solution
  report.json        # Output
```

### Dependencies
- pyomo (optimization modeling)
- ipopt or knitro (nonlinear solver) - will attempt ipopt with fallback to scipy.optimize
- numpy, scipy (numerical operations)
- json (I/O)

**Solver Strategy**: Try ipopt first (best for AC-OPF). If unavailable, use Pyomo's default IPOPT installation attempt or fallback to GLPK/other available solvers. Log warning if using suboptimal solver.

**Report Detail**: Include top 10 most-loaded branches by loading percentage (prioritizing >80% utilization)

### Execution Flow
1. run_opf.py loads network.json
2. ac_opf.py builds and solves Pyomo model
3. report.py formats results and writes report.json
4. User can verify AC-feasibility and cost optimality

### Testing & Verification
- Check solver status = "optimal"
- Verify all constraints satisfied: P/Q balance, voltage limits, branch limits
- Compare feasibility_check metrics (should be near-zero for optimal solution)
- Validate report structure matches provided JSON schema
- Check physically reasonable values: voltage 0.9-1.1 pu, power flows within limits

### Known Challenges & Solutions
1. **Non-convex problem**: Use good solver (ipopt) + possibly multiple starting points
2. **Numerical issues**: Normalize voltages to pu, scale equations properly
3. **Missing load data**: network.json has Pd/Qd in bus table (not separate 'load' array)
4. **Transformer ratios**: Handle complex transformer parameters in branch equations

## Implementation Plan (Step-by-step)

1. Create ac_opf.py - Pyomo model for AC-OPF
2. Create report.py - Extract and format results
3. Create run_opf.py - Main orchestration script
4. Test with network.json data
5. Output report.json and verify feasibility
