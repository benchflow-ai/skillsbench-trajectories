"""
AC branch pi-model power flow computations matching MATPOWER conventions.
"""
import numpy as np


def build_bus_id_to_idx(buses):
    """Build mapping from bus ID to array index."""
    bus_ids = buses[:, 0].astype(int)
    return {bus_id: idx for idx, bus_id in enumerate(bus_ids)}


def compute_branch_flows_pu(Vm, Va, branch, bus_id_to_idx):
    """
    Compute branch power flows in per-unit using the pi-model.

    Args:
        Vm: array of voltage magnitudes (pu)
        Va: array of voltage angles (radians)
        branch: single branch row [F_BUS, T_BUS, BR_R, BR_X, BR_B, RATE_A, ..., TAP, SHIFT, ...]
        bus_id_to_idx: dict mapping bus IDs to indices

    Returns:
        P_ij, Q_ij, P_ji, Q_ji: real and reactive power flows (pu)
    """
    # Extract branch data
    f_bus_id = int(branch[0])
    t_bus_id = int(branch[1])
    r = float(branch[2])
    x = float(branch[3])
    b_c = float(branch[4])  # Total line charging susceptance
    tap = float(branch[8])
    shift_deg = float(branch[9])

    # Get bus indices
    i = bus_id_to_idx[f_bus_id]
    j = bus_id_to_idx[t_bus_id]

    # Voltage magnitudes and angles
    Vi = Vm[i]
    Vj = Vm[j]
    theta_i = Va[i]
    theta_j = Va[j]

    # Tap ratio (default to 1.0 if zero)
    if abs(tap) < 1e-12:
        tap = 1.0

    # Phase shift (convert to radians)
    shift_rad = shift_deg * np.pi / 180.0

    # Series admittance y = g + jb
    if abs(r) < 1e-12 and abs(x) < 1e-12:
        g = 0.0
        b = 0.0
    else:
        denom = r**2 + x**2
        g = r / denom
        b = -x / denom

    # Inverse tap ratio
    inv_t = 1.0 / tap
    inv_t2 = inv_t ** 2

    # Angle differences
    delta_ij = theta_i - theta_j - shift_rad
    delta_ji = theta_j - theta_i + shift_rad

    # Power flow from i to j
    P_ij = g * Vi**2 * inv_t2 - Vi * Vj * inv_t * (g * np.cos(delta_ij) + b * np.sin(delta_ij))
    Q_ij = -(b + b_c/2) * Vi**2 * inv_t2 - Vi * Vj * inv_t * (g * np.sin(delta_ij) - b * np.cos(delta_ij))

    # Power flow from j to i
    P_ji = g * Vj**2 - Vi * Vj * inv_t * (g * np.cos(delta_ji) + b * np.sin(delta_ji))
    Q_ji = -(b + b_c/2) * Vj**2 - Vi * Vj * inv_t * (g * np.sin(delta_ji) - b * np.cos(delta_ji))

    return P_ij, Q_ij, P_ji, Q_ji


def compute_all_branch_flows_pu(Vm, Va, branches, bus_id_to_idx):
    """
    Compute power flows for all branches.

    Returns:
        P_ij, Q_ij, P_ji, Q_ji: arrays of power flows (pu)
    """
    n_branch = len(branches)
    P_ij = np.zeros(n_branch)
    Q_ij = np.zeros(n_branch)
    P_ji = np.zeros(n_branch)
    Q_ji = np.zeros(n_branch)

    for b in range(n_branch):
        P_ij[b], Q_ij[b], P_ji[b], Q_ji[b] = compute_branch_flows_pu(
            Vm, Va, branches[b], bus_id_to_idx
        )

    return P_ij, Q_ij, P_ji, Q_ji


def compute_bus_injections_pu(Vm, Va, branches, bus_id_to_idx, n_bus):
    """
    Compute total branch power flowing out of each bus.

    Returns:
        P_out, Q_out: arrays of net power flowing out via branches (pu)
    """
    P_out = np.zeros(n_bus)
    Q_out = np.zeros(n_bus)

    for branch in branches:
        f_bus_id = int(branch[0])
        t_bus_id = int(branch[1])
        br_status = int(branch[10])

        if br_status == 0:
            continue

        i = bus_id_to_idx[f_bus_id]
        j = bus_id_to_idx[t_bus_id]

        P_ij, Q_ij, P_ji, Q_ji = compute_branch_flows_pu(Vm, Va, branch, bus_id_to_idx)

        # Add flows leaving each bus
        P_out[i] += P_ij
        Q_out[i] += Q_ij
        P_out[j] += P_ji
        Q_out[j] += Q_ji

    return P_out, Q_out
