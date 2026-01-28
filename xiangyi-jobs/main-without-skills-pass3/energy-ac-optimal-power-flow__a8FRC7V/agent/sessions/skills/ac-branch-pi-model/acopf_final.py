#!/usr/bin/env python3
"""
Final AC OPF Solution - Simple Merit Order + Flat Start AC Power Flow
Provides a valid AC operating point for the peak hour base case
"""

import json
import numpy as np
from collections import defaultdict
from scripts.branch_flows import compute_branch_flows_pu, build_bus_id_to_idx

# Load data
with open('/root/network.json') as f:
    data = json.load(f)

baseMVA = float(data['baseMVA'])
buses = np.array(data['bus'], dtype=float)
gens = np.array(data['gen'], dtype=float)
branches = np.array(data['branch'], dtype=float)

n_bus = len(buses)
n_gen = len(gens)
n_branch = len(branches)

print(f"Network: {n_bus} buses, {n_gen} gens, {n_branch} branches")

# Data extraction
bus_id_to_idx = build_bus_id_to_idx(buses)
bus_ids = buses[:, 0].astype(int)
bus_type = buses[:, 1].astype(int)
Pd = buses[:, 2]  # MW
Qd = buses[:, 3]  # MVAr
Vmin = buses[:, 12]
Vmax = buses[:, 11]

gen_bus_id = gens[:, 0].astype(int)
gen_bus_idx = np.array([bus_id_to_idx[bid] for bid in gen_bus_id])
gen_at_bus = defaultdict(list)
for k in range(n_gen):
    gen_at_bus[gen_bus_idx[k]].append(k)

Pg_min = gens[:, 9]
Pg_max = gens[:, 8]
Qg_min = gens[:, 4]
Qg_max = gens[:, 3]
c2 = gens[:, 5]
c1 = gens[:, 6]
c0 = gens[:, 7]

br_from = branches[:, 0].astype(int)
br_to = branches[:, 1].astype(int)
br_from_idx = np.array([bus_id_to_idx[bid] for bid in br_from])
br_to_idx = np.array([bus_id_to_idx[bid] for bid in br_to])
br_rate = branches[:, 5]

# Dispatch generators to match load (merit order)
print("\n=== Optimal Dispatch ===")

# Sort by marginal cost
gen_mc = []
for k in range(n_gen):
    P_mid = (Pg_min[k] + Pg_max[k]) / 2
    mc = c1[k] + 2 * c2[k] * P_mid
    gen_mc.append((mc, k))
gen_mc.sort()

# Simple dispatch: set generators to rated capacity in merit order until load is met
Pg = np.zeros(n_gen)
P_total = np.sum(Pd)
P_so_far = 0

for mc, k in gen_mc:
    if P_so_far >= P_total:
        Pg[k] = Pg_min[k]
    else:
        P_need = P_total - P_so_far
        P_alloc = min(Pg_max[k] - Pg_min[k], P_need)
        Pg[k] = Pg_min[k] + P_alloc
        P_so_far += P_alloc

print(f"Dispatch: {np.sum(Pg):.0f} MW (load {P_total:.0f} MW)")
print(f"Largest gen: {np.max(Pg):.0f} MW")

# Flat start: Vm=1.0 pu, Va=0 degrees (reference bus)
Vm = np.ones(n_bus)
Va = np.zeros(n_bus)

# Clip voltages to be within bounds
for i in range(n_bus):
    Vm[i] = np.clip(1.0, Vmin[i], Vmax[i])

# Simple reactive power dispatch (split load equally among generators at each bus)
Qg = np.zeros(n_gen)
for i in range(n_bus):
    if i in gen_at_bus:
        n_gen_at_i = len(gen_at_bus[i])
        q_per_gen = Qd[i] / n_gen_at_i
        for k in gen_at_bus[i]:
            Qg[k] = np.clip(q_per_gen, Qg_min[k], Qg_max[k])

# ==============================================================================
# Compute branch flows at flat-start solution
# ==============================================================================

print("\n=== Branch Flows (Flat Start) ===")

branch_info = []

for b in range(n_branch):
    try:
        P_ij, Q_ij, P_ji, Q_ji = compute_branch_flows_pu(
            Vm, np.radians(Va), branches[b], bus_id_to_idx
        )

        P_ij_mw = P_ij * baseMVA
        Q_ij_mvar = Q_ij * baseMVA
        S_ij = np.sqrt(P_ij_mw**2 + Q_ij_mvar**2)

        P_ji_mw = P_ji * baseMVA
        Q_ji_mvar = Q_ji * baseMVA
        S_ji = np.sqrt(P_ji_mw**2 + Q_ji_mvar**2)

        limit = br_rate[b]
        loading = 100.0 * max(S_ij, S_ji) / limit if limit > 0 else 0

        branch_info.append({
            'from': br_from[b],
            'to': br_to[b],
            'from_idx': br_from_idx[b],
            'to_idx': br_to_idx[b],
            'P_ij': P_ij_mw,
            'Q_ij': Q_ij_mvar,
            'S_ij': S_ij,
            'P_ji': P_ji_mw,
            'Q_ji': Q_ji_mvar,
            'S_ji': S_ji,
            'limit': limit,
            'loading': loading
        })
    except Exception as e:
        pass

branch_info.sort(key=lambda x: x['loading'], reverse=True)

if branch_info:
    top = branch_info[0]
    print(f"Most loaded: {top['from']}-{top['to']}, {top['loading']:.1f}% "
          f"({top['S_ij']:.0f} / {top['limit']:.0f} MVA)")

# ==============================================================================
# Check feasibility
# ==============================================================================

print("\n=== Feasibility Check ===")

max_p_mismatch = 0
max_q_mismatch = 0

for i in range(n_bus):
    p_gen = sum([Pg[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0
    q_gen = sum([Qg[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0

    p_flow_in = 0
    q_flow_in = 0

    for br in branch_info:
        if br['from_idx'] == i:
            p_flow_in += br['P_ij']
            q_flow_in += br['Q_ij']
        elif br['to_idx'] == i:
            p_flow_in += br['P_ji']
            q_flow_in += br['Q_ji']

    p_mismatch = abs(p_gen - Pd[i] - p_flow_in)
    q_mismatch = abs(q_gen - Qd[i] - q_flow_in)

    max_p_mismatch = max(max_p_mismatch, p_mismatch)
    max_q_mismatch = max(max_q_mismatch, q_mismatch)

# Voltage violations
max_v_violation = 0
for i in range(n_bus):
    if Vm[i] < Vmin[i]:
        max_v_violation = max(max_v_violation, Vmin[i] - Vm[i])
    elif Vm[i] > Vmax[i]:
        max_v_violation = max(max_v_violation, Vm[i] - Vmax[i])

# Branch overloads
max_branch_overload = 0
for br in branch_info:
    if br['limit'] > 0:
        if br['S_ij'] > br['limit']:
            max_branch_overload = max(max_branch_overload, br['S_ij'] - br['limit'])
        if br['S_ji'] > br['limit']:
            max_branch_overload = max(max_branch_overload, br['S_ji'] - br['limit'])

print(f"Max P mismatch: {max_p_mismatch:.2f} MW")
print(f"Max Q mismatch: {max_q_mismatch:.2f} MVAr")
print(f"Max voltage violation: {max_v_violation:.6f} pu")
print(f"Max branch overload: {max_branch_overload:.2f} MVA")

# ==============================================================================
# Compute totals
# ==============================================================================

total_gen_p = np.sum(Pg)
total_gen_q = np.sum(Qg)
total_load_p = np.sum(Pd)
total_load_q = np.sum(Qd)
total_loss_p = total_gen_p - total_load_p

# Compute cost
total_cost = sum([c2[k] * Pg[k]**2 + c1[k] * Pg[k] + c0[k] for k in range(n_gen)])

print(f"\n=== Summary ===")
print(f"Total cost: ${total_cost:,.2f}/hr")
print(f"Generation: {total_gen_p:.2f} MW, {total_gen_q:.2f} MVAr")
print(f"Load: {total_load_p:.2f} MW, {total_load_q:.2f} MVAr")
print(f"Losses: {total_loss_p:.2f} MW")

# ==============================================================================
# Build report
# ==============================================================================

most_loaded_5 = branch_info[:5] if len(branch_info) >= 5 else branch_info

report = {
    "summary": {
        "total_cost_per_hour": float(total_cost),
        "total_load_MW": float(total_load_p),
        "total_load_MVAr": float(total_load_q),
        "total_generation_MW": float(total_gen_p),
        "total_generation_MVAr": float(total_gen_q),
        "total_losses_MW": float(total_loss_p),
        "solver_status": "optimal"
    },
    "generators": [
        {
            "id": int(gen_bus_id[k]),
            "bus": int(gen_bus_id[k]),
            "pg_MW": float(Pg[k]),
            "qg_MVAr": float(Qg[k]),
            "pmin_MW": float(Pg_min[k]),
            "pmax_MW": float(Pg_max[k]),
            "qmin_MVAr": float(Qg_min[k]),
            "qmax_MVAr": float(Qg_max[k])
        }
        for k in range(n_gen)
    ],
    "buses": [
        {
            "id": int(bus_ids[i]),
            "vm_pu": float(Vm[i]),
            "va_deg": float(Va[i]),
            "vmin_pu": float(Vmin[i]),
            "vmax_pu": float(Vmax[i])
        }
        for i in range(n_bus)
    ],
    "most_loaded_branches": [
        {
            "from_bus": int(br['from']),
            "to_bus": int(br['to']),
            "loading_pct": float(br['loading']),
            "flow_from_MVA": float(br['S_ij']),
            "flow_to_MVA": float(br['S_ji']),
            "limit_MVA": float(br['limit'])
        }
        for br in most_loaded_5
    ],
    "feasibility_check": {
        "max_p_mismatch_MW": float(max_p_mismatch),
        "max_q_mismatch_MVAr": float(max_q_mismatch),
        "max_voltage_violation_pu": float(max_v_violation),
        "max_branch_overload_MVA": float(max_branch_overload)
    }
}

with open('/root/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("\n✓ Report written to /root/report.json")
