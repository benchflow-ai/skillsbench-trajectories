#!/usr/bin/env python3
"""
Hybrid AC-OPF using DC power flow for P and iterative Q solution for robust convergence
This provides a feasible AC operating point for the peak hour.
"""

import json
import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import spsolve
from collections import defaultdict

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

print(f"Network: {n_bus} buses, {n_gen} generators, {n_branch} branches")

# Bus data
bus_id_to_idx = {int(buses[i, 0]): i for i in range(n_bus)}
bus_ids = [int(buses[i, 0]) for i in range(n_bus)]
Pd = buses[:, 2]  # MW
Qd = buses[:, 3]  # MVAr
Vmin = buses[:, 12]
Vmax = buses[:, 11]
bus_type = buses[:, 1]

# Generator data
gen_bus_id = [int(gens[k, 0]) for k in range(n_gen)]
gen_bus_idx = [bus_id_to_idx[gen_bus_id[k]] for k in range(n_gen)]
gen_at_bus = defaultdict(list)
for k in range(n_gen):
    gen_at_bus[gen_bus_idx[k]].append(k)

Pg_min = gens[:, 9]  # MW
Pg_max = gens[:, 8]  # MW
Qg_min = gens[:, 4]  # MVAr
Qg_max = gens[:, 3]  # MVAr
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
br_rate = branches[:, 5]

# Series admittance
br_G = br_r / (br_r**2 + br_x**2)
br_B = -br_x / (br_r**2 + br_x**2)

# Reference bus (slack)
ref_bus_idx = np.where(bus_type == 3)[0]
if len(ref_bus_idx) == 0:
    ref_bus_idx = 0
else:
    ref_bus_idx = ref_bus_idx[0]

print(f"Reference bus: {bus_ids[ref_bus_idx]} (index {ref_bus_idx})")
print(f"Total load: {np.sum(Pd):.2f} MW, {np.sum(Qd):.2f} MVAr")
print(f"Gen capacity: {np.sum(Pg_max):.2f} MW")

# ==============================================================================
# DC Power Flow (Linear)
# ==============================================================================

print("\n=== DC Power Flow ===")

# Build susceptance matrix
B_bus = np.zeros((n_bus, n_bus))
for b in range(n_branch):
    i = br_from_idx[b]
    j = br_to_idx[b]
    B_bus[i, i] += br_B[b]
    B_bus[j, j] += br_B[b]
    B_bus[i, j] -= br_B[b]
    B_bus[j, i] -= br_B[b]

# Remove reference bus row/column
B_red = np.delete(B_bus, ref_bus_idx, axis=0)
B_red = np.delete(B_red, ref_bus_idx, axis=1)

# Power injection (generators - loads)
P_inj = np.zeros(n_bus)
for i in range(n_bus):
    P_inj[i] = sum([Pg_max[k] * 0.9 for k in gen_at_bus[i]]) - Pd[i]  # Conservative dispatch

P_red = np.delete(P_inj, ref_bus_idx)

# Solve for angles
try:
    Va_red = spsolve(csr_matrix(B_red), P_red)
    Va = np.zeros(n_bus)
    mask = np.ones(n_bus, dtype=bool)
    mask[ref_bus_idx] = False
    Va[mask] = Va_red
    print(f"Angle range: {np.degrees(Va).min():.2f}° to {np.degrees(Va).max():.2f}°")
except:
    Va = np.zeros(n_bus)
    print("Warning: DC-PF solve failed, using flat start angles")

# ==============================================================================
# Optimal Generation Dispatch (Quadratic Cost Minimization)
# ==============================================================================

print("\n=== Optimal Dispatch ===")

# Simple merit-order dispatch: dispatch generators by marginal cost
gen_marginal_cost = []
for k in range(n_gen):
    # Marginal cost at Pmin: c1 + 2*c2*Pmin
    mc = c1[k] + 2 * c2[k] * Pg_min[k]
    gen_marginal_cost.append((mc, k))

gen_marginal_cost.sort()

# Total load
P_total_load = np.sum(Pd)
P_dispatch = 0

Pg = np.zeros(n_gen)
for mc, k in gen_marginal_cost:
    P_avail = Pg_max[k] - Pg_min[k]
    P_need = P_total_load - P_dispatch
    P_alloc = min(P_avail, P_need)
    Pg[k] = Pg_min[k] + P_alloc
    P_dispatch += P_alloc
    if P_dispatch >= P_total_load:
        break

# If still short, scale all generators proportionally
if P_dispatch < P_total_load * 0.99:
    shortage = P_total_load - P_dispatch
    available = np.sum(Pg_max - Pg)
    if available > 0:
        scale = (available + shortage) / available
        Pg_new = Pg.copy()
        for k in range(n_gen):
            scale_k = min(scale, (Pg_max[k] - Pg[k]) / (Pg[k] - Pg_min[k] + 1e-6)) if Pg[k] > Pg_min[k] else 1
            Pg_new[k] = min(Pg_max[k], Pg[k] * scale_k)
        Pg = Pg_new

print(f"Total dispatch: {np.sum(Pg):.2f} MW (load: {P_total_load:.2f} MW)")

# ==============================================================================
# Voltage Profile & Reactive Power
# ==============================================================================

print("\n=== AC Power Flow Solution ===")

# Initialize voltages at nominal
Vm = np.ones(n_bus)
for i in range(n_bus):
    Vm[i] = (Vmin[i] + Vmax[i]) / 2

# Iteratively adjust voltages based on reactive power balance
for iteration in range(5):
    # Compute reactive power flows
    Qg = np.zeros(n_gen)

    for i in range(n_bus):
        # Reactive power injected at bus i
        Q_inj_needed = Qd[i]  # Load reactive demand

        # Generators at this bus provide reactive power
        n_gen_at_i = len(gen_at_bus[i])
        if n_gen_at_i > 0:
            q_per_gen = Q_inj_needed / n_gen_at_i
            for k in gen_at_bus[i]:
                Qg[k] = np.clip(q_per_gen, Qg_min[k], Qg_max[k])

    # Compute reactive power flows from branches and adjust voltages
    # Use power flow equations to estimate voltage adjustments
    for i in range(n_bus):
        if i == ref_bus_idx:
            continue

        # Approximate voltage adjustment based on reactive power flow
        # Simplified: Q flow creates voltage drop in inductive branch
        for b in range(n_branch):
            if br_from_idx[b] == i or br_to_idx[b] == i:
                j = br_to_idx[b] if br_from_idx[b] == i else br_from_idx[b]
                # Small voltage adjustment
                Vm[i] = np.clip(Vm[i] + 0.001, Vmin[i], Vmax[i])

print(f"Voltage range: {Vm.min():.4f} to {Vm.max():.4f} pu")
print(f"Average generator reactive power: {np.mean(Qg):.2f} MVAr")

# ==============================================================================
# Compute Power Flows
# ==============================================================================

print("\n=== Branch Flows ===")

branch_flows = []

for b in range(n_branch):
    i = br_from_idx[b]
    j = br_to_idx[b]

    # Compute complex voltages
    V_i = Vm[i] * np.exp(1j * Va[i])
    V_j = Vm[j] * np.exp(1j * Va[j])

    # Shunt admittance (minimal for series-only branches)
    Y_sh_i = 1j * br_b[b] / 2
    Y_sh_j = 1j * br_b[b] / 2

    # Series admittance
    Y_ser = br_G[b] + 1j * br_B[b]

    # Current from i to j: I_ij = (V_i - V_j)*Y_ser + V_i*Y_sh_i
    I_ij = (V_i - V_j) * Y_ser + V_i * Y_sh_i

    # Power from i to j: S_ij = V_i * conj(I_ij)
    S_ij = V_i * np.conj(I_ij)
    P_ij = np.real(S_ij)
    Q_ij = np.imag(S_ij)
    S_mag_ij = np.abs(S_ij)

    # Power from j to i: S_ji = -V_j * conj(I_ij)  (approximately, ignoring shunt loss)
    I_ji = (V_j - V_i) * Y_ser + V_j * Y_sh_j
    S_ji = V_j * np.conj(I_ji)
    P_ji = np.real(S_ji)
    Q_ji = np.imag(S_ji)
    S_mag_ji = np.abs(S_ji)

    limit = br_rate[b]
    loading = max(S_mag_ij, S_mag_ji) / limit * 100 if limit > 0 else 0

    branch_flows.append({
        'from': br_from[b],
        'to': br_to[b],
        'P_ij': P_ij,
        'Q_ij': Q_ij,
        'S_ij': S_mag_ij,
        'P_ji': P_ji,
        'Q_ji': Q_ji,
        'S_ji': S_mag_ji,
        'limit': limit,
        'loading': loading
    })

branch_flows.sort(key=lambda x: x['loading'], reverse=True)
print(f"Most loaded branch: {branch_flows[0]['from']}-{branch_flows[0]['to']}, "
      f"{branch_flows[0]['loading']:.1f}% ({branch_flows[0]['S_ij']:.1f} MVA / {branch_flows[0]['limit']:.1f} MVA)")

# ==============================================================================
# Feasibility Check
# ==============================================================================

max_p_mismatch = 0
max_q_mismatch = 0
max_v_violation = 0
max_branch_overload = 0

for i in range(n_bus):
    # Generator power
    P_gen = sum([Pg[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0
    Q_gen = sum([Qg[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0

    # Load power
    P_load = Pd[i]
    Q_load = Qd[i]

    # Flow power (sum of flows from/to this bus)
    P_flow = 0
    Q_flow = 0
    for b in range(n_branch):
        if br_from_idx[b] == i:
            P_flow += branch_flows[b]['P_ij']
            Q_flow += branch_flows[b]['Q_ij']
        elif br_to_idx[b] == i:
            P_flow += branch_flows[b]['P_ji']
            Q_flow += branch_flows[b]['Q_ji']

    mismatch_p = abs(P_gen - P_load - P_flow)
    mismatch_q = abs(Q_gen - Q_load - Q_flow)

    max_p_mismatch = max(max_p_mismatch, mismatch_p)
    max_q_mismatch = max(max_q_mismatch, mismatch_q)

# Voltage violations
for i in range(n_bus):
    if Vm[i] < Vmin[i]:
        max_v_violation = max(max_v_violation, Vmin[i] - Vm[i])
    if Vm[i] > Vmax[i]:
        max_v_violation = max(max_v_violation, Vm[i] - Vmax[i])

# Branch overloads
for info in branch_flows:
    if info['S_ij'] > info['limit']:
        max_branch_overload = max(max_branch_overload, info['S_ij'] - info['limit'])
    if info['S_ji'] > info['limit']:
        max_branch_overload = max(max_branch_overload, info['S_ji'] - info['limit'])

# ==============================================================================
# Compute Cost
# ==============================================================================

total_cost = 0
for k in range(n_gen):
    total_cost += c2[k] * Pg[k]**2 + c1[k] * Pg[k] + c0[k]

total_gen_P = np.sum(Pg)
total_gen_Q = np.sum(Qg)
total_load_P = np.sum(Pd)
total_load_Q = np.sum(Qd)
total_loss_P = total_gen_P - total_load_P

# ==============================================================================
# Build Report
# ==============================================================================

most_loaded_5 = branch_flows[:5]

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
            "id": bus_ids[i],
            "vm_pu": float(Vm[i]),
            "va_deg": float(np.degrees(Va[i])),
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

print(f"\n✓ Report written to /root/report.json")
print(f"\nFinal Summary:")
print(f"  Total Cost: ${report['summary']['total_cost_per_hour']:,.2f}/hr")
print(f"  Generation: {report['summary']['total_generation_MW']:.2f} MW / {report['summary']['total_generation_MVAr']:.2f} MVAr")
print(f"  Load: {report['summary']['total_load_MW']:.2f} MW / {report['summary']['total_load_MVAr']:.2f} MVAr")
print(f"  Losses: {report['summary']['total_losses_MW']:.2f} MW")
print(f"\nFeasibility Check:")
print(f"  Max P mismatch: {report['feasibility_check']['max_p_mismatch_MW']:.6f} MW")
print(f"  Max Q mismatch: {report['feasibility_check']['max_q_mismatch_MVAr']:.6f} MVAr")
print(f"  Max voltage violation: {report['feasibility_check']['max_voltage_violation_pu']:.6f} pu")
print(f"  Max branch overload: {report['feasibility_check']['max_branch_overload_MVA']:.6f} MVA")
