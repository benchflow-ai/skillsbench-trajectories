"""
Open Dicke Model Simulation with Wigner Function Calculation

Simulates an open Dicke model (N two-level systems coupled to a cavity mode)
under 4 different loss scenarios and calculates the cavity field Wigner function.

The Hamiltonian is:
H = ω₀J_z + ω_c a†a + g(a† + a)(J₊ + J₋)

where J_z, J₊, J₋ are collective spin operators for N two-level systems.
"""

import numpy as np
import qutip as qt
import csv
from pathlib import Path
import sys

# Force unbuffered output
sys.stdout = open(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = open(sys.stderr.fileno(), 'w', buffering=1)

# System parameters
N = 4  # Number of two-level systems
omega_0 = 1.0  # Atomic transition frequency
omega_c = 1.0  # Cavity frequency
g = 2.0 / np.sqrt(N)  # Light-matter coupling strength
kappa = 1.0  # Cavity loss rate
n_max = 16  # Photon number cutoff

# Wigner function grid parameters
x_min, x_max = -6, 6
p_min, p_max = -6, 6
grid_points = 1000

print("=" * 70, flush=True)
print("Open Dicke Model Simulation", flush=True)
print("=" * 70, flush=True)
print(f"Parameters:", flush=True)
print(f"  N = {N} (two-level systems)", flush=True)
print(f"  ω₀ = {omega_0}, ω_c = {omega_c}", flush=True)
print(f"  g = {g:.4f}", flush=True)
print(f"  κ = {kappa} (cavity loss)", flush=True)
print(f"  n_max = {n_max} (photon cutoff)", flush=True)
print(f"  Wigner grid: [{x_min}, {x_max}] × [{p_min}, {p_max}], {grid_points}×{grid_points}", flush=True)
print("=" * 70, flush=True)

# Create cavity operators
a = qt.tensor(qt.destroy(n_max), qt.qeye([2]*N))  # Cavity annihilation
a_dag = a.dag()

# Create collective spin operators using Dicke basis
# For N two-level systems, we use collective spin operators
# J = N/2, so the total angular momentum quantum number is j = N/2

# Create collective spin operators by summing individual spins
def create_collective_operators(N, n_max):
    """Create collective spin operators for N two-level systems coupled to cavity"""
    # Identity for cavity
    I_cavity = qt.qeye(n_max)

    # Initialize collective operators
    J_plus = 0
    J_minus = 0
    J_z = 0

    for i in range(N):
        # Create operator list for tensor product
        op_list = [I_cavity]  # Cavity mode first

        for j in range(N):
            if j == i:
                op_list.append(qt.sigmap())  # σ₊ for spin i
            else:
                op_list.append(qt.qeye(2))  # Identity for other spins

        J_plus += qt.tensor(op_list)

        # J_minus
        op_list = [I_cavity]
        for j in range(N):
            if j == i:
                op_list.append(qt.sigmam())  # σ₋ for spin i
            else:
                op_list.append(qt.qeye(2))

        J_minus += qt.tensor(op_list)

        # J_z
        op_list = [I_cavity]
        for j in range(N):
            if j == i:
                op_list.append(qt.sigmaz() / 2.0)  # σ_z/2 for spin i
            else:
                op_list.append(qt.qeye(2))

        J_z += qt.tensor(op_list)

    return J_plus, J_minus, J_z

print("\nConstructing collective spin operators...", flush=True)
J_plus, J_minus, J_z = create_collective_operators(N, n_max)

# Construct Hamiltonian
print("Constructing Dicke Hamiltonian...", flush=True)
H = omega_0 * J_z + omega_c * a_dag * a + g * (a_dag + a) * (J_plus + J_minus)

# Create individual spin operators for local dissipation
def create_individual_spin_ops(N, n_max):
    """Create individual spin operators for each two-level system"""
    sigma_plus_list = []
    sigma_minus_list = []
    sigma_z_list = []

    I_cavity = qt.qeye(n_max)

    for i in range(N):
        op_list = [I_cavity]
        for j in range(N):
            if j == i:
                op_list.append(qt.sigmap())
            else:
                op_list.append(qt.qeye(2))
        sigma_plus_list.append(qt.tensor(op_list))

        op_list = [I_cavity]
        for j in range(N):
            if j == i:
                op_list.append(qt.sigmam())
            else:
                op_list.append(qt.qeye(2))
        sigma_minus_list.append(qt.tensor(op_list))

        op_list = [I_cavity]
        for j in range(N):
            if j == i:
                op_list.append(qt.sigmaz())
            else:
                op_list.append(qt.qeye(2))
        sigma_z_list.append(qt.tensor(op_list))

    return sigma_plus_list, sigma_minus_list, sigma_z_list

print("Constructing individual spin operators...", flush=True)
sigma_plus_list, sigma_minus_list, sigma_z_list = create_individual_spin_ops(N, n_max)

# Define loss cases
loss_cases = [
    {
        'name': 'Case 1: Local dephasing & local pumping',
        'gamma_phi': 0.01,
        'gamma_up': 0.1,
        'gamma_down': 0.0,
        'gamma_col_up': 0.0,
        'gamma_col_down': 0.0,
        'filename': '1.csv'
    },
    {
        'name': 'Case 2: Local dephasing & local emission',
        'gamma_phi': 0.01,
        'gamma_up': 0.0,
        'gamma_down': 0.1,
        'gamma_col_up': 0.0,
        'gamma_col_down': 0.0,
        'filename': '2.csv'
    },
    {
        'name': 'Case 3: Local dephasing & local emission & collective pumping',
        'gamma_phi': 0.01,
        'gamma_up': 0.0,
        'gamma_down': 0.1,
        'gamma_col_up': 0.1,
        'gamma_col_down': 0.0,
        'filename': '3.csv'
    },
    {
        'name': 'Case 4: Local dephasing & local emission & collective emission',
        'gamma_phi': 0.01,
        'gamma_up': 0.0,
        'gamma_down': 0.1,
        'gamma_col_up': 0.0,
        'gamma_col_down': 0.1,
        'filename': '4.csv'
    }
]

def create_collapse_operators(case):
    """Create collapse operators for a given loss case"""
    c_ops = []

    # Cavity decay
    c_ops.append(np.sqrt(kappa) * a)

    # Local dephasing (on each spin)
    gamma_phi = case['gamma_phi']
    if gamma_phi > 0:
        for sigma_z in sigma_z_list:
            c_ops.append(np.sqrt(gamma_phi) * sigma_z)

    # Local pumping (on each spin)
    gamma_up = case['gamma_up']
    if gamma_up > 0:
        for sigma_plus in sigma_plus_list:
            c_ops.append(np.sqrt(gamma_up) * sigma_plus)

    # Local emission (on each spin)
    gamma_down = case['gamma_down']
    if gamma_down > 0:
        for sigma_minus in sigma_minus_list:
            c_ops.append(np.sqrt(gamma_down) * sigma_minus)

    # Collective pumping
    gamma_col_up = case['gamma_col_up']
    if gamma_col_up > 0:
        c_ops.append(np.sqrt(gamma_col_up) * J_plus)

    # Collective emission
    gamma_col_down = case['gamma_col_down']
    if gamma_col_down > 0:
        c_ops.append(np.sqrt(gamma_col_down) * J_minus)

    return c_ops

def trace_out_spins(rho_full, n_max, N):
    """Trace out all spin degrees of freedom to get cavity state

    The full system has dimensions: [n_max, 2, 2, 2, 2] for N=4
    We want to trace out indices [1, 2, 3, 4] to keep only index 0 (cavity)
    """
    # QuTiP uses 0-based indexing
    # We need to trace out spin subsystems (indices 1 through N)
    spin_indices = list(range(1, N + 1))
    rho_cavity = rho_full.ptrace(0)  # Keep only the cavity (index 0)
    return rho_cavity

# Process each loss case
for i, case in enumerate(loss_cases, 1):
    print(f"\n{'='*70}", flush=True)
    print(f"{case['name']}", flush=True)
    print(f"{'='*70}", flush=True)

    # Create collapse operators
    print("Creating collapse operators...", flush=True)
    c_ops = create_collapse_operators(case)
    print(f"  Number of collapse operators: {len(c_ops)}", flush=True)

    # Solve for steady state
    print("Solving for steady state...", flush=True)
    print("  (This may take a few minutes...)", flush=True)
    rho_ss = qt.steadystate(H, c_ops, method='eigen', use_rcm=True)
    print("  Steady state found!", flush=True)

    # Trace out spins to get cavity state
    print("Tracing out spin degrees of freedom...", flush=True)
    rho_cavity = trace_out_spins(rho_ss, n_max, N)

    # Verify trace is 1
    trace_val = rho_cavity.tr()
    print(f"  Cavity state trace: {trace_val:.6f}", flush=True)

    # Calculate Wigner function
    print(f"Calculating Wigner function on {grid_points}×{grid_points} grid...", flush=True)
    xvec = np.linspace(x_min, x_max, grid_points)
    pvec = np.linspace(p_min, p_max, grid_points)

    W = qt.wigner(rho_cavity, xvec, pvec)

    print(f"  Wigner function shape: {W.shape}", flush=True)
    print(f"  Wigner min: {W.min():.6f}, max: {W.max():.6f}", flush=True)

    # Save to CSV
    print(f"Saving to {case['filename']}...", flush=True)

    # Create CSV with x, p, W(x,p) format
    # Each row: x_value, p_value, W_value
    with open(case['filename'], 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['x', 'p', 'W'])

        for i_x, x_val in enumerate(xvec):
            for i_p, p_val in enumerate(pvec):
                writer.writerow([x_val, p_val, W[i_x, i_p]])

    print(f"  ✓ Saved to {case['filename']}", flush=True)

print(f"\n{'='*70}", flush=True)
print("All simulations completed successfully!", flush=True)
print("="*70, flush=True)
print("\nOutput files:", flush=True)
for case in loss_cases:
    filepath = Path(case['filename']).absolute()
    print(f"  {case['filename']}: {case['name']}", flush=True)
print(, flush=True)
