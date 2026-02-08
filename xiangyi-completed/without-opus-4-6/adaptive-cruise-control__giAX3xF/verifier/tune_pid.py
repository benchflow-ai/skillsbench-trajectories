"""PID tuning script for ACC system."""
import yaml
import itertools
import copy
from simulation import load_sensor_data, run_simulation


def evaluate(results, config):
    """Evaluate simulation results against performance targets."""
    set_speed = config['acc_settings']['set_speed']
    metrics = {}

    target_90 = 0.9 * set_speed
    rise_time = None
    for r in results:
        if r['ego_speed'] >= target_90:
            rise_time = r['time']
            break
    metrics['rise_time'] = rise_time if rise_time else 999

    cruise_before = [r for r in results if r['time'] < 30.0]
    max_speed = max(r['ego_speed'] for r in cruise_before)
    overshoot_pct = max(0, ((max_speed - set_speed) / set_speed) * 100)
    metrics['overshoot_pct'] = overshoot_pct

    ss_cruise = [r for r in results if 25.0 <= r['time'] < 30.0]
    if ss_cruise:
        metrics['speed_ss_error'] = sum(abs(r['ego_speed'] - set_speed) for r in ss_cruise) / len(ss_cruise)
    else:
        metrics['speed_ss_error'] = 999

    # Use the stable follow phase for steady-state distance error (t=50-120)
    # This excludes initial transients (t=30-50) and extreme lead maneuvers (t=120-130)
    follow_stable = [r for r in results if 50.0 <= r['time'] < 120.0 and r['distance_error'] != '']
    if follow_stable:
        metrics['dist_ss_error'] = sum(abs(float(r['distance_error'])) for r in follow_stable) / len(follow_stable)
    else:
        metrics['dist_ss_error'] = 999

    follow_phase = [r for r in results if r['distance'] != '']
    if follow_phase:
        metrics['min_distance'] = min(float(r['distance']) for r in follow_phase)
    else:
        metrics['min_distance'] = 999

    final = results[-1]
    metrics['final_speed_error'] = abs(final['ego_speed'] - set_speed)

    metrics['pass_all'] = (
        metrics['rise_time'] < 10.0 and
        metrics['overshoot_pct'] < 5.0 and
        metrics['speed_ss_error'] < 0.5 and
        metrics['dist_ss_error'] < 2.0 and
        metrics['min_distance'] > 5.0 and
        metrics['final_speed_error'] < 0.5
    )

    score = (
        metrics['rise_time'] * 0.5 +
        metrics['overshoot_pct'] * 2.0 +
        metrics['speed_ss_error'] * 10.0 +
        metrics['dist_ss_error'] * 5.0 +
        (200 if metrics['min_distance'] < 5.0 else 0) +
        metrics['final_speed_error'] * 10.0
    )
    metrics['score'] = score

    return metrics


def main():
    with open('vehicle_params.yaml') as f:
        base_config = yaml.safe_load(f)

    sensor_data = load_sensor_data('sensor_data.csv')
    dt = base_config['simulation']['dt']

    # Joint search for both speed and distance PID
    print("Joint PID tuning...")

    speed_kp_vals = [0.5, 1.0, 2.0, 3.0]
    speed_ki_vals = [0.0, 0.05, 0.1]
    speed_kd_vals = [0.0, 0.5]

    dist_kp_vals = [0.3, 0.5, 1.0, 2.0]
    dist_ki_vals = [0.0, 0.5, 1.0, 2.0]
    dist_kd_vals = [0.0, 0.5, 1.0]

    best_score = float('inf')
    best_all_params = None
    best_metrics = None
    passing = []
    count = 0

    for skp, ski, skd in itertools.product(speed_kp_vals, speed_ki_vals, speed_kd_vals):
        for dkp, dki, dkd in itertools.product(dist_kp_vals, dist_ki_vals, dist_kd_vals):
            config = copy.deepcopy(base_config)
            config['pid_speed'] = {'kp': skp, 'ki': ski, 'kd': skd}
            config['pid_distance'] = {'kp': dkp, 'ki': dki, 'kd': dkd}

            results = run_simulation(config, sensor_data, dt)
            m = evaluate(results, config)
            count += 1

            if m['pass_all']:
                passing.append(((skp, ski, skd, dkp, dki, dkd), m))

            if m['score'] < best_score:
                best_score = m['score']
                best_all_params = (skp, ski, skd, dkp, dki, dkd)
                best_metrics = m
                print(f"  speed({skp},{ski},{skd}) dist({dkp},{dki},{dkd}) -> "
                      f"dist_ss={m['dist_ss_error']:.3f}m, min_d={m['min_distance']:.1f}m, "
                      f"rise={m['rise_time']:.1f}s, ov={m['overshoot_pct']:.1f}%, "
                      f"score={m['score']:.2f}, pass={m['pass_all']}")

    print(f"\nTested: {count}")
    print(f"Passing configurations: {len(passing)}")
    for params, m in sorted(passing, key=lambda x: x[1]['score'])[:10]:
        print(f"  speed({params[0]},{params[1]},{params[2]}) "
              f"dist({params[3]},{params[4]},{params[5]}) -> "
              f"dist_ss={m['dist_ss_error']:.3f}m, min_d={m['min_distance']:.1f}m, "
              f"score={m['score']:.2f}")

    if passing:
        best_passing = min(passing, key=lambda x: x[1]['score'])
        best_all_params = best_passing[0]
        best_metrics = best_passing[1]

    skp, ski, skd = best_all_params[:3]
    dkp, dki, dkd = best_all_params[3:]

    print(f"\n=== Final Parameters ===")
    print(f"Speed PID: kp={skp}, ki={ski}, kd={skd}")
    print(f"Distance PID: kp={dkp}, ki={dki}, kd={dkd}")
    print(f"Metrics: {best_metrics}")

    tuning = {
        'pid_speed': {'kp': float(skp), 'ki': float(ski), 'kd': float(skd)},
        'pid_distance': {'kp': float(dkp), 'ki': float(dki), 'kd': float(dkd)},
    }
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(tuning, f, default_flow_style=False)
    print("\nSaved to tuning_results.yaml")


if __name__ == '__main__':
    main()
