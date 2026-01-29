"""Analyze lead vehicle data from sensor_data.csv."""

import csv

with open('/root/sensor_data.csv', 'r') as f:
    reader = csv.DictReader(f)
    data = list(reader)

# Find rows with lead vehicle
rows_with_lead = [r for r in data if r['lead_speed'].strip()]

print(f"Lead vehicle present from t={rows_with_lead[0]['time']}s to t={rows_with_lead[-1]['time']}s")
print(f"Total rows with lead: {len(rows_with_lead)}")

# Sample some distances
sample_indices = [0, 100, 200, 500, 800, 999]
for idx in sample_indices:
    if idx < len(rows_with_lead):
        r = rows_with_lead[idx]
        t = float(r['time'])
        lead_spd = float(r['lead_speed'])
        dist = float(r['distance'])
        desired_at_30 = max(10, 30 * 1.5)  # At ego speed ~30
        print(f"t={t:.1f}: lead_speed={lead_spd:.2f}, distance={dist:.2f}, desired(ego=30)={desired_at_30}")

# Check distance range
distances = [float(r['distance']) for r in rows_with_lead]
print(f"\nDistance stats:")
print(f"  Min: {min(distances):.2f}")
print(f"  Max: {max(distances):.2f}")
print(f"  Mean: {sum(distances)/len(distances):.2f}")
