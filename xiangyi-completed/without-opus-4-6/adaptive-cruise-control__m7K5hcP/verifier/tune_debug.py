"""Debug tuning - check what metrics we get."""
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


def simulate(sp_kp, sp_ki, sp_kd, dp_kp, dp_ki, dp_kd):
    ego_speed = 0.0
    sp_integral = 0.0
    sp_prev_error = None
    dp_integral = 0.0
    dp_prev_error = None

    speeds = []
    min_dist_seen = float('inf')
    distance_errors_follow = []

    for i, (t, lead_speed, distance) in enumerate(sensor_data):
        if lead_speed is None:
            speed_error = SET_SPEED - ego_speed
            sp_integral += speed_error * DT
            if sp_prev_error is None:
                sp_d = 0.0
            else:
                sp_d = sp_kd * (speed_error - sp_prev_error) / DT
            sp_prev_error = speed_error
            accel_cmd = sp_kp * speed_error + sp_ki * sp_integral + sp_d

            dp_integral = 0.0
            dp_prev_error = None
        else:
            closing = ego_speed - lead_speed
            ttc = (distance / closing) if (closing > 0 and distance > 0) else None

            desired_dist = MIN_DIST + TIME_HEADWAY * ego_speed
            dist_error = distance - desired_dist

            if ttc is not None and ttc < EMERGENCY_TTC:
                accel_cmd = MAX_DECEL
            else:
                dp_integral += dist_error * DT
                if dp_prev_error is None:
                    dp_d = 0.0
                else:
                    dp_d = dp_kd * (dist_error - dp_prev_error) / DT
                dp_prev_error = dist_error
                dist_accel = dp_kp * dist_error + dp_ki * dp_integral + dp_d

                target_speed = min(lead_speed, SET_SPEED)
                speed_error = target_speed - ego_speed
                sp_integral += speed_error * DT
                if sp_prev_error is None:
                    sp_d = 0.0
                else:
                    sp_d = sp_kd * (speed_error - sp_prev_error) / DT
                sp_prev_error = speed_error
                speed_accel = sp_kp * speed_error + sp_ki * sp_integral + sp_d

                if dist_error < 0:
                    accel_cmd = min(dist_accel, speed_accel)
                else:
                    accel_cmd = speed_accel

            if distance is not None:
                min_dist_seen = min(min_dist_seen, distance)
                if t > 40.0 and t < 129.0:
                    distance_errors_follow.append(dist_error)

        accel_cmd = max(MAX_DECEL, min(MAX_ACCEL, accel_cmd))
        ego_speed = max(0.0, ego_speed + accel_cmd * DT)
        speeds.append(ego_speed)

    # Rise time to 27 m/s (90% of 30)
    rise_time = 999
    for i, (t, _, _) in enumerate(sensor_data):
        if speeds[i] >= 27.0:
            rise_time = t
            break

    max_speed = max(speeds)
    overshoot = (max_speed - SET_SPEED) / SET_SPEED * 100.0 if max_speed > SET_SPEED else 0.0

    # Speed SS error — check cruise phases
    # Phase 1: t=25-29.9 (before lead appears)
    ss1 = [abs(SET_SPEED - speeds[i]) for i, (t, ls, _) in enumerate(sensor_data) if 25.0 <= t <= 29.9 and ls is None]
    # Phase 2: t=140-150 (after lead disappears)
    ss2 = [abs(SET_SPEED - speeds[i]) for i, (t, ls, _) in enumerate(sensor_data) if 140.0 <= t <= 150.0 and ls is None]

    speed_ss1 = sum(ss1) / len(ss1) if ss1 else 999
    speed_ss2 = sum(ss2) / len(ss2) if ss2 else 999

    # Distance SS error
    abs_de = [abs(e) for e in distance_errors_follow]
    dist_ss = sum(abs_de) / len(abs_de) if abs_de else 999

    return {
        'rise_time': rise_time,
        'overshoot': overshoot,
        'max_speed': max_speed,
        'speed_ss1': speed_ss1,
        'speed_ss2': speed_ss2,
        'dist_ss': dist_ss,
        'min_dist': min_dist_seen,
    }


# Test a few parameter sets
tests = [
    (1.0, 0.05, 0.1, 0.3, 0.01, 0.1),
    (2.0, 0.1, 0.0, 0.5, 0.05, 0.0),
    (1.5, 0.05, 0.0, 0.3, 0.01, 0.0),
    (3.0, 0.1, 0.0, 0.5, 0.0, 0.0),
    (1.0, 0.01, 0.0, 0.3, 0.0, 0.0),
    (0.5, 0.01, 0.0, 0.2, 0.0, 0.0),
    (2.0, 0.05, 0.5, 0.5, 0.01, 0.5),
]

for params in tests:
    m = simulate(*params)
    print(f"sp=({params[0]},{params[1]},{params[2]}) dp=({params[3]},{params[4]},{params[5]})")
    print(f"  rise={m['rise_time']:.1f}s overshoot={m['overshoot']:.2f}% max_spd={m['max_speed']:.2f}")
    print(f"  ss1={m['speed_ss1']:.3f} ss2={m['speed_ss2']:.3f} dist_ss={m['dist_ss']:.3f} min_d={m['min_dist']:.1f}")
    print()
