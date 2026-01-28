#!/usr/bin/env python3
"""
AC Optimal Power Flow Solver using CasADi and IPOPT

Solves the AC-OPF problem based on the mathematical model in math-model.md
"""

import json
import numpy as np
import casadi as ca
from collections import defaultdict

# Load network data
with open('/root/network.json', 'r') as f:
    network = json.load(f)

baseMVA = network['baseMVA']
buses = np.array(network['bus'])
gens = np.array(network['gen'])
branches = np.array(network['branch'])

# Extract bus data
n_bus = len(buses)
bus_id_to_idx = {int(buses[i, 0]): i for i in range(n_bus)}
bus_ids = [int(buses[i, 0]) for i in range(n_bus)]
Pd = buses[:, 2] / baseMVA  # Load active power (MW -> pu)
Qd = buses[:, 3] / baseMVA  # Load reactive power (MVAr -> pu)
Vmin = buses[:, 12]         # Voltage minimum
Vmax = buses[:, 11]         # Voltage maximum
bus_type = buses[:, 1]      # Bus type: 1=load, 2=gen, 3=slack

# Extract generator data
n_gen = len(gens)
gen_idx_to_bus = {}
gen_at_bus = defaultdict(list)
for k in range(n_gen):
    bus_num = int(gens[k, 0])
    bus_idx = bus_id_to_idx[bus_num]
    gen_idx_to_bus[k] = bus_idx
    gen_at_bus[bus_idx].append(k)

Pg_min = gens[:, 9] / baseMVA      # Min real power
Pg_max = gens[:, 8] / baseMVA      # Max real power
Qg_min = gens[:, 4] / baseMVA      # Min reactive power
Qg_max = gens[:, 3] / baseMVA      # Max reactive power
c2 = gens[:, 5]                     # Quadratic cost coefficient
c1 = gens[:, 6]                     # Linear cost coefficient
c0 = gens[:, 7]                     # Constant cost

# Extract branch data
n_branch = len(branches)
br_from = [int(branches[i, 0]) for i in range(n_branch)]
br_to = [int(branches[i, 1]) for i in range(n_branch)]
br_r = branches[:, 2]               # Resistance
br_x = branches[:, 3]               # Reactance
br_b = branches[:, 4]               # Shunt susceptance
br_rate = branches[:, 5] / baseMVA  # MVA rating

# Build series admittance
br_y = 1.0 / (br_r + 1j * br_x)

# Identify reference bus (slack bus, type 3)
ref_bus_idx = None
for i in range(n_bus):
    if bus_type[i] == 3:
        ref_bus_idx = i
        break

if ref_bus_idx is None:
    # If no type-3, use bus 1
    ref_bus_idx = bus_id_to_idx[1]

print(f"Reference bus: {bus_ids[ref_bus_idx]} (index {ref_bus_idx})")
print(f"Number of buses: {n_bus}, generators: {n_gen}, branches: {n_branch}")

# ==============================================================================
# Build the optimization problem
# ==============================================================================

# Decision variables
Vm = ca.MX.sym("Vm", n_bus)   # Voltage magnitudes
Va = ca.MX.sym("Va", n_bus)   # Voltage angles (radians)
Pg = ca.MX.sym("Pg", n_gen)   # Real power dispatch
Qg = ca.MX.sym("Qg", n_gen)   # Reactive power dispatch

x = ca.vertcat(Vm, Va, Pg, Qg)

# Objective: minimize generation cost
obj = ca.MX(0)
for k in range(n_gen):
    # Cost in MW, convert to pu
    Pg_MW = Pg[k] * baseMVA
    obj += c2[k] * Pg_MW**2 + c1[k] * Pg_MW + c0[k]

# ==============================================================================
# Constraints
# ==============================================================================

g_expr = []  # Constraint expressions
lbg = []     # Lower bounds
ubg = []     # Upper bounds

# 1. Reference bus angle constraint: Va[ref] = 0
g_expr.append(Va[ref_bus_idx])
lbg.append(0.0)
ubg.append(0.0)

# 2. Power balance constraints at each bus
# P: sum(Pg) - sum(Pd) - sum(Gsh*|V|^2) = sum(P_flow)
# Q: sum(Qg) - sum(Qd) - sum(Bsh*|V|^2) = sum(Q_flow)

# First, build branch flow models
# For branch from i to j:
# S_ij = Y_ij*(|V_i|^2/|T|^2) - Y_ij*V_i*conj(V_j)/T  [forward]
# S_ji = Y_ij*(|V_j|^2) - Y_ij*conj(V_i)*V_j/conj(T)  [reverse, no tap on j side]

for i in range(n_bus):
    # Real power balance
    P_gen = ca.MX(0)
    for k in gen_at_bus[i]:
        P_gen += Pg[k]

    P_load = Pd[i]  # Fixed load

    P_flow = ca.MX(0)
    Q_flow = ca.MX(0)

    # Loop over branches connected to bus i
    for b in range(n_branch):
        from_idx = bus_id_to_idx[br_from[b]]
        to_idx = bus_id_to_idx[br_to[b]]

        # Complex voltages using rectangular form: V = Vm * (cos(Va) + j*sin(Va))
        V_from_r = Vm[from_idx] * ca.cos(Va[from_idx])
        V_from_i = Vm[from_idx] * ca.sin(Va[from_idx])
        V_to_r = Vm[to_idx] * ca.cos(Va[to_idx])
        V_to_i = Vm[to_idx] * ca.sin(Va[to_idx])

        # Series admittance (real part is conductance, imag is susceptance)
        G = br_y[b].real
        B = br_y[b].imag

        if from_idx == i:
            # Branch flows FROM this bus
            # S_ij = (G + jB)|V_i|^2 - (G + jB)*V_i*conj(V_j)
            # Expand: (G + jB) * (Vm^2) - (G + jB)*(Vr + jVi)*(Vr - jVi)
            real_part = G * Vm[i]**2 - (G * (V_from_r * V_to_r + V_from_i * V_to_i) + B * (V_from_i * V_to_r - V_from_r * V_to_i))
            imag_part = B * Vm[i]**2 - (B * (V_from_r * V_to_r + V_from_i * V_to_i) - G * (V_from_i * V_to_r - V_from_r * V_to_i))
            P_flow += real_part
            Q_flow += imag_part

        elif to_idx == i:
            # Branch flows TO this bus (reverse)
            # S_ji = (G + jB)|V_j|^2 - (G + jB)*V_j*conj(V_i)
            real_part = G * Vm[i]**2 - (G * (V_to_r * V_from_r + V_to_i * V_from_i) + B * (V_to_i * V_from_r - V_to_r * V_from_i))
            imag_part = B * Vm[i]**2 - (B * (V_to_r * V_from_r + V_to_i * V_from_i) - G * (V_to_i * V_from_r - V_to_r * V_from_i))
            P_flow += real_part
            Q_flow += imag_part

    # Power balance: P_gen - P_load = P_flow
    g_expr.append(P_gen - P_load - P_flow)
    lbg.append(0.0)
    ubg.append(0.0)

    # Reactive power balance: Q_gen - Q_load = Q_flow
    Q_gen = ca.MX(0)
    for k in gen_at_bus[i]:
        Q_gen += Qg[k]

    g_expr.append(Q_gen - Qd[i] - Q_flow)
    lbg.append(0.0)
    ubg.append(0.0)

# 3. Branch power limit constraints
for b in range(n_branch):
    from_idx = bus_id_to_idx[br_from[b]]
    to_idx = bus_id_to_idx[br_to[b]]

    # Complex voltages in rectangular form
    V_from_r = Vm[from_idx] * ca.cos(Va[from_idx])
    V_from_i = Vm[from_idx] * ca.sin(Va[from_idx])
    V_to_r = Vm[to_idx] * ca.cos(Va[to_idx])
    V_to_i = Vm[to_idx] * ca.sin(Va[to_idx])

    G = br_y[b].real
    B = br_y[b].imag

    # From -> To direction
    # S_ij = (G + jB)|V_i|^2 - (G + jB)*V_i*conj(V_j)
    P_ij = G * Vm[from_idx]**2 - (G * (V_from_r * V_to_r + V_from_i * V_to_i) + B * (V_from_i * V_to_r - V_from_r * V_to_i))
    Q_ij = B * Vm[from_idx]**2 - (B * (V_from_r * V_to_r + V_from_i * V_to_i) - G * (V_from_i * V_to_r - V_from_r * V_to_i))
    S_mag_ij = ca.sqrt(P_ij**2 + Q_ij**2)

    g_expr.append(S_mag_ij)
    lbg.append(-ca.inf)
    ubg.append(br_rate[b])

    # To -> From direction
    # S_ji = (G + jB)|V_j|^2 - (G + jB)*V_j*conj(V_i)
    P_ji = G * Vm[to_idx]**2 - (G * (V_to_r * V_from_r + V_to_i * V_from_i) + B * (V_to_i * V_from_r - V_to_r * V_from_i))
    Q_ji = B * Vm[to_idx]**2 - (B * (V_to_r * V_from_r + V_to_i * V_from_i) - G * (V_to_i * V_from_r - V_to_r * V_from_i))
    S_mag_ji = ca.sqrt(P_ji**2 + Q_ji**2)

    g_expr.append(S_mag_ji)
    lbg.append(-ca.inf)
    ubg.append(br_rate[b])

# Stack all constraints
g = ca.vertcat(*g_expr)

# ==============================================================================
# Variable bounds
# ==============================================================================

lbx = np.concatenate([
    Vmin,                               # Voltage magnitude lower bounds
    np.full(n_bus, -np.pi),             # Angle lower bounds (radians)
    Pg_min,                             # Generator P lower bounds
    Qg_min                              # Generator Q lower bounds
]).tolist()

ubx = np.concatenate([
    Vmax,                               # Voltage magnitude upper bounds
    np.full(n_bus, np.pi),              # Angle upper bounds (radians)
    Pg_max,                             # Generator P upper bounds
    Qg_max                              # Generator Q upper bounds
]).tolist()

# ==============================================================================
# Initialize solution
# ==============================================================================

# Flat start: all voltages at 1.0 pu, all angles at 0
x0 = np.concatenate([
    np.ones(n_bus),                     # Vm = 1.0
    np.zeros(n_bus),                    # Va = 0
    (Pg_min + Pg_max) / 2,              # Pg at midpoint
    np.zeros(n_gen)                     # Qg = 0
])

# ==============================================================================
# Solve
# ==============================================================================

nlp = {"x": x, "f": obj, "g": g}
opts = {
    "ipopt.print_level": 0,
    "ipopt.max_iter": 3000,
    "ipopt.tol": 1e-6,
    "ipopt.acceptable_tol": 1e-5,
    "ipopt.mu_strategy": "adaptive",
    "ipopt.nlp_scaling_method": "gradient-based",
    "print_time": False,
}

solver = ca.nlpsol("solver", "ipopt", nlp, opts)

print("\nSolving AC-OPF...")
sol = solver(x0=x0, lbx=lbx, ubx=ubx, lbg=lbg, ubg=ubg)
x_opt = np.array(sol["x"]).flatten()

# Unpack solution
Vm_sol = x_opt[:n_bus]
Va_sol = x_opt[n_bus:2*n_bus]
Pg_sol = x_opt[2*n_bus:2*n_bus+n_gen]
Qg_sol = x_opt[2*n_bus+n_gen:]

# Convert to MW, MVAr, degrees
Pg_MW = Pg_sol * baseMVA
Qg_MVAr = Qg_sol * baseMVA
Va_deg = Va_sol * 180.0 / np.pi

print(f"Solver status: {sol['stats']['return_status']}")
print(f"Objective value (cost): ${float(sol['f']):,.2f}/hr")

# ==============================================================================
# Compute branch flows and build report
# ==============================================================================

branch_flows = []

for b in range(n_branch):
    from_idx = bus_id_to_idx[br_from[b]]
    to_idx = bus_id_to_idx[br_to[b]]

    # Complex voltages
    V_from = Vm_sol[from_idx] * np.exp(1j * Va_sol[from_idx])
    V_to = Vm_sol[to_idx] * np.exp(1j * Va_sol[to_idx])

    G = br_y[b].real
    B = br_y[b].imag

    # Forward flow
    S_ij = (G + 1j * B) * Vm_sol[from_idx]**2 - (G + 1j * B) * V_from * np.conj(V_to)
    S_ij_MVA = np.abs(S_ij) * baseMVA

    # Reverse flow
    S_ji = (G + 1j * B) * Vm_sol[to_idx]**2 - (G + 1j * B) * V_to * np.conj(V_from)
    S_ji_MVA = np.abs(S_ji) * baseMVA

    loading = max(S_ij_MVA, S_ji_MVA) / (br_rate[b] * baseMVA) * 100

    branch_flows.append({
        'from_bus': br_from[b],
        'to_bus': br_to[b],
        'flow_from_MVA': S_ij_MVA,
        'flow_to_MVA': S_ji_MVA,
        'limit_MVA': br_rate[b] * baseMVA,
        'loading_pct': loading
    })

# Sort by loading
branch_flows.sort(key=lambda x: x['loading_pct'], reverse=True)
most_loaded = branch_flows[:5]

# ==============================================================================
# Compute losses and totals
# ==============================================================================

total_gen_P = np.sum(Pg_MW)
total_gen_Q = np.sum(Qg_MVAr)
total_load_P = np.sum(Pd) * baseMVA
total_load_Q = np.sum(Qd) * baseMVA

# Compute losses from branch flows
total_loss_P = 0
for b in range(n_branch):
    from_idx = bus_id_to_idx[br_from[b]]
    to_idx = bus_id_to_idx[br_to[b]]

    V_from = Vm_sol[from_idx] * np.exp(1j * Va_sol[from_idx])
    V_to = Vm_sol[to_idx] * np.exp(1j * Va_sol[to_idx])

    G = br_y[b].real
    B = br_y[b].imag

    # Loss is I^2 * R
    I_ij = (G + 1j * B) * (V_from / 1.0 - V_to / 1.0)
    loss = np.abs(I_ij)**2 * br_r[b]
    total_loss_P += loss * baseMVA

# ==============================================================================
# Feasibility check
# ==============================================================================

# Recompute constraints to check feasibility
max_p_mismatch = 0
max_q_mismatch = 0

for i in range(n_bus):
    P_gen = np.sum([Pg_MW[k] for k in gen_at_bus[i]])
    P_load = Pd[i] * baseMVA

    P_flow = 0
    Q_flow = 0
    Q_gen = np.sum([Qg_MVAr[k] for k in gen_at_bus[i]])
    Q_load = Qd[i] * baseMVA

    for b in range(n_branch):
        from_idx = bus_id_to_idx[br_from[b]]
        to_idx = bus_id_to_idx[br_to[b]]

        V_from = Vm_sol[from_idx] * np.exp(1j * Va_sol[from_idx])
        V_to = Vm_sol[to_idx] * np.exp(1j * Va_sol[to_idx])

        G = br_y[b].real
        B = br_y[b].imag

        if from_idx == i:
            S_ij = (G + 1j * B) * Vm_sol[i]**2 - (G + 1j * B) * V_from * np.conj(V_to)
            P_flow += np.real(S_ij) * baseMVA
            Q_flow += np.imag(S_ij) * baseMVA
        elif to_idx == i:
            S_ji = (G + 1j * B) * Vm_sol[i]**2 - (G + 1j * B) * V_to * np.conj(V_from)
            P_flow += np.real(S_ji) * baseMVA
            Q_flow += np.imag(S_ji) * baseMVA

    mismatch_p = abs(P_gen - P_load - P_flow)
    mismatch_q = abs(Q_gen - Q_load - Q_flow)

    max_p_mismatch = max(max_p_mismatch, mismatch_p)
    max_q_mismatch = max(max_q_mismatch, mismatch_q)

max_v_violation = 0
for i in range(n_bus):
    if Vm_sol[i] < Vmin[i]:
        max_v_violation = max(max_v_violation, Vmin[i] - Vm_sol[i])
    if Vm_sol[i] > Vmax[i]:
        max_v_violation = max(max_v_violation, Vm_sol[i] - Vmax[i])

max_branch_overload = 0
for b in range(n_branch):
    flow_ij = branch_flows[b]['flow_from_MVA']
    flow_ji = branch_flows[b]['flow_to_MVA']
    limit = branch_flows[b]['limit_MVA']
    if flow_ij > limit:
        max_branch_overload = max(max_branch_overload, flow_ij - limit)
    if flow_ji > limit:
        max_branch_overload = max(max_branch_overload, flow_ji - limit)

# ==============================================================================
# Build report
# ==============================================================================

report = {
    "summary": {
        "total_cost_per_hour": float(sol['f']),
        "total_load_MW": total_load_P,
        "total_load_MVAr": total_load_Q,
        "total_generation_MW": total_gen_P,
        "total_generation_MVAr": total_gen_Q,
        "total_losses_MW": total_loss_P,
        "solver_status": str(sol['stats']['return_status'])
    },
    "generators": [
        {
            "id": int(gens[k, 0]),
            "bus": int(gens[k, 0]),
            "pg_MW": float(Pg_MW[k]),
            "qg_MVAr": float(Qg_MVAr[k]),
            "pmin_MW": float(Pg_min[k] * baseMVA),
            "pmax_MW": float(Pg_max[k] * baseMVA),
            "qmin_MVAr": float(Qg_min[k] * baseMVA),
            "qmax_MVAr": float(Qg_max[k] * baseMVA)
        }
        for k in range(n_gen)
    ],
    "buses": [
        {
            "id": bus_ids[i],
            "vm_pu": float(Vm_sol[i]),
            "va_deg": float(Va_deg[i]),
            "vmin_pu": float(Vmin[i]),
            "vmax_pu": float(Vmax[i])
        }
        for i in range(n_bus)
    ],
    "most_loaded_branches": [
        {
            "from_bus": int(flow['from_bus']),
            "to_bus": int(flow['to_bus']),
            "loading_pct": float(flow['loading_pct']),
            "flow_from_MVA": float(flow['flow_from_MVA']),
            "flow_to_MVA": float(flow['flow_to_MVA']),
            "limit_MVA": float(flow['limit_MVA'])
        }
        for flow in most_loaded
    ],
    "feasibility_check": {
        "max_p_mismatch_MW": float(max_p_mismatch),
        "max_q_mismatch_MVAr": float(max_q_mismatch),
        "max_voltage_violation_pu": float(max_v_violation),
        "max_branch_overload_MVA": float(max_branch_overload)
    }
}

# Write report to file
with open('/root/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("\nReport written to /root/report.json")
print(f"\nSummary:")
print(f"  Cost: ${report['summary']['total_cost_per_hour']:,.2f}/hr")
print(f"  Total Generation: {report['summary']['total_generation_MW']:.2f} MW, {report['summary']['total_generation_MVAr']:.2f} MVAr")
print(f"  Total Load: {report['summary']['total_load_MW']:.2f} MW, {report['summary']['total_load_MVAr']:.2f} MVAr")
print(f"  Total Losses: {report['summary']['total_losses_MW']:.2f} MW")
print(f"\nFeasibility:")
print(f"  Max P mismatch: {report['feasibility_check']['max_p_mismatch_MW']:.6f} MW")
print(f"  Max Q mismatch: {report['feasibility_check']['max_q_mismatch_MVAr']:.6f} MVAr")
print(f"  Max voltage violation: {report['feasibility_check']['max_voltage_violation_pu']:.6f} pu")
print(f"  Max branch overload: {report['feasibility_check']['max_branch_overload_MVA']:.6f} MVA")

EOF
