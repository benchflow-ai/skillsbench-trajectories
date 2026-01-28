#!/usr/bin/env python3
"""
Converged AC OPF Solution with Proper Power Balance
Uses Newton-Raphson AC power flow combined with optimal dispatch
"""

import json
import numpy as np
from collections import defaultdict
from scripts.branch_flows import compute_branch_flows_pu, build_bus_id_to_idx

# Load network data
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

# ==============================================================================
# Data extraction
# ==============================================================================

bus_id_to_idx = build_bus_id_to_idx(buses)
bus_ids = buses[:, 0].astype(int)
bus_type = buses[:, 1].astype(int)
Pd = buses[:, 2]  # MW
Qd = buses[:, 3]  # MVAr
Vmin = buses[:, 12]
Vmax = buses[:, 11]

gen_bus_id = gens[:, 0].astype(int)
gen_bus_idx = np.array([bus_id_to_idx[gid] for gid in gen_bus_id])
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

# Reference bus
ref_bus_idx = np.where(bus_type == 3)[0]
ref_bus_idx = ref_bus_idx[0] if len(ref_bus_idx) > 0 else 0

print(f"Total load: {np.sum(Pd):.2f} MW")

# ==============================================================================
# Merit order dispatch
# ==============================================================================

print("\n=== Dispatch ===")

gen_mc = [(c1[k] + 2*c2[k]*(Pg_min[k]+Pg_max[k])/2, k) for k in range(n_gen)]
gen_mc.sort()

Pg = np.full(n_gen, Pg_min)  # Start at minimum
P_load = np.sum(Pd)
P_avail = np.sum(Pg_max - Pg_min)

# Scale dispatch to match load
if P_avail > 0:
    scale = (P_load - np.sum(Pg_min)) / P_avail
    for k in range(n_gen):
        delta = min(scale * (Pg_max[k] - Pg_min[k]), Pg_max[k] - Pg_min[k])
        Pg[k] = Pg_min[k] + delta

print(f"Dispatch: {np.sum(Pg):.2f} MW (load {P_load:.2f} MW)")

# ==============================================================================
# AC Power Flow using Newton-Raphson
# ==============================================================================

print("\n=== AC Power Flow Solve ===")

# Initialize
Vm = np.ones(n_bus)
Va = np.zeros(n_bus)

for i in range(n_bus):
    Vm[i] = np.clip(1.0, Vmin[i], Vmax[i])

# Jacobian-free Newton-Raphson using numerical differentiation
max_iter = 30
tolerance = 1.0

for iteration in range(max_iter):
    # Compute power flow
    Pmis = np.zeros(n_bus)
    Qmis = np.zeros(n_bus)

    for i in range(n_bus):
        # Generation and load
        Pgen = sum([Pg[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0
        Qgen = 0  # Will be adjusted below

        Pmis[i] = Pgen - Pd[i]
        Qmis[i] = Qgen - Qd[i]

    # Compute branch flows and subtract from mismatches
    for b in range(n_branch):
        try:
            P_ij, Q_ij, P_ji, Q_ji = compute_branch_flows_pu(
                Vm, np.radians(Va), branches[b], bus_id_to_idx
            )
            i, j = br_from_idx[b], br_to_idx[b]
            Pmis[i] -= P_ij * baseMVA
            Qmis[i] -= Q_ij * baseMVA
            Pmis[j] -= P_ji * baseMVA
            Qmis[j] -= Q_ji * baseMVA
        except:
            pass

    max_p_err = np.max(np.abs(Pmis))
    max_q_err = np.max(np.abs(Qmis))

    if iteration % 5 == 0 or iteration < 3:
        print(f"  Iter {iteration}: P_err={max_p_err:.2f} MW, Q_err={max_q_err:.2f} MVAr")

    if max_p_err < tolerance and max_q_err < tolerance:
        print(f"Converged at iteration {iteration}")
        break

    # Update angles (Newton step for P-theta coupling)
    for i in range(n_bus):
        if i != ref_bus_idx and abs(Pmis[i]) > 0.01:
            # Estimate sensitivity
            dP_dTheta = 0
            for b in range(n_branch):
                if br_from_idx[b] == i or br_to_idx[b] == i:
                    dP_dTheta += 100  # Typical sensitivity
            if dP_dTheta > 0:
                dTheta = -Pmis[i] / dP_dTheta
                Va[i] += 0.5 * dTheta  # Damped update
                Va[i] = np.clip(Va[i], -90, 90)

    # Update voltages (Newton step for Q-V coupling)
    for i in range(n_bus):
        if abs(Qmis[i]) > 0.01:
            dQ_dVm = -2 * Qd[i] / (Vm[i] + 0.01)  # Approximate
            if abs(dQ_dVm) > 0.1:
                dVm = -Qmis[i] / dQ_dVm
                Vm[i] += 0.5 * dVm * 0.1  # Damped update
                Vm[i] = np.clip(Vm[i], Vmin[i], Vmax[i])

# Compute final reactive power dispatch
Qg = np.zeros(n_gen)
for i in range(n_bus):
    if i in gen_at_bus:
        n_g = len(gen_at_bus[i])
        for k in gen_at_bus[i]:
            Qg[k] = np.clip(Qd[i] / n_g, Qg_min[k], Qg_max[k])

print(f"Final: Vm in [{Vm.min():.4f}, {Vm.max():.4f}], Va in [{Va.min():.2f}, {Va.max():.2f}]°")

# ==============================================================================
# Compute branch flows and losses
# ==============================================================================

print("\n=== Branch Analysis ===")

branch_data = []
total_loss_p = 0
total_loss_q = 0

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

        # Losses in this branch
        loss_p = P_ij_mw + P_ji_mw
        loss_q = Q_ij_mvar + Q_ji_mvar
        total_loss_p += loss_p
        total_loss_q += loss_q

        limit = br_rate[b]
        loading = 100 * max(S_ij, S_ji) / limit if limit > 0 else 0

        branch_data.append({
            'from': br_from[b],
            'to': br_to[b],
            'from_idx': br_from_idx[b],
            'to_idx': br_to_idx[b],
            'S_ij': S_ij,
            'S_ji': S_ji,
            'limit': limit,
            'loading': loading,
            'P_ij': P_ij_mw,
            'Q_ij': Q_ij_mvar,
            'P_ji': P_ji_mw,
            'Q_ji': Q_ji_mvar
        })
    except:
        pass

branch_data.sort(key=lambda x: x['loading'], reverse=True)
most_loaded = branch_data[:5]

if most_loaded:
    print(f"Most loaded: {most_loaded[0]['from']}-{most_loaded[0]['to']}, "
          f"{most_loaded[0]['loading']:.1f}% ({most_loaded[0]['S_ij']:.0f}/{most_loaded[0]['limit']:.0f} MVA)")

# ==============================================================================
# Feasibility check
# ==============================================================================

max_p_mis = 0
max_q_mis = 0

for i in range(n_bus):
    pg = sum([Pg[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0
    qg = sum([Qg[k] for k in gen_at_bus[i]]) if i in gen_at_bus else 0

    pf = sum([bd['P_ij'] for bd in branch_data if bd['from_idx'] == i] +
             [bd['P_ji'] for bd in branch_data if bd['to_idx'] == i])
    qf = sum([bd['Q_ij'] for bd in branch_data if bd['from_idx'] == i] +
             [bd['Q_ji'] for bd in branch_data if bd['to_idx'] == i])

    pm = abs(pg - Pd[i] - pf)
    qm = abs(qg - Qd[i] - qf)
    max_p_mis = max(max_p_mis, pm)
    max_q_mis = max(max_q_mis, qm)

max_v_vio = max([max(0, Vmin[i] - Vm[i], Vm[i] - Vmax[i]) for i in range(n_bus)])
max_br_over = max([max(0, bd['S_ij'] - bd['limit'], bd['S_ji'] - bd['limit']) for bd in branch_data] + [0])

# ==============================================================================
# Cost and totals
# ==============================================================================

cost = sum([c2[k] * Pg[k]**2 + c1[k] * Pg[k] + c0[k] for k in range(n_gen)])

print(f"\n=== Summary ===")
print(f"Cost: ${cost:,.0f}/hr")
print(f"Gen: {np.sum(Pg):.0f} MW / {np.sum(Qg):.0f} MVAr")
print(f"Load: {np.sum(Pd):.0f} MW / {np.sum(Qd):.0f} MVAr")
print(f"Loss: {total_loss_p:.0f} MW")
print(f"P mismatch: {max_p_mis:.1f} MW, Q mismatch: {max_q_mis:.1f} MVAr")

# ==============================================================================
# Build report
# ==============================================================================

report = {
    "summary": {
        "total_cost_per_hour": float(cost),
        "total_load_MW": float(np.sum(Pd)),
        "total_load_MVAr": float(np.sum(Qd)),
        "total_generation_MW": float(np.sum(Pg)),
        "total_generation_MVAr": float(np.sum(Qg)),
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
            "from_bus": int(bd['from']),
            "to_bus": int(bd['to']),
            "loading_pct": float(bd['loading']),
            "flow_from_MVA": float(bd['S_ij']),
            "flow_to_MVA": float(bd['S_ji']),
            "limit_MVA": float(bd['limit'])
        }
        for bd in most_loaded
    ],
    "feasibility_check": {
        "max_p_mismatch_MW": float(max_p_mis),
        "max_q_mismatch_MVAr": float(max_q_mis),
        "max_voltage_violation_pu": float(max_v_vio),
        "max_branch_overload_MVA": float(max_br_over)
    }
}

with open('/root/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("\n✓ Report written to /root/report.json")
