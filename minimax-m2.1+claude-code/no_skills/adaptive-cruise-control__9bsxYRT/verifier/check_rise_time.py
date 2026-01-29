"""Check what happens during rise time."""

import csv

with open('/root/simulation_results.csv', 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Check acceleration profile during first 15 seconds
print("Acceleration profile during first 15 seconds:")
for i, r in enumerate(rows[:150]):
    t = float(r['time'])
    if t <= 15.0:
        speed = float(r['ego_speed'])
        acc = float(r['acceleration_cmd'])
        if t % 1.0 < 0.05:  # Print every second
            print(f"t={t:.1f}: speed={speed:.2f}, acc={acc:.2f}")

# Check when acceleration drops below 3.0
print("\n\nWhen acceleration drops below max:")
for i, r in enumerate(rows):
    t = float(r['time'])
    speed = float(r['ego_speed'])
    acc = float(r['acceleration_cmd'])
    if acc < 3.0 and t < 20:
        print(f"t={t:.1f}: speed={speed:.2f}, acc={acc:.2f}")
        if t > 15:
            break
