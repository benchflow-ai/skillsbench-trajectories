import csv
import yaml

from acc_system import AdaptiveCruiseControl


def _float_or_none(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == '':
        return None
    return float(value)


def _format(value):
    if value is None:
        return ''
    if value == float('inf'):
        return ''
    return f"{value:.3f}"


def run_simulation(
    sensor_path='sensor_data.csv',
    params_path='vehicle_params.yaml',
    tuning_path='tuning_results.yaml',
    output_path='simulation_results.csv',
):
    with open(params_path, 'r') as f:
        config = yaml.safe_load(f)

    with open(tuning_path, 'r') as f:
        tuning = yaml.safe_load(f)

    if tuning:
        config['pid_speed'] = tuning.get('pid_speed', config.get('pid_speed', {}))
        config['pid_distance'] = tuning.get('pid_distance', config.get('pid_distance', {}))

    acc = AdaptiveCruiseControl(config)

    ego_speed = 0.0
    ego_pos = 0.0
    lead_pos = None
    prev_time = None

    results = []

    with open(sensor_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time = float(row['time'])
            if prev_time is None:
                dt = config.get('simulation', {}).get('dt', 0.1)
            else:
                dt = time - prev_time
            prev_time = time

            lead_speed = _float_or_none(row.get('lead_speed'))
            lead_distance_meas = _float_or_none(row.get('distance'))

            if lead_speed is None or lead_distance_meas is None:
                lead_speed = None
                distance = None
                lead_pos = None
            else:
                if lead_pos is None:
                    lead_pos = ego_pos + lead_distance_meas
                else:
                    lead_pos += lead_speed * dt
                distance = lead_pos - ego_pos

            accel_cmd, mode, distance_error = acc.compute(
                ego_speed=ego_speed,
                lead_speed=lead_speed,
                distance=distance,
                dt=dt,
            )

            # Update ego state
            ego_speed = max(0.0, ego_speed + accel_cmd * dt)
            ego_pos += ego_speed * dt

            # TTC for reporting
            if lead_speed is not None and distance is not None:
                rel_speed = ego_speed - lead_speed
                if rel_speed > 1e-3 and distance > 0.0:
                    ttc = distance / rel_speed
                else:
                    ttc = None
            else:
                ttc = None

            results.append([
                f"{time:.1f}",
                _format(ego_speed),
                _format(accel_cmd),
                mode,
                _format(distance_error),
                _format(distance),
                _format(ttc),
            ])

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'time',
            'ego_speed',
            'acceleration_cmd',
            'mode',
            'distance_error',
            'distance',
            'ttc',
        ])
        writer.writerows(results)


if __name__ == '__main__':
    run_simulation()
