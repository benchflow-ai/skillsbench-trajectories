"""Optimized PID tuning for ACC system with proper vehicle dynamics."""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def simulate_with_gains(speed_kp, speed_ki, speed_kd, dist_kp, dist_ki, dist_kd):
    """Simulate ACC system with given PID gains."""
    # Load config and sensor data
    with open('vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    sensor_df = pd.read_csv('sensor_data.csv')
    dt = config['simulation']['dt']

    # Update PID gains
    config['pid_speed'] = {'kp': speed_kp, 'ki': speed_ki, 'kd': speed_kd}
    config['pid_distance'] = {'kp': dist_kp, 'ki': dist_ki, 'kd': dist_kd}

    # Create ACC system
    acc = AdaptiveCruiseControl(config)

    # Initialize ego vehicle
    ego_speed = 0.0
    set_speed = config['acc_settings']['set_speed']

    # Track metrics
    speeds = []
    min_distance = float('inf')
    distance_errors_follow = []

    # Simulate
    for idx, row in sensor_df.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        # Compute ACC control
        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)

        # Update ego vehicle speed (Euler integration)
        ego_speed = max(0.0, ego_speed + accel_cmd * dt)
        speeds.append(ego_speed)

        # Track following errors
        if mode == 'follow' and dist_error is not None:
            distance_errors_follow.append(abs(dist_error))

        # Track minimum distance
        if distance is not None:
            # Adjust distance based on speed difference (rough approximation)
            # This simulates the relative motion
            if lead_speed is not None:
                relative_speed = ego_speed - lead_speed
                adjusted_dist = distance - relative_speed * dt * idx  # Approximate
                min_distance = min(min_distance, adjusted_dist)

    speeds = np.array(speeds)

    # Metrics
    # 1. Rise time to 90% of set speed
    rise_idx = np.where(speeds >= 0.9 * set_speed)[0]
    rise_time = rise_idx[0] * dt if len(rise_idx) > 0 else 999

    # 2. Overshoot in cruise phase (first 30s)
    cruise_speeds = speeds[:min(300, len(speeds))]
    overshoot = max(0, (cruise_speeds.max() - set_speed) / set_speed * 100)

    # 3. Speed steady-state error (25-30s of cruise)
    ss_start = min(250, len(speeds)-10)
    ss_end = min(300, len(speeds))
    if ss_end > ss_start:
        speed_ss_error = abs(speeds[ss_start:ss_end].mean() - set_speed)
    else:
        speed_ss_error = 999

    # 4. Distance steady-state error (last 30% of following)
    if distance_errors_follow:
        steady_idx = int(len(distance_errors_follow) * 0.7)
        dist_ss_error = np.mean(distance_errors_follow[steady_idx:])
    else:
        dist_ss_error = 0

    # 5. Minimum distance check
    if min_distance == float('inf'):
        min_distance = 999

    # Score function (lower is better)
    score = 0

    # Critical constraints (heavy penalties)
    if rise_time > 10:
        score += (rise_time - 10) ** 2 * 100
    else:
        score += rise_time

    if overshoot > 5:
        score += (overshoot - 5) ** 2 * 20
    else:
        score += overshoot * 0.5

    if speed_ss_error > 0.5:
        score += (speed_ss_error - 0.5) ** 2 * 200
    else:
        score += speed_ss_error * 2

    if dist_ss_error > 2:
        score += (dist_ss_error - 2) ** 2 * 100
    else:
        score += dist_ss_error

    if min_distance < 5:
        score += (5 - min_distance) ** 2 * 1000

    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'speed_ss_error': speed_ss_error,
        'dist_ss_error': dist_ss_error,
        'min_distance': min_distance,
        'score': score
    }


def tune():
    """Tune PID parameters using focused grid search."""
    print("ACC PID Tuning - Focused Search")
    print("=" * 70)

    best_score = float('inf')
    best_gains = None
    best_metrics = None

    # Focused parameter ranges based on control theory
    # Speed: Need strong P and I for fast rise and zero SS error, D for damping
    speed_params = [
        (2.0, 0.3, 3.0),
        (2.5, 0.3, 3.0),
        (2.5, 0.4, 3.0),
        (3.0, 0.3, 3.0),
        (3.0, 0.4, 3.0),
        (3.0, 0.4, 4.0),
        (3.5, 0.4, 3.0),
        (3.5, 0.4, 4.0),
    ]

    # Distance: Moderate P, low I, moderate D for smooth following
    dist_params = [
        (0.8, 0.02, 2.5),
        (1.0, 0.02, 2.5),
        (1.0, 0.03, 3.0),
        (1.2, 0.02, 2.5),
        (1.2, 0.03, 3.0),
        (1.5, 0.02, 3.0),
    ]

    total = len(speed_params) * len(dist_params)
    count = 0

    for s_kp, s_ki, s_kd in speed_params:
        for d_kp, d_ki, d_kd in dist_params:
            count += 1

            try:
                metrics = simulate_with_gains(s_kp, s_ki, s_kd, d_kp, d_ki, d_kd)

                if metrics['score'] < best_score:
                    best_score = metrics['score']
                    best_gains = {
                        'speed': (s_kp, s_ki, s_kd),
                        'dist': (d_kp, d_ki, d_kd)
                    }
                    best_metrics = metrics

                    meets = all([
                        metrics['rise_time'] < 10,
                        metrics['overshoot'] < 5,
                        metrics['speed_ss_error'] < 0.5,
                        metrics['dist_ss_error'] < 2,
                        metrics['min_distance'] > 5
                    ])

                    print(f"\n[{count}/{total}] New best! Score: {best_score:.2f} {'✓ ALL' if meets else ''}")
                    print(f"  Speed PID: Kp={s_kp}, Ki={s_ki}, Kd={s_kd}")
                    print(f"  Dist PID:  Kp={d_kp}, Ki={d_ki}, Kd={d_kd}")
                    print(f"  Rise: {metrics['rise_time']:.1f}s {'✓' if metrics['rise_time']<10 else '✗'}", end="")
                    print(f" | Overshoot: {metrics['overshoot']:.1f}% {'✓' if metrics['overshoot']<5 else '✗'}", end="")
                    print(f" | Speed SS: {metrics['speed_ss_error']:.2f} {'✓' if metrics['speed_ss_error']<0.5 else '✗'}")
                    print(f"  Dist SS: {metrics['dist_ss_error']:.2f}m {'✓' if metrics['dist_ss_error']<2 else '✗'}", end="")
                    print(f" | Min dist: {metrics['min_distance']:.1f}m {'✓' if metrics['min_distance']>5 else '✗'}")

            except Exception as e:
                print(f"[{count}/{total}] Error: {e}")

            if count % 10 == 0:
                print(f"  Progress: {count}/{total} ({100*count/total:.0f}%)")

    print("\n" + "=" * 70)
    print("TUNING COMPLETE\n")

    s_kp, s_ki, s_kd = best_gains['speed']
    d_kp, d_ki, d_kd = best_gains['dist']

    print(f"Best Speed PID:    Kp={s_kp:.2f}, Ki={s_ki:.2f}, Kd={s_kd:.2f}")
    print(f"Best Distance PID: Kp={d_kp:.2f}, Ki={d_ki:.2f}, Kd={d_kd:.2f}\n")
    print(f"Performance:")
    print(f"  Rise time: {best_metrics['rise_time']:.2f}s (target: <10s)")
    print(f"  Overshoot: {best_metrics['overshoot']:.2f}% (target: <5%)")
    print(f"  Speed SS error: {best_metrics['speed_ss_error']:.3f} m/s (target: <0.5 m/s)")
    print(f"  Distance SS error: {best_metrics['dist_ss_error']:.3f} m (target: <2m)")
    print(f"  Min distance: {best_metrics['min_distance']:.2f} m (target: >5m)")

    # Save results
    results = {
        'pid_speed': {'kp': float(s_kp), 'ki': float(s_ki), 'kd': float(s_kd)},
        'pid_distance': {'kp': float(d_kp), 'ki': float(d_ki), 'kd': float(d_kd)}
    }

    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(results, f, default_flow_style=False)

    print(f"\nSaved to tuning_results.yaml")


if __name__ == '__main__':
    tune()
