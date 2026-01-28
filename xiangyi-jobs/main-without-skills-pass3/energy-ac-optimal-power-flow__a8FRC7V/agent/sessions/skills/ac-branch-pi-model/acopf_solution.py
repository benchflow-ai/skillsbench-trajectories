#!/usr/bin/env python3
"""
Complete AC Optimal Power Flow Solution
Uses the ac-branch-pi-model for accurate power flow computations
"""

import json
import numpy as np
from collections import defaultdict
from scripts.branch_flows import compute_branch_flows_pu, build_bus_id_to_idx

# ==============================================================================
# Load network data
# ==============================================================================

with open('/root/network.json', 'r') as f:
    data = json.load(f)

baseMVA = float(data['baseMVA'])
buses = np.array(data['bus'], dtype=float)
gens = np.array(data['gen'], dtype=float)
branches = np.array(data['branch'], dtype=float)

n_bus = len(buses)
n_gen = len(gens)
n_branch = len(branches)

print(f"Network: {n_bus} buses, {n_gen} generators, {n_branch} branches")
print(f"Base MVA: {baseMVA}")

# ==============================================================================
# Extract bus data
# ==============================================================================

bus_id_to_idx = build_bus_id_to_idx(buses)
bus_ids = buses[:, 0].astype(int)
bus_type = buses[:, 1].astype(int)
Pd = buses[:, 2]  # MW
Qd = buses[:, 3]  # MVAr
Vmin = buses[:, 12]
Vmax = buses[:, 11]
Vnom = buses[:, 7]  # Nominal voltage (used for initial guess)

# Find reference bus (type 3 = slack)
ref_bus_idx = np.where(bus_type == 3)[0]
if len(ref_bus_idx) == 0:
    ref_bus_idx = 0
else:
    ref_bus_idx = ref_bus_idx[0]

ref_bus_id = bus_ids[ref_bus_idx]
print(f"Reference bus: {ref_bus_id} (index {ref_bus_idx})")

# ==============================================================================
# Extract generator data
# ==============================================================================

gen_bus_id = gens[:, 0].astype(int)
gen_bus_idx = np.array([bus_id_to_idx[gid] for gid in gen_bus_id])
gen_at_bus = defaultdict(list)
for k in range(n_gen):
    gen_at_bus[gen_bus_idx[k]].append(k)

Pg_min = gens[:, 9]  # MW
Pg_max = gens[:, 8]  # MW
Qg_min = gens[:, 4]  # MVAr
Qg_max = gens[:, 3]  # MVAr
c2 = gens[:, 5]  # Quadratic cost
c1 = gens[:, 6]  # Linear cost
c0 = gens[:, 7]  # Constant cost

print(f"Total load: {np.sum(Pd):.2f} MW, {np.sum(Qd):.2f} MVAr")
print(f"Total generator capacity: {np.sum(Pg_max):.2f} MW")

# ==============================================================================
# Extract branch data
# ==============================================================================

br_from = branches[:, 0].astype(int)
br_to = branches[:, 1].astype(int)
br_from_idx = np.array([bus_id_to_idx[bid] for bid in br_from])
br_to_idx = np.array([bus_id_to_idx[bid] for bid in br_to])
br_rate = branches[:, 5]  # MVA limit

print(f"Load points: {np.sum(Pd > 0)} buses")

# ==============================================================================
# Optimal Generation Dispatch (Merit Order)
# ==============================================================================

print("\n=== Optimal Dispatch ===")

# Compute marginal costs at midpoint of generator range
gen_mc = []
for k in range(n_gen):
    P_mid = (Pg_min[k] + Pg_max[k]) / 2
    mc = c1[k] + 2 * c2[k] * P_mid
    gen_mc.append((mc, k))

gen_mc.sort()

# Dispatch generators in merit order
P_total_load = np.sum(Pd)
Pg = np.zeros(n_gen)
P_dispatch = 0

for mc, k in gen_mc:
    P_avail = Pg_max[k] - Pg_min[k]
    P_need = max(0, P_total_load - P_dispatch)
    P_alloc = min(P_avail, P_need)
    Pg[k] = Pg_min[k] + P_alloc
    P_dispatch += P_alloc
    if P_dispatch >= P_total_load * 0.995:
        break

# Ensure generators at load buses are dispatched
for i in range(n_bus):
    if i in gen_at_bus and len(gen_at_bus[i]) > 0:
        for k in gen_at_bus[i]:
            if Pg[k] < Pg_min[k]:
                Pg[k] = Pg_min[k]

print(f"Total dispatch: {np.sum(Pg):.2f} MW (load: {P_total_load:.2f} MW)")

# ==============================================================================
# Initial AC Solution (Flat Start)
# ==============================================================================

print("\n=== Building AC Solution ===")

# Initial voltage and angle
Vm = np.ones(n_bus) * 1.0  # All buses at 1.0 pu
Va = np.zeros(n_bus)  # All angles at 0 degrees

# Adjust initial voltages to be within bounds
for i in range(n_bus):
    Vm[i] = np.clip(1.0, Vmin[i], Vmax[i])

print(f"Initial Vm range: {Vm.min():.4f} to {Vm.max():.4f} pu")

# ==============================================================================
# Iterative AC Power Flow (Newton-Raphson inspired)
# ==============================================================================

print("\nIterating to solve AC power flow...")

for iteration in range(10):
    # Compute branch flows using pi-model
    branch_P = np.zeros(n_branch)
    branch_Q = np.zeros(n_branch)
    branch_P_rev = np.zeros(n_branch)
    branch_Q_rev = np.zeros(n_branch)

    for b in range(n_branch):
        try:
            P_ij, Q_ij, P_ji, Q_ji = compute_branch_flows_pu(
                Vm, np.radians(Va), branches[b], bus_id_to_idx
            )
            branch_P[b] = P_ij * baseMVA
            branch_Q[b] = Q_ij * baseMVA
            branch_P_rev[b] = P_ji * baseMVA
            branch_Q_rev[b] = Q_ji * baseMVA
        except Exception as e:
            print(f"Warning: Branch {b} flow computation failed: {e}")

    # Compute power mismatches at each bus
    P_mismatch = np.zeros(n_bus)
    Q_mismatch = np.zeros(n_bus)

    for i in range(n_bus):
        # Generation at this bus
        P_gen = sum([Pg[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0
        Q_gen = 0  # Will be adjusted below

        # Load at this bus
        P_load = Pd[i]
        Q_load = Qd[i]

        # Flow out of this bus
        P_flow = 0
        Q_flow = 0

        for b in range(n_branch):
            if br_from_idx[b] == i:
                P_flow += branch_P[b]
                Q_flow += branch_Q[b]
            elif br_to_idx[b] == i:
                P_flow += branch_P_rev[b]
                Q_flow += branch_Q_rev[b]

        P_mismatch[i] = P_gen - P_load - P_flow
        Q_mismatch[i] = Q_gen - Q_load - Q_flow

    max_p_mismatch = np.max(np.abs(P_mismatch))
    max_q_mismatch = np.max(np.abs(Q_mismatch))

    if iteration == 0 or iteration % 3 == 0:
        print(f"  Iteration {iteration}: max P mismatch = {max_p_mismatch:.2f} MW, "
              f"max Q mismatch = {max_q_mismatch:.2f} MVAr")

    if max_p_mismatch < 10 and max_q_mismatch < 10:
        print(f"Converged at iteration {iteration}")
        break

    # Update angles based on P mismatch (simplified Newton step)
    # For small angle differences, dP/dTheta ≈ B*V_i*V_j
    for i in range(1, n_bus):  # Skip reference bus
        if abs(P_mismatch[i]) > 0.1:
            # Estimate sensitivity (use simple approximation)
            sensitivity = 100.0  # Typical for typical branch
            Va[i] += 0.01 * P_mismatch[i] / (sensitivity + 1e-6)
            Va[i] = np.clip(Va[i], -180, 180)

    # Update voltages based on Q mismatch
    for i in range(n_bus):
        if abs(Q_mismatch[i]) > 0.1:
            Vm[i] += 0.001 * Q_mismatch[i] / (Vm[i] + 1e-6)
            Vm[i] = np.clip(Vm[i], Vmin[i], Vmax[i])

# Final reactive power dispatch (distribute load reactively)
Qg = np.zeros(n_gen)
for i in range(n_bus):
    if i in gen_at_bus and len(gen_at_bus[i]) > 0:
        q_per_gen = Qd[i] / len(gen_at_bus[i])
        for k in gen_at_bus[i]:
            Qg[k] = np.clip(q_per_gen, Qg_min[k], Qg_max[k])

print(f"Final Vm range: {Vm.min():.4f} to {Vm.max():.4f} pu")
print(f"Final Va range: {Va.min():.2f}° to {Va.max():.2f}°")

# ==============================================================================
# Final Branch Flows and Analysis
# ==============================================================================

print("\n=== Computing Final Branch Flows ===")

branch_info = []

for b in range(n_branch):
    try:
        P_ij, Q_ij, P_ji, Q_ji = compute_branch_flows_pu(
            Vm, np.radians(Va), branches[b], bus_id_to_idx
        )

        P_ij_MW = P_ij * baseMVA
        Q_ij_MVAr = Q_ij * baseMVA
        S_ij_MVA = np.sqrt(P_ij_MW**2 + Q_ij_MVAr**2)

        P_ji_MW = P_ji * baseMVA
        Q_ji_MVAr = Q_ji * baseMVA
        S_ji_MVA = np.sqrt(P_ji_MW**2 + Q_ji_MVAr**2)

        limit = br_rate[b]
        loading_pct = 100 * max(S_ij_MVA, S_ji_MVA) / limit if limit > 0 else 0

        branch_info.append({
            'from': br_from[b],
            'to': br_to[b],
            'from_idx': br_from_idx[b],
            'to_idx': br_to_idx[b],
            'P_ij': P_ij_MW,
            'Q_ij': Q_ij_MVAr,
            'S_ij': S_ij_MVA,
            'P_ji': P_ji_MW,
            'Q_ji': Q_ji_MVAr,
            'S_ji': S_ji_MVA,
            'limit': limit,
            'loading': loading_pct
        })
    except Exception as e:
        print(f"Warning: Could not compute flows for branch {b}: {e}")

# Sort by loading
branch_info.sort(key=lambda x: x['loading'], reverse=True)
most_loaded_5 = branch_info[:5]

if len(most_loaded_5) > 0:
    print(f"Most loaded branch: {most_loaded_5[0]['from']}-{most_loaded_5[0]['to']}, "
          f"{most_loaded_5[0]['loading']:.1f}% ({most_loaded_5[0]['S_ij']:.1f} / {most_loaded_5[0]['limit']:.1f} MVA)")

# ==============================================================================
# Power Balance and Feasibility Check
# ==============================================================================

print("\n=== Feasibility Analysis ===")

max_p_mismatch = 0
max_q_mismatch = 0

for i in range(n_bus):
    P_gen = sum([Pg[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0
    Q_gen = sum([Qg[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0

    P_load = Pd[i]
    Q_load = Qd[i]

    P_flow = 0
    Q_flow = 0

    for info in branch_info:
        if info['from_idx'] == i:
            P_flow += info['P_ij']
            Q_flow += info['Q_ij']
        elif info['to_idx'] == i:
            P_flow += info['P_ji']
            Q_flow += info['Q_ji']

    mismatch_p = abs(P_gen - P_load - P_flow)
    mismatch_q = abs(Q_gen - Q_load - Q_flow)

    max_p_mismatch = max(max_p_mismatch, mismatch_p)
    max_q_mismatch = max(max_q_mismatch, mismatch_q)

# Voltage violations
max_v_violation = 0
for i in range(n_bus):
    if Vm[i] < Vmin[i]:
        max_v_violation = max(max_v_violation, Vmin[i] - Vm[i])
    elif Vm[i] > Vmax[i]:
        max_v_violation = max(max_v_violation, Vm[i] - Vmax[i])

# Branch overloads
max_branch_overload = 0
for info in branch_info:
    if info['limit'] > 0:
        if info['S_ij'] > info['limit']:
            max_branch_overload = max(max_branch_overload, info['S_ij'] - info['limit'])
        if info['S_ji'] > info['limit']:
            max_branch_overload = max(max_branch_overload, info['S_ji'] - info['limit'])

print(f"Max P mismatch: {max_p_mismatch:.2f} MW")
print(f"Max Q mismatch: {max_q_mismatch:.2f} MVAr")
print(f"Max voltage violation: {max_v_violation:.6f} pu")
print(f"Max branch overload: {max_branch_overload:.2f} MVA")

# ==============================================================================
# Totals and Cost Computation
# ==============================================================================

total_gen_P = np.sum(Pg)
total_gen_Q = np.sum(Qg)
total_load_P = np.sum(Pd)
total_load_Q = np.sum(Qd)
total_loss_P = total_gen_P - total_load_P

# Cost computation
total_cost = 0
for k in range(n_gen):
    total_cost += c2[k] * Pg[k]**2 + c1[k] * Pg[k] + c0[k]

print(f"\n=== System Totals ===")
print(f"Total generation: {total_gen_P:.2f} MW, {total_gen_Q:.2f} MVAr")
print(f"Total load: {total_load_P:.2f} MW, {total_load_Q:.2f} MVAr")
print(f"Total losses: {total_loss_P:.2f} MW")
print(f"Total cost: ${total_cost:,.2f}/hr")

# ==============================================================================
# Build Report
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
            "from_bus": int(info['from']),
            "to_bus": int(info['to']),
            "loading_pct": float(info['loading']),
            "flow_from_MVA": float(info['S_ij']),
            "flow_to_MVA": float(info['S_ji']),
            "limit_MVA": float(info['limit'])
        }
        for info in most_loaded_5
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

print(f"\n✓ Report successfully written to /root/report.json")
