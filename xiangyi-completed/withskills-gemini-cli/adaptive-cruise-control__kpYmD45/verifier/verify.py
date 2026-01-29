import pandas as pd
import numpy as np

df = pd.read_csv('simulation_results.csv')
times = df['time'].values
speeds = df['ego_speed'].values
distances = df['distance'].dropna().values
dist_errors = df['distance_error'].dropna().values

# 1. Rise time
t10 = t90 = None
for t, v in zip(times, speeds):
    if t < 30.0:
        if t10 is None and v >= 3.0: t10 = t
        if t90 is None and v >= 27.0: t90 = t
rise_time = t90 - t10 if t10 is not None and t90 is not None else 999

# 2. Overshoot
cruise_speeds = [v for t, v in zip(times, speeds) if 10.0 < t < 30.0]
max_speed = max(cruise_speeds)
overshoot = (max_speed - 30.0) / 30.0 * 100 if max_speed > 30.0 else 0

# 3. Speed SS error
ss_speed_err = abs(30.0 - np.mean(speeds[250:300]))

# 4. Distance SS error
ss_dist_err = np.mean([abs(e) for e in dist_errors[-100:]])

# 5. Min distance
min_dist = min(distances)

print(f"Rise Time: {rise_time:.2f}s (Target < 10s)")
print(f"Overshoot: {overshoot:.2f}% (Target < 5%)")
print(f"Speed SS Error: {ss_speed_err:.4f} m/s (Target < 0.5 m/s)")
print(f"Distance SS Error: {ss_dist_err:.4f} m (Target < 2 m)")
print(f"Minimum Distance: {min_dist:.2f} m (Target > 5 m)")
min_dist_idx = df['distance'].idxmin()
print("\nRows around minimum distance:")
print(df.iloc[max(0, min_dist_idx-5):min_dist_idx+5])

print("\nFirst 10 follow rows:")
print(df[df['mode'] == 'follow'].head(10))

print("\nLast 10 follow rows:")
print(df[df['mode'] == 'follow'].tail(10))
