"""PID tuning — cascade architecture with refined metrics."""

import csv
import yaml

with open('vehicle_params.yaml', 'r') as f:
    config = yaml.safe_load(f)

sensor_data = []
with open('sensor_data.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        t = float(row['time'])
        ls = float(row['lead_speed']) if row['lead_speed'] != '' else None
        d = float(row['distance']) if row['distance'] != '' else None
        sensor_data.append((t, ls, d))

DT = 0.1
SET_SPEED = 30.0
TIME_HEADWAY = 1.5
MIN_DIST = 10.0
EMERGENCY_TTC = 3.0
MAX_ACCEL = 3.0
MAX_DECEL = -8.0
INITIAL_GAP = 52.1


def simulate(sp_kp, sp_ki, sp_kd, dp_kp, dp_ki, dp_kd):
    ego_speed = 0.0
    ego_pos = 0.0

    sp_integral = 0.0
    sp_prev_error = None
    dp_integral = 0.0
    dp_prev_error = None

    lead_pos = None
    min_distance_sim = float('inf')
    distance_errors_ss = []

    speeds = []
    accels = []
    modes = []
    distances_out = []
    dist_errors_out = []
    ttcs_out = []

    for i, (t, lead_speed, sensor_dist) in enumerate(sensor_data):
        has_lead = (lead_speed is not None)

        if has_lead and lead_pos is None:
            lead_pos = ego_pos + INITIAL_GAP

        if has_lead:
            distance = lead_pos - ego_pos
        else:
            distance = None
            lead_pos = None

        if not has_lead:
            # CRUISE mode
            speed_error = SET_SPEED - ego_speed
            p_term = sp_kp * speed_error
            d_term = 0.0 if sp_prev_error is None else sp_kd * (speed_error - sp_prev_error) / DT
            sp_prev_error = speed_error
            i_term = sp_ki * sp_integral

            raw = p_term + i_term + d_term
            accel_cmd = max(MAX_DECEL, min(MAX_ACCEL, raw))

            if MAX_DECEL < raw < MAX_ACCEL:
                sp_integral += speed_error * DT

            dp_integral = 0.0
            dp_prev_error = None
            mode = 'cruise'
            dist_error = None
            ttc_val = None
        else:
            closing = ego_speed - lead_speed
            ttc_val = (distance / closing) if (closing > 0 and distance > 0) else None

            desired_dist = MIN_DIST + TIME_HEADWAY * ego_speed
            dist_error = distance - desired_dist

            if ttc_val is not None and ttc_val < EMERGENCY_TTC:
                accel_cmd = MAX_DECEL
                mode = 'emergency'
                dp_integral = 0.0
                dp_prev_error = None
                sp_integral = 0.0
                sp_prev_error = None
            else:
                mode = 'follow'

                # Outer loop: distance PID → speed correction
                dp_p = dp_kp * dist_error
                dp_d = 0.0 if dp_prev_error is None else dp_kd * (dist_error - dp_prev_error) / DT
                dp_prev_error = dist_error
                dp_i = dp_ki * dp_integral

                speed_correction = dp_p + dp_i + dp_d
                speed_correction = max(-15.0, min(15.0, speed_correction))

                if -15.0 < (dp_p + dp_i + dp_d) < 15.0:
                    dp_integral += dist_error * DT

                target_speed = lead_speed + speed_correction
                target_speed = max(0.0, min(SET_SPEED, target_speed))

                # Inner loop: speed PID
                speed_error = target_speed - ego_speed
                sp_p = sp_kp * speed_error
                sp_d = 0.0 if sp_prev_error is None else sp_kd * (speed_error - sp_prev_error) / DT
                sp_prev_error = speed_error
                sp_i = sp_ki * sp_integral

                raw = sp_p + sp_i + sp_d
                accel_cmd = max(MAX_DECEL, min(MAX_ACCEL, raw))

                if MAX_DECEL < raw < MAX_ACCEL:
                    sp_integral += speed_error * DT

            if distance is not None:
                min_distance_sim = min(min_distance_sim, distance)
                # Distance SS: measure when lead_speed <= set_speed and after initial settling
                if 35.0 <= t <= 65.0:
                    distance_errors_ss.append(abs(dist_error))

        accel_cmd = max(MAX_DECEL, min(MAX_ACCEL, accel_cmd))
        ego_speed = max(0.0, ego_speed + accel_cmd * DT)
        ego_pos += ego_speed * DT

        if has_lead:
            lead_pos += lead_speed * DT

        speeds.append(ego_speed)
        accels.append(accel_cmd)
        modes.append(mode)
        distances_out.append(distance)
        dist_errors_out.append(dist_error)
        ttcs_out.append(ttc_val)

    # Metrics
    rise_time = 999
    for i, (t, _, _) in enumerate(sensor_data):
        if speeds[i] >= 0.9 * SET_SPEED:
            rise_time = t
            break

    max_speed = max(speeds)
    overshoot = max(0, (max_speed - SET_SPEED) / SET_SPEED * 100.0)

    ss1 = [abs(SET_SPEED - speeds[i]) for i, (t, ls, _) in enumerate(sensor_data)
           if 25.0 <= t <= 29.9 and ls is None]
    ss2 = [abs(SET_SPEED - speeds[i]) for i, (t, ls, _) in enumerate(sensor_data)
           if 140.0 <= t <= 150.0 and ls is None]

    speed_ss = max(
        sum(ss1) / len(ss1) if ss1 else 999,
        sum(ss2) / len(ss2) if ss2 else 999
    )

    dist_ss = sum(distance_errors_ss) / len(distance_errors_ss) if distance_errors_ss else 999

    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'max_speed': max_speed,
        'speed_ss': speed_ss,
        'dist_ss': dist_ss,
        'min_dist': min_distance_sim,
        'speeds': speeds,
        'accels': accels,
        'modes': modes,
        'distances': distances_out,
        'dist_errors': dist_errors_out,
        'ttcs': ttcs_out,
    }


def passes(m):
    return (m['rise_time'] < 10.0 and
            m['overshoot'] < 5.0 and
            m['speed_ss'] < 0.5 and
            m['dist_ss'] < 2.0 and
            m['min_dist'] > 5.0)


def score(m):
    return (m['rise_time'] * 0.5 + m['overshoot'] * 2 + m['speed_ss'] * 10 +
            m['dist_ss'] * 5 - min(m['min_dist'], 20) * 0.2)


# Full sweep
print("Running sweep...")
best_score = float('inf')
best_params = None
best_metrics = None

sp_kps = [0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0, 5.0]
sp_kis = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]
sp_kds = [0.0, 0.1, 0.3, 0.5, 1.0]
dp_kps = [0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0]
dp_kis = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1]
dp_kds = [0.0, 0.1, 0.3, 0.5, 1.0]

count = 0
passing_count = 0
for sp_kp in sp_kps:
    for sp_ki in sp_kis:
        for sp_kd in sp_kds:
            for dp_kp in dp_kps:
                for dp_ki in dp_kis:
                    for dp_kd in dp_kds:
                        count += 1
                        m = simulate(sp_kp, sp_ki, sp_kd, dp_kp, dp_ki, dp_kd)
                        if passes(m):
                            passing_count += 1
                            s = score(m)
                            if s < best_score:
                                best_score = s
                                best_params = (sp_kp, sp_ki, sp_kd, dp_kp, dp_ki, dp_kd)
                                best_metrics = m

print(f"\nEvaluated {count} combinations, {passing_count} passed")
if best_params:
    print(f"BEST: sp=({best_params[0]},{best_params[1]},{best_params[2]}) dp=({best_params[3]},{best_params[4]},{best_params[5]})")
    print(f"  rise={best_metrics['rise_time']:.1f}s OS={best_metrics['overshoot']:.2f}%")
    print(f"  speed_ss={best_metrics['speed_ss']:.4f} dist_ss={best_metrics['dist_ss']:.3f} min_d={best_metrics['min_dist']:.1f}")

    result = {
        'pid_speed': {
            'kp': round(best_params[0], 4),
            'ki': round(best_params[1], 4),
            'kd': round(best_params[2], 4),
        },
        'pid_distance': {
            'kp': round(best_params[3], 4),
            'ki': round(best_params[4], 4),
            'kd': round(best_params[5], 4),
        },
    }
    with open('tuning_results.yaml', 'w') as f:
        yaml.dump(result, f, default_flow_style=False)
    print(f"\nSaved to tuning_results.yaml:")
    print(yaml.dump(result, default_flow_style=False))
else:
    print("No valid combination found!")
