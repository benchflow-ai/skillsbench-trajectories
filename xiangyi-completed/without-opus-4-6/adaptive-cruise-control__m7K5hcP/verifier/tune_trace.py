"""Trace simulation to understand distance behavior."""
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
INITIAL_GAP = 52.1
EMERGENCY_TTC = 3.0
MAX_ACCEL = 3.0
MAX_DECEL = -8.0

# Use sp=(1.0, 0.05, 0.0) dp=(0.5, 0.01, 0.0)
sp_kp, sp_ki, sp_kd = 1.0, 0.05, 0.0
dp_kp, dp_ki, dp_kd = 0.5, 0.01, 0.0

ego_speed = 0.0
ego_pos = 0.0
sp_integral = 0.0
sp_prev_error = None
dp_integral = 0.0
dp_prev_error = None
lead_pos = None

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
        dist_error = None
    else:
        closing = ego_speed - lead_speed
        ttc_val = (distance / closing) if (closing > 0 and distance > 0) else None
        desired_dist = MIN_DIST + TIME_HEADWAY * ego_speed
        dist_error = distance - desired_dist

        if ttc_val is not None and ttc_val < EMERGENCY_TTC:
            accel_cmd = MAX_DECEL
            dp_integral = 0.0
            dp_prev_error = None
            sp_integral = 0.0
            sp_prev_error = None
        else:
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

            speed_error = target_speed - ego_speed
            sp_p = sp_kp * speed_error
            sp_d = 0.0 if sp_prev_error is None else sp_kd * (speed_error - sp_prev_error) / DT
            sp_prev_error = speed_error
            sp_i = sp_ki * sp_integral
            raw = sp_p + sp_i + sp_d
            accel_cmd = max(MAX_DECEL, min(MAX_ACCEL, raw))
            if MAX_DECEL < raw < MAX_ACCEL:
                sp_integral += speed_error * DT

    accel_cmd = max(MAX_DECEL, min(MAX_ACCEL, accel_cmd))
    ego_speed = max(0.0, ego_speed + accel_cmd * DT)
    ego_pos += ego_speed * DT
    if has_lead:
        lead_pos += lead_speed * DT

    # Print at key times
    if has_lead and (30.0 <= t <= 35.0 or t % 10 < 0.05 or 128 < t < 132):
        desired = MIN_DIST + TIME_HEADWAY * ego_speed
        print(f"t={t:6.1f} ego_spd={ego_speed:5.2f} lead_spd={lead_speed:5.2f} "
              f"dist={distance:7.1f} desired={desired:6.1f} err={dist_error:7.1f} "
              f"accel={accel_cmd:5.2f} dp_int={dp_integral:8.2f}")

# Also check what lead_speed looks like over time
print("\n--- Lead speed profile ---")
lead_speeds = [(t, ls) for t, ls, _ in sensor_data if ls is not None]
# Bin by 10s intervals and compute mean
for start in range(30, 130, 10):
    speeds = [ls for t, ls in lead_speeds if start <= t < start + 10]
    print(f"t={start}-{start+10}: mean_lead_speed={sum(speeds)/len(speeds):.2f}")
