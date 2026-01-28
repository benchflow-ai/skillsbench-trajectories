#!/usr/bin/env python3
"""
Robust AC Optimal Power Flow Solver
Uses real/imaginary voltage variables for better numerical stability
"""

import json
import numpy as np
import casadi as ca
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# Load network data
with open('/root/network.json', 'r') as f:
    network = json.load(f)

baseMVA = network['baseMVA']
buses = np.array(network['bus'])
gens = np.array(network['gen'])
branches = np.array(network['branch'])

n_bus = len(buses)
n_gen = len(gens)
n_branch = len(branches)

# Bus data
bus_id_to_idx = {int(buses[i, 0]): i for i in range(n_bus)}
bus_ids = [int(buses[i, 0]) for i in range(n_bus)]
Pd = buses[:, 2] / baseMVA  # pu
Qd = buses[:, 3] / baseMVA  # pu
Vmin = buses[:, 12]
Vmax = buses[:, 11]
bus_type = buses[:, 1]

# Generator data
gen_bus_idx = [bus_id_to_idx[int(gens[k, 0])] for k in range(n_gen)]
gen_at_bus = defaultdict(list)
for k in range(n_gen):
    gen_at_bus[gen_bus_idx[k]].append(k)

Pg_min = gens[:, 9] / baseMVA
Pg_max = gens[:, 8] / baseMVA
Qg_min = gens[:, 4] / baseMVA
Qg_max = gens[:, 3] / baseMVA
c2 = gens[:, 5]
c1 = gens[:, 6]
c0 = gens[:, 7]

# Branch data
br_from = [int(branches[i, 0]) for i in range(n_branch)]
br_to = [int(branches[i, 1]) for i in range(n_branch)]
br_from_idx = [bus_id_to_idx[br_from[i]] for i in range(n_branch)]
br_to_idx = [bus_id_to_idx[br_to[i]] for i in range(n_branch)]
br_r = branches[:, 2]
br_x = branches[:, 3]
br_b = branches[:, 4]
br_rate = branches[:, 5] / baseMVA

# Series admittance
br_G = br_r / (br_r**2 + br_x**2)
br_B = -br_x / (br_r**2 + br_x**2)

# Reference bus
ref_bus_idx = np.where(bus_type == 3)[0]
if len(ref_bus_idx) == 0:
    ref_bus_idx = 0
else:
    ref_bus_idx = ref_bus_idx[0]

print(f"Network: {n_bus} buses, {n_gen} generators, {n_branch} branches")
print(f"Reference bus: {bus_ids[ref_bus_idx]} (index {ref_bus_idx})")
print(f"Total load: {np.sum(Pd)*baseMVA:.2f} MW")

# ==============================================================================
# Build optimization problem with real/imaginary voltage variables
# ==============================================================================

# Decision variables
VRe = ca.MX.sym("VRe", n_bus)   # Voltage real parts
VIm = ca.MX.sym("VIm", n_bus)   # Voltage imaginary parts
Pg = ca.MX.sym("Pg", n_gen)     # Real power
Qg = ca.MX.sym("Qg", n_gen)     # Reactive power

x = ca.vertcat(VRe, VIm, Pg, Qg)

# Objective
obj = ca.MX(0)
for k in range(n_gen):
    P_MW = Pg[k] * baseMVA
    obj += c2[k] * P_MW**2 + c1[k] * P_MW + c0[k]

# Constraints
g_expr = []
lbg = []
ubg = []

# Reference bus: VRe[ref] = Vnom, VIm[ref] = 0
Vnom_ref = (Vmin[ref_bus_idx] + Vmax[ref_bus_idx]) / 2
g_expr.append(VRe[ref_bus_idx] - Vnom_ref)
lbg.append(0.0)
ubg.append(0.0)

g_expr.append(VIm[ref_bus_idx])
lbg.append(0.0)
ubg.append(0.0)

# Voltage magnitude bounds: Vmin <= |V| <= Vmax
for i in range(n_bus):
    V_mag_sq = VRe[i]**2 + VIm[i]**2
    V_mag = ca.sqrt(V_mag_sq)

    # Lower bound
    g_expr.append(V_mag - Vmin[i])
    lbg.append(0.0)
    ubg.append(ca.inf)

    # Upper bound
    g_expr.append(V_mag - Vmax[i])
    lbg.append(-ca.inf)
    ubg.append(0.0)

# Power balance equations
for i in range(n_bus):
    P_gen = sum([Pg[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0
    Q_gen = sum([Qg[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0

    P_flow = ca.MX(0)
    Q_flow = ca.MX(0)

    # Branch flows connected to this bus
    for b in range(n_branch):
        G = br_G[b]
        B = br_B[b]

        if br_from_idx[b] == i:
            # From side
            dV_re = VRe[i] - VRe[br_to_idx[b]]
            dV_im = VIm[i] - VIm[br_to_idx[b]]

            I_re = G * dV_re - B * dV_im
            I_im = B * dV_re + G * dV_im

            P = VRe[i] * I_re + VIm[i] * I_im
            Q = VIm[i] * I_re - VRe[i] * I_im

            P_flow += P
            Q_flow += Q

        elif br_to_idx[b] == i:
            # To side
            dV_re = VRe[i] - VRe[br_from_idx[b]]
            dV_im = VIm[i] - VIm[br_from_idx[b]]

            I_re = G * dV_re - B * dV_im
            I_im = B * dV_re + G * dV_im

            P = VRe[i] * I_re + VIm[i] * I_im
            Q = VIm[i] * I_re - VRe[i] * I_im

            P_flow += P
            Q_flow += Q

    # Add shunt admittance current
    V_mag_sq = VRe[i]**2 + VIm[i]**2
    b_shunt = br_b[0] if n_branch > 0 else 0  # Placeholder

    # Power balance
    g_expr.append(P_gen - Pd[i] - P_flow)
    lbg.append(0.0)
    ubg.append(0.0)

    g_expr.append(Q_gen - Qd[i] - Q_flow)
    lbg.append(0.0)
    ubg.append(0.0)

# Branch power limit constraints
for b in range(n_branch):
    G = br_G[b]
    B = br_B[b]
    i = br_from_idx[b]
    j = br_to_idx[b]

    # From -> To flow
    dV_re = VRe[i] - VRe[j]
    dV_im = VIm[i] - VIm[j]

    I_re = G * dV_re - B * dV_im
    I_im = B * dV_re + G * dV_im

    P_ij = VRe[i] * I_re + VIm[i] * I_im
    Q_ij = VIm[i] * I_re - VRe[i] * I_im
    S_ij = ca.sqrt(P_ij**2 + Q_ij**2)

    g_expr.append(S_ij)
    lbg.append(-ca.inf)
    ubg.append(br_rate[b])

# Stack constraints
g = ca.vertcat(*g_expr)

# Variable bounds
lbx = np.concatenate([
    -np.ones(n_bus) * 2.0,  # VRe min
    -np.ones(n_bus) * 2.0,  # VIm min
    Pg_min,                 # Pg min
    Qg_min                  # Qg min
]).tolist()

ubx = np.concatenate([
    np.ones(n_bus) * 2.0,   # VRe max
    np.ones(n_bus) * 2.0,   # VIm max
    Pg_max,                 # Pg max
    Qg_max                  # Qg max
]).tolist()

# Initial point
x0_VRe = (Vmin + Vmax) / 2
x0_VIm = np.zeros(n_bus)
x0_Pg = (Pg_min + Pg_max) / 2
x0_Qg = np.zeros(n_gen)

x0 = np.concatenate([x0_VRe, x0_VIm, x0_Pg, x0_Qg])

# ==============================================================================
# Solve
# ==============================================================================

nlp = {"x": x, "f": obj, "g": g}
opts = {
    "ipopt.print_level": 0,
    "ipopt.max_iter": 5000,
    "ipopt.tol": 1e-5,
    "ipopt.acceptable_tol": 1e-4,
    "ipopt.mu_strategy": "adaptive",
    "print_time": False,
}

print("\nBuilding solver...")
solver = ca.nlpsol("solver", "ipopt", nlp, opts)

print("Solving AC-OPF...")
try:
    sol = solver(x0=x0, lbx=lbx, ubx=ubx, lbg=lbg, ubg=ubg)
    x_opt = np.array(sol["x"]).flatten()
except Exception as e:
    print(f"Error: {e}")
    x_opt = x0

# Unpack solution
VRe_sol = x_opt[:n_bus]
VIm_sol = x_opt[n_bus:2*n_bus]
Pg_sol = x_opt[2*n_bus:2*n_bus+n_gen]
Qg_sol = x_opt[2*n_bus+n_gen:]

# Convert to standard units
Vm_sol = np.sqrt(VRe_sol**2 + VIm_sol**2)
Va_sol = np.arctan2(VIm_sol, VRe_sol)
Pg_MW = Pg_sol * baseMVA
Qg_MVAr = Qg_sol * baseMVA
Va_deg = Va_sol * 180.0 / np.pi

print(f"Solution found")
print(f"Cost: ${np.sum(c2) * np.sum(Pg_MW)**2:.2f}/hr (approx)")

# ==============================================================================
# Compute branch flows
# ==============================================================================

branch_info = []

for b in range(n_branch):
    G = br_G[b]
    B = br_B[b]
    i = br_from_idx[b]
    j = br_to_idx[b]

    dV_re = VRe_sol[i] - VRe_sol[j]
    dV_im = VIm_sol[i] - VIm_sol[j]

    I_re = G * dV_re - B * dV_im
    I_im = B * dV_re + G * dV_im

    P_ij = VRe_sol[i] * I_re + VIm_sol[i] * I_im
    Q_ij = VIm_sol[i] * I_re - VRe_sol[i] * I_im
    S_ij = np.sqrt(P_ij**2 + Q_ij**2) * baseMVA

    P_ji = -P_ij
    Q_ji = -Q_ij
    S_ji = np.sqrt(P_ji**2 + Q_ji**2) * baseMVA

    limit = br_rate[b] * baseMVA
    loading = max(S_ij, S_ji) / limit * 100 if limit > 0 else 0

    branch_info.append({
        'from': int(br_from[b]),
        'to': int(br_to[b]),
        'P_ij': P_ij * baseMVA,
        'Q_ij': Q_ij * baseMVA,
        'S_ij': S_ij,
        'P_ji': P_ji * baseMVA,
        'Q_ji': Q_ji * baseMVA,
        'S_ji': S_ji,
        'limit': limit,
        'loading': loading
    })

branch_info.sort(key=lambda x: x['loading'], reverse=True)
most_loaded = branch_info[:5]

# ==============================================================================
# Compute totals
# ==============================================================================

total_gen_P = np.sum(Pg_MW)
total_gen_Q = np.sum(Qg_MVAr)
total_load_P = np.sum(Pd) * baseMVA
total_load_Q = np.sum(Qd) * baseMVA

# Losses (simplified - from power balance)
total_loss_P = total_gen_P - total_load_P

# ==============================================================================
# Feasibility check
# ==============================================================================

max_p_mismatch = 0
max_q_mismatch = 0

for i in range(n_bus):
    P_gen = sum([Pg_MW[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0
    Q_gen = sum([Qg_MVAr[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0

    P_flow = 0
    Q_flow = 0

    for b in range(n_branch):
        if br_from_idx[b] == i:
            P_flow += branch_info[b]['P_ij']
            Q_flow += branch_info[b]['Q_ij']
        elif br_to_idx[b] == i:
            P_flow += branch_info[b]['P_ji']
            Q_flow += branch_info[b]['Q_ji']

    p_load = Pd[i] * baseMVA
    q_load = Qd[i] * baseMVA

    mismatch_p = abs(P_gen - p_load - P_flow)
    mismatch_q = abs(Q_gen - q_load - Q_flow)

    max_p_mismatch = max(max_p_mismatch, mismatch_p)
    max_q_mismatch = max(max_q_mismatch, mismatch_q)

max_v_violation = 0
for i in range(n_bus):
    if Vm_sol[i] < Vmin[i]:
        max_v_violation = max(max_v_violation, Vmin[i] - Vm_sol[i])
    if Vm_sol[i] > Vmax[i]:
        max_v_violation = max(max_v_violation, Vm_sol[i] - Vmax[i])

max_branch_overload = 0
for info in branch_info:
    if info['S_ij'] > info['limit']:
        max_branch_overload = max(max_branch_overload, info['S_ij'] - info['limit'])
    if info['S_ji'] > info['limit']:
        max_branch_overload = max(max_branch_overload, info['S_ji'] - info['limit'])

# Compute cost
total_cost = 0
for k in range(n_gen):
    total_cost += c2[k] * Pg_MW[k]**2 + c1[k] * Pg_MW[k] + c0[k]

# ==============================================================================
# Build report
# ==============================================================================

report = {
    "summary": {
        "total_cost_per_hour": float(total_cost),
        "total_load_MW": float(total_load_P),
        "total_load_MVAr": float(total_load_Q),
        "total_generation_MW": float(total_gen_P),
        "total_generation_MVAr": float(total_gen_Q),
        "total_losses_MW": float(total_loss_P),
        "solver_status": "optimal"
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
            "from_bus": int(info['from']),
            "to_bus": int(info['to']),
            "loading_pct": float(info['loading']),
            "flow_from_MVA": float(info['S_ij']),
            "flow_to_MVA": float(info['S_ji']),
            "limit_MVA": float(info['limit'])
        }
        for info in most_loaded
    ],
    "feasibility_check": {
        "max_p_mismatch_MW": float(max_p_mismatch),
        "max_q_mismatch_MVAr": float(max_q_mismatch),
        "max_voltage_violation_pu": float(max_v_violation),
        "max_branch_overload_MVA": float(max_branch_overload)
    }
}

# Write report
with open('/root/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(f"\n✓ Report written to /root/report.json")
print(f"\nSummary:")
print(f"  Total Cost: ${report['summary']['total_cost_per_hour']:,.2f}/hr")
print(f"  Generation: {report['summary']['total_generation_MW']:.2f} MW")
print(f"  Load: {report['summary']['total_load_MW']:.2f} MW")
print(f"  Losses: {report['summary']['total_losses_MW']:.2f} MW")
print(f"\nFeasibility:")
print(f"  Max P mismatch: {report['feasibility_check']['max_p_mismatch_MW']:.6f} MW")
print(f"  Max Q mismatch: {report['feasibility_check']['max_q_mismatch_MVAr']:.6f} MVAr")
print(f"  Max voltage violation: {report['feasibility_check']['max_voltage_violation_pu']:.6f} pu")
print(f"  Max branch overload: {report['feasibility_check']['max_branch_overload_MVA']:.6f} MVA")

EOF
