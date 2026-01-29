"""Debug ACC output during cruise mode."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl

# Load config
with open('/root/vehicle_params.yaml', 'r') as f:
    config = yaml.safe_load(f)

with open('/root/tuning_results.yaml', 'r') as f:
    tuning = yaml.safe_load(f)

config['pid_speed'] = tuning['pid_speed']
config['pid_distance'] = tuning['pid_distance']

acc = AdaptiveCruiseControl(config)

# Simulate first 15 seconds
dt = 0.1
ego_speed = 0.0

print("Simulating with ACC system directly:")
for t in [i * dt for i in range(150)]:
    acc_cmd, mode, _ = acc.compute(
        ego_speed=ego_speed,
        lead_speed=None,
        distance=None,
        dt=dt
    )

    ego_speed += acc_cmd * dt
    ego_speed = max(0.0, ego_speed)

    if t < 15.0 and t % 1.0 < 0.05:
        speed_error = 30.0 - ego_speed
        print(f"t={t:.1f}: ego={ego_speed:.2f}, err={speed_error:.2f}, acc={acc_cmd:.2f}, mode={mode}")

    if t > 6.0 and t < 6.2:
        speed_error = 30.0 - ego_speed
        print(f"t={t:.1f}: ego={ego_speed:.2f}, err={speed_error:.2f}, acc={acc_cmd:.2f}, mode={mode}")
