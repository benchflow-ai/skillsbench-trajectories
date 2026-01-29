"""Debug emergency mode trigger."""

import csv

# Load sensor data and our simulation results
sensor_data = []
with open('/root/sensor_data.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sensor_data.append({
            'time': float(row['time']),
            'ego_speed': float(row['ego_speed']),
            'lead_speed': float(row['lead_speed']) if row['lead_speed'].strip() else None,
            'distance': float(row['distance']) if row['distance'].strip() else None
        })

sim_data = []
with open('/root/simulation_results.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sim_data.append({
            'time': float(row['time']),
            'ego_speed': float(row['ego_speed']),
            'acc': float(row['acceleration_cmd']),
            'mode': row['mode']
        })

# Check around t=120
print("Checking around t=120:")
for i in range(1190, 1220):
    if i < len(sensor_data):
        s = sensor_data[i]
        sim = sim_data[i]
        t = s['time']
        if abs(t - 120) < 5:
            rel_speed = sim['ego_speed'] - s['lead_speed'] if s['lead_speed'] else None
            ttc = s['distance'] / rel_speed if rel_speed and rel_speed > 0 else float('inf')
            print(f"t={t:.1f}: ego={sim['ego_speed']:.2f}, lead={s['lead_speed']}, dist={s['distance']}, rel={rel_speed}, ttc={ttc:.2f}, mode={sim['mode']}")
