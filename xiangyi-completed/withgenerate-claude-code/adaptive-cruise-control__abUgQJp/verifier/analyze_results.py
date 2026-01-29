"""Analyze simulation results for the ACC report."""

import csv


def load_results(filepath):
    results = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {}
            for key, value in row.items():
                if value == '':
                    entry[key] = None
                else:
                    try:
                        entry[key] = float(value)
                    except ValueError:
                        entry[key] = value
            results.append(entry)
    return results


def analyze(results, set_speed=30.0):
    """Analyze simulation results and compute metrics."""

    # Separate by mode
    cruise_results = [r for r in results if r['mode'] == 'cruise']
    follow_results = [r for r in results if r['mode'] == 'follow']
    emergency_results = [r for r in results if r['mode'] == 'emergency']

    # Initial cruise (before lead vehicle at t=30)
    early_cruise = [r for r in cruise_results if r['time'] < 30]

    # Rise time (90% of set speed)
    target_90 = 0.9 * set_speed
    rise_time = None
    for r in early_cruise:
        if r['ego_speed'] >= target_90:
            rise_time = r['time']
            break

    # Overshoot during initial cruise
    if early_cruise:
        max_speed_early = max(r['ego_speed'] for r in early_cruise)
        overshoot_pct = max(0, (max_speed_early - set_speed) / set_speed * 100)
    else:
        overshoot_pct = 0

    # Steady-state error for speed (t=25-30)
    steady_cruise = [r for r in early_cruise if 25 <= r['time'] <= 30]
    if steady_cruise:
        avg_speed = sum(r['ego_speed'] for r in steady_cruise) / len(steady_cruise)
        speed_ss_error = abs(set_speed - avg_speed)
    else:
        speed_ss_error = None

    # Final cruise phase (t > 145)
    late_cruise = [r for r in cruise_results if r['time'] > 145]
    if late_cruise:
        avg_speed_late = sum(r['ego_speed'] for r in late_cruise) / len(late_cruise)
        speed_ss_error_late = abs(set_speed - avg_speed_late)
    else:
        speed_ss_error_late = None

    # Distance control metrics
    if follow_results:
        dist_errors = [abs(r['distance_error']) for r in follow_results
                       if r['distance_error'] is not None]
        avg_dist_error = sum(dist_errors) / len(dist_errors) if dist_errors else None
    else:
        avg_dist_error = None

    # All distances (including emergency)
    all_distances = [r['distance'] for r in results if r['distance'] is not None]
    min_distance = min(all_distances) if all_distances else float('inf')

    # Mode statistics
    mode_counts = {
        'cruise': len(cruise_results),
        'follow': len(follow_results),
        'emergency': len(emergency_results)
    }

    # Emergency braking events
    emergency_events = []
    in_emergency = False
    event_start = None
    for r in results:
        if r['mode'] == 'emergency' and not in_emergency:
            in_emergency = True
            event_start = r['time']
        elif r['mode'] != 'emergency' and in_emergency:
            in_emergency = False
            emergency_events.append({
                'start': event_start,
                'end': r['time']
            })

    return {
        'rise_time': rise_time,
        'overshoot_pct': overshoot_pct,
        'speed_ss_error': speed_ss_error,
        'speed_ss_error_late': speed_ss_error_late,
        'avg_dist_error': avg_dist_error,
        'min_distance': min_distance,
        'mode_counts': mode_counts,
        'emergency_events': emergency_events,
        'total_timesteps': len(results)
    }


def main():
    results = load_results('simulation_results.csv')
    metrics = analyze(results)

    print("=" * 60)
    print("ACC Simulation Results Analysis")
    print("=" * 60)

    print("\n## Speed Control Performance")
    print(f"  Rise time (0 to 27 m/s): {metrics['rise_time']:.2f}s (target: <10s) {'PASS' if metrics['rise_time'] < 10 else 'FAIL'}")
    print(f"  Speed overshoot: {metrics['overshoot_pct']:.3f}% (target: <5%) {'PASS' if metrics['overshoot_pct'] < 5 else 'FAIL'}")
    print(f"  Speed SS error (t=25-30): {metrics['speed_ss_error']:.4f} m/s (target: <0.5 m/s) {'PASS' if metrics['speed_ss_error'] < 0.5 else 'FAIL'}")
    if metrics['speed_ss_error_late'] is not None:
        print(f"  Speed SS error (t>145): {metrics['speed_ss_error_late']:.4f} m/s")

    print("\n## Distance Control Performance")
    if metrics['avg_dist_error'] is not None:
        print(f"  Average distance error: {metrics['avg_dist_error']:.2f}m (target: <2m) {'PASS' if metrics['avg_dist_error'] < 2 else 'FAIL'}")
    print(f"  Minimum distance: {metrics['min_distance']:.2f}m (target: >5m) {'PASS' if metrics['min_distance'] > 5 else 'FAIL'}")

    print("\n## Mode Statistics")
    for mode, count in metrics['mode_counts'].items():
        pct = count / metrics['total_timesteps'] * 100
        print(f"  {mode}: {count} timesteps ({pct:.1f}%)")

    print("\n## Emergency Events")
    if metrics['emergency_events']:
        for i, event in enumerate(metrics['emergency_events'], 1):
            duration = event['end'] - event['start']
            print(f"  Event {i}: t={event['start']:.1f}s to t={event['end']:.1f}s (duration: {duration:.1f}s)")
    else:
        print("  No emergency events")

    print("\n## Overall Assessment")
    all_pass = (
        metrics['rise_time'] < 10 and
        metrics['overshoot_pct'] < 5 and
        metrics['speed_ss_error'] < 0.5 and
        metrics['min_distance'] > 5 and
        (metrics['avg_dist_error'] is None or metrics['avg_dist_error'] < 2)
    )
    print(f"  All targets met: {'YES' if all_pass else 'NO'}")


if __name__ == '__main__':
    main()
