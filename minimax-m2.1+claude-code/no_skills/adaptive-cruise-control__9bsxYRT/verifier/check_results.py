"""Check distance error during follow mode."""

import csv

with open('/root/simulation_results.csv', 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

# Check follow mode rows with reasonable distance (< 80m)
follow_rows = [r for r in rows if r['mode'] in ['follow', 'emergency'] and r['distance'] and float(r['distance']) < 80]

print(f"Total follow rows with distance < 80m: {len(follow_rows)}")

# Check distance errors
if follow_rows:
    distance_errors = [abs(float(r['distance_error'])) for r in follow_rows[-300:] if r['distance_error']]
    print(f"Distance errors in last 30s of follow: min={min(distance_errors):.2f}, max={max(distance_errors):.2f}, mean={sum(distance_errors)/len(distance_errors):.2f}")

# Check distances during follow mode
distances = [float(r['distance']) for r in follow_rows]
print(f"\nDistance stats (during follow, <80m): min={min(distances):.2f}, max={max(distances):.2f}, mean={sum(distances)/len(distances):.2f}")

# Check what distance errors look like
print("\nSample distance errors:")
for r in follow_rows[-20:]:
    t = float(r['time'])
    dist = float(r['distance'])
    err = r['distance_error']
    if err:
        print(f"t={t:.1f}: dist={dist:.2f}, error={err:.2f}")
