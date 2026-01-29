"""Aggressive PID tuning to meet safety requirements."""

import pandas as pd
import yaml
from acc_system import AdaptiveCruiseControl


def simulate_with_params(speed_kp, speed_ki, dist_kp, dist_ki, dist_kd, sensor_data, config, dt):
    """Run simulation."""
    config['pid_speed'] = {'kp': speed_kp, 'ki': speed_ki, 'kd': 0.0}
    config['pid_distance'] = {'kp': dist_kp, 'ki': dist_ki, 'kd': dist_kd}

    acc = AdaptiveCruiseControl(config)
    ego_speed = 0.0
    results = []

    for idx, row in sensor_data.iterrows():
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None

        accel_cmd, mode, dist_error = acc.compute(ego_speed, lead_speed, distance, dt)
        ego_speed += accel_cmd * dt
        ego_speed = max(0, ego_speed)

        results.append({
            'time': row['time'],
            'ego_speed': ego_speed,
            'accel': accel_cmd,
            'mode': mode,
            'dist_error': dist_error,
            'distance': distance,
        })

    return pd.DataFrame(results)


def check_requirements(df, set_speed):
    """Check all requirements."""
    # Cruise mode analysis
    cruise = df[df['mode'] == 'cruise']

    if len(cruise) < 10:
        return None, False

    # 1. Rise time
    idx_90 = cruise[cruise['ego_speed'] >= 0.9 * set_speed].index
    rise_time = cruise.loc[idx_90[0], 'time'] if len(idx_90) > 0 else 999

    # 2. Overshoot
    max_speed = cruise['ego_speed'].max()
    overshoot = (max_speed - set_speed) / set_speed * 100

    # 3. Speed steady state (last 10%)
    n_steady = max(int(len(cruise) * 0.1), 10)
    speed_ss_err = abs(cruise['ego_speed'].iloc[-n_steady:].mean() - set_speed)

    # Follow mode analysis
    follow = df[df['mode'] == 'follow']

    # 4. Distance steady state (last 10%)
    if len(follow) > 10:
        dist_errs = follow['dist_error'].dropna()
        if len(dist_errs) > 10:
            n_steady = max(int(len(dist_errs) * 0.1), 10)
            dist_ss_err = abs(dist_errs.iloc[-n_steady:].mean())
        else:
            dist_ss_err = 999
    else:
        dist_ss_err = 999

    # 5. Minimum distance
    all_dist = df['distance'].dropna()
    min_dist = all_dist.min() if len(all_dist) > 0 else 999

    metrics = {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'speed_ss': speed_ss_err,
        'dist_ss': dist_ss_err,
        'min_dist': min_dist,
    }

    # Check pass/fail
    passed = (
        rise_time < 10 and
        overshoot < 5 and
        speed_ss_err < 0.5 and
        dist_ss_err < 2.0 and
        min_dist > 5.0
    )

    return metrics, passed


def aggressive_search():
    """Aggressive search for parameters."""
    with open('/root/vehicle_params.yaml', 'r') as f:
        config = yaml.safe_load(f)

    sensor_data = pd.read_csv('/root/sensor_data.csv')
    dt = config['simulation']['dt']
    set_speed = config['acc_settings']['set_speed']

    print("Aggressive PID Search")
    print("=" * 70)

    # Very conservative speed control to minimize overshoot
    speed_kps = [0.4, 0.45, 0.5, 0.55]
    speed_kis = [0.03, 0.04, 0.05]

    # Very aggressive distance control for safety
    dist_kps = [6.0, 7.0, 8.0, 9.0]
    dist_kis = [0.3, 0.4, 0.5]
    dist_kds = [2.0, 2.5, 3.0]

    best = None
    solutions = []

    total = len(speed_kps) * len(speed_kis) * len(dist_kps) * len(dist_kis) * len(dist_kds)
    tested = 0

    for speed_kp in speed_kps:
        for speed_ki in speed_kis:
            for dist_kp in dist_kps:
                for dist_ki in dist_kis:
                    for dist_kd in dist_kds:
                        tested += 1
                        if tested % 50 == 0:
                            print(f"Tested {tested}/{total}, found {len(solutions)} solutions...")

                        df = simulate_with_params(speed_kp, speed_ki, dist_kp, dist_ki, dist_kd,
                                                   sensor_data, config, dt)
                        metrics, passed = check_requirements(df, set_speed)

                        if metrics is None:
                            continue

                        if passed:
                            solutions.append({
                                'speed_kp': speed_kp,
                                'speed_ki': speed_ki,
                                'dist_kp': dist_kp,
                                'dist_ki': dist_ki,
                                'dist_kd': dist_kd,
                                'metrics': metrics
                            })
                            print(f"\n✓ Solution #{len(solutions)}:")
                            print(f"  Speed: kp={speed_kp}, ki={speed_ki}")
                            print(f"  Dist:  kp={dist_kp}, ki={dist_ki}, kd={dist_kd}")
                            print(f"  RT={metrics['rise_time']:.2f}s, OS={metrics['overshoot']:.2f}%, " +
                                  f"SS_v={metrics['speed_ss']:.3f}, SS_d={metrics['dist_ss']:.3f}, " +
                                  f"min_d={metrics['min_dist']:.2f}m")

                        if best is None or (metrics is not None and metrics['min_dist'] > best['metrics']['min_dist']):
                            best = {
                                'speed_kp': speed_kp,
                                'speed_ki': speed_ki,
                                'dist_kp': dist_kp,
                                'dist_ki': dist_ki,
                                'dist_kd': dist_kd,
                                'metrics': metrics,
                                'passed': passed
                            }

    print(f"\n{'=' * 70}")
    print(f"Search complete: {len(solutions)} valid solutions found")
    print(f"{'=' * 70}\n")

    if len(solutions) > 0:
        # Use first solution (prefer lower gains = smoother)
        final = solutions[0]
        print("Selected solution (first found):")
    else:
        print("No perfect solution found. Using best attempt:")
        final = best

    print(f"\nSpeed PID:    kp={final['speed_kp']}, ki={final['speed_ki']}, kd=0.0")
    print(f"Distance PID: kp={final['dist_kp']}, ki={final['dist_ki']}, kd={final['dist_kd']}")

    m = final['metrics']
    print(f"\nPerformance:")
    print(f"  Rise time:        {m['rise_time']:6.2f}s  ({'✓' if m['rise_time'] < 10 else '✗'} <10s)")
    print(f"  Overshoot:        {m['overshoot']:6.2f}%  ({'✓' if m['overshoot'] < 5 else '✗'} <5%)")
    print(f"  Speed SS error:   {m['speed_ss']:6.3f} m/s ({'✓' if m['speed_ss'] < 0.5 else '✗'} <0.5)")
    print(f"  Distance SS error:{m['dist_ss']:6.3f} m   ({'✓' if m['dist_ss'] < 2 else '✗'} <2m)")
    print(f"  Min distance:     {m['min_dist']:6.2f} m   ({'✓' if m['min_dist'] > 5 else '✗'} >5m)")

    # Save
    result = {
        'pid_speed': {
            'kp': float(final['speed_kp']),
            'ki': float(final['speed_ki']),
            'kd': 0.0
        },
        'pid_distance': {
            'kp': float(final['dist_kp']),
            'ki': float(final['dist_ki']),
            'kd': float(final['dist_kd'])
        }
    }

    with open('/root/tuning_results.yaml', 'w') as f:
        yaml.dump(result, f, default_flow_style=False)

    print("\n✓ Saved to tuning_results.yaml")


if __name__ == '__main__':
    aggressive_search()
