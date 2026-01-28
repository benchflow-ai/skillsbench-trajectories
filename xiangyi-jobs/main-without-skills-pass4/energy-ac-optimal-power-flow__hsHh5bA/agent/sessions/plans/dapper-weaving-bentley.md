# AC-OPF Solver for ISO Peak Hour Base Case

## Overview
Implement an AC Optimal Power Flow (OPF) solver using CasADi/IPOPT and the AC branch pi-model equations from `math-model.md`. The solver will:
1. Minimize generation cost subject to AC power flow equations
2. Enforce voltage limits, generator limits, and branch thermal limits
3. Generate a JSON report with operational data and feasibility metrics

## Key Findings

### Data Structure (network.json)
- **Buses**: 300 buses, types 1 (PQ), 2 (PV), 3 (Slack)
- **Generators**: 69 generators with quadratic cost functions
- **Branches**: 411 branches with series impedance, shunts, and MVA limits
- **Loads**: Embedded in bus data (columns 2-3: PD, QD in MW/MVAr)
- **Base MVA**: 100 MVA
- **Total Load**: ~23,526 MW, ~7,788 MVAr

### Technology Stack
- **Solver**: CasADi + IPOPT for large-scale NLP optimization
- **Branch Flow Model**: Exact AC pi-model from skill `ac-branch-pi-model`
- **Cost Function**: Quadratic generator cost (c2*P² + c1*P + c0)

## Implementation Plan

### Phase 1: Data Loading & Preprocessing
**File**: `ac_opf_solver.py` (main)

1. Load network.json and parse all data arrays
2. Build bus ID → array index mappings
3. Extract load data from bus array (columns 2-3)
4. Extract generator parameters and costs
5. Identify slack bus (type 3) and set VA = 0 constraint
6. Initialize voltage/angle starting points from bus data (columns 7-8)

### Phase 2: Build Symbolic NLP
**Using CasADi**

1. **Decision Variables**:
   - Vm: voltage magnitudes for all 300 buses (pu)
   - Va: voltage angles for all 300 buses (rad)
   - Pg: real power for 69 generators (MW)
   - Qg: reactive power for 69 generators (MVAr)

2. **Objective Function**:
   - `sum(c2[k] * Pg[k]² + c1[k] * Pg[k] + c0[k])` for each generator k

3. **Constraints**:
   - **AC Power Flow** (Nodal Balance): For each bus i
     - Σ(Pg_k) - Σ(Pd) - Gs*Vm² - P_branch_out = 0
     - Σ(Qg_k) - Σ(Qd) + Bs*Vm² - Q_branch_out = 0
     - Where P_branch_out, Q_branch_out computed using branch_flows.py for all connected branches

   - **Reference Angle**: Va[slack_bus] = 0

   - **Generator Limits**:
     - Pmin[k] ≤ Pg[k] ≤ Pmax[k]
     - Qmin[k] ≤ Qg[k] ≤ Qmax[k]

   - **Voltage Limits**:
     - Vmin[i] ≤ Vm[i] ≤ Vmax[i]

   - **Angle Difference Limits** (per branch):
     - ANGMIN[ij] ≤ Va[i] - Va[j] ≤ ANGMAX[ij]

   - **Branch MVA Limits**:
     - |S_ij| ≤ RATE_A (computed for both directions)
     - |S_ji| ≤ RATE_A

4. **Variable Bounds**:
   - Vm: [Vmin, Vmax] for each bus
   - Va: [-π, π] (unrestricted except reference)
   - Pg, Qg: [min, max] from gen data

### Phase 3: Solver Setup & Execution
**CasADi IPOPT configuration**
- Tolerance: 1e-7
- Acceptable tolerance: 1e-5
- Max iterations: 2000
- Initialization: Two attempts
  - Attempt 1: Data-derived (from network.json initial values)
  - Attempt 2: Flat start (Vm=1.0, Va=0, generators at minimum)

### Phase 4: Post-Processing & Report Generation
**File**: `report.json`

1. **Extract Solution**:
   - Bus voltages (Vm, Va), all generator dispatch (Pg, Qg)
   - Compute branch flows using branch_flows.py
   - Compute losses: sum(P_ij + P_ji) for all branches

2. **Feasibility Check**:
   - Power balance mismatches (should be <1e-3 MW/MVAr)
   - Voltage violations (should be 0)
   - Branch overloads (should be 0)

3. **Most Loaded Branches**:
   - Compute loading % for all branches
   - Sort and report top N branches

4. **JSON Structure** (per requirements):
   - summary: cost, loads, generation, losses, solver status
   - generators: dispatch for all 69 units
   - buses: voltages for all 300 buses
   - most_loaded_branches: top 5-10 branches by loading
   - feasibility_check: max violations

## Critical Implementation Notes

### Per-Unit Conversion
- **Input/Output**: Generator costs and power in MW/MVAr
- **Solver Internal**: Use per-unit by dividing/multiplying by baseMVA (100)
- Cost functions may expect MW—verify in gencost parsing

### Bus ID Mapping
- Bus IDs in data may not be sequential (1-300)
- Must create bus_id_to_idx mapping for reliable lookups
- All array operations use indices, not bus IDs

### Branch Flow Computation
- Use branch_flows.py for exact AC pi-model flows
- Inputs: Vm, Va (pu/rad), branch row, bus_id_to_idx
- Both P_ij/Q_ij and P_ji/Q_ji needed for power balance and MVA limits
- Convert to MW/MVAr for output using baseMVA

### Slack Bus Constraint
- Identify type=3 bus (slack)
- Enforce Va[slack] = 0 (reference angle)
- Pg, Qg at slack bus determined by power balance, not limited by Pmin/Pmax

### Common Pitfalls
- **MATPOWER tap=0** means 1.0 (no transformer)—handled in branch_flows.py
- **Angle units**: branch data in degrees (SHIFT, ANGMIN/MAX), solver uses radians
- **Shunt signs**: Gs/Bs are conductance/susceptance; confirm sign convention
- **Cost function**: c2 may be 0 (linear cost)—handle gracefully

## Verification (How to Test)
1. Run solver on full 300-bus network
2. Check solver status = "optimal" or "locally optimal"
3. Verify all constraints satisfied:
   - Power mismatches < 0.1 MW/MVAr
   - Voltages within bounds
   - No branch overloads
4. Inspect report.json:
   - Total cost is positive and reasonable
   - Generation ≈ Load + Losses
   - Most loaded branches have loading_pct ≤ 100%
5. Compare against known test cases (if available)

## Files to Create/Modify
- **Create**: `/root/ac_opf_solver.py` (main implementation)
- **Output**: `/root/report.json` (final results)
