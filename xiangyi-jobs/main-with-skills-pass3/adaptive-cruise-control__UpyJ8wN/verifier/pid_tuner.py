"""PID parameter tuning for Adaptive Cruise Control."""

import csv
import yaml
import numpy as np
from acc_system import AdaptiveCruiseControl


class PIDTuner:
    """Tunes PID parameters to meet performance targets."""

    def __init__(self, config_path, sensor_data_path):
        """Initialize tuner.

        Args:
            config_path (str): Path to vehicle_params.yaml
            sensor_data_path (str): Path to sensor_data.csv
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.sensor_data = self._load_sensor_data(sensor_data_path)
        self.dt = self.config['simulation']['dt']

    def _load_sensor_data(self, sensor_data_path):
        """Load sensor data from CSV."""
        data = []
        with open(sensor_data_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = {
                    'time': float(row['time']),
                    'ego_speed': float(row['ego_speed']),
                    'lead_speed': float(row['lead_speed']) if row['lead_speed'] else None,
                    'distance': float(row['distance']) if row['distance'] else None,
                }
                data.append(entry)
        return data

    def evaluate(self, pid_speed_gains, pid_distance_gains):
        """Evaluate PID gains against performance targets.

        Args:
            pid_speed_gains (dict): Speed PID gains {kp, ki, kd}
            pid_distance_gains (dict): Distance PID gains {kp, ki, kd}

        Returns:
            dict: Metrics including rise_time, overshoot, steady_state_error, etc.
        """
        config = self.config.copy()
        config['pid_speed'] = pid_speed_gains
        config['pid_distance'] = pid_distance_gains

        acc = AdaptiveCruiseControl(config)

        # Simulate
        speeds = []
        distances = []
        modes = []
        times = []
        distance_errors = []

        for sensor_row in self.sensor_data:
            time = sensor_row['time']
            ego_speed = sensor_row['ego_speed']
            lead_speed = sensor_row['lead_speed']
            distance = sensor_row['distance']

            accel_cmd, mode, distance_error = acc.compute(
                ego_speed, lead_speed, distance, self.dt
            )

            speeds.append(ego_speed)
            distances.append(distance)
            modes.append(mode)
            times.append(time)
            distance_errors.append(distance_error if distance_error is not None else 0)

        # Calculate metrics
        speeds = np.array(speeds)
        distances = np.array(distances)
        distance_errors = np.array(distance_errors)
        set_speed = self.config['acc_settings']['set_speed']

        # Speed metrics (during cruise mode)
        cruise_mask = np.array([m == 'cruise' for m in modes])
        cruise_speeds = speeds[cruise_mask]

        if len(cruise_speeds) > 0:
            # Rise time: time to reach 90% of set speed
            rise_time = self._compute_rise_time(cruise_speeds, set_speed * 0.9)
            # Overshoot: max speed - target speed
            overshoot = np.max(cruise_speeds) - set_speed
            overshoot_pct = (overshoot / set_speed) * 100 if set_speed > 0 else 0
            # Steady state error (last 30s in cruise mode)
            final_cruise = cruise_speeds[-300:] if len(cruise_speeds) > 300 else cruise_speeds
            speed_sse = np.abs(np.mean(final_cruise) - set_speed)
        else:
            rise_time = float('inf')
            overshoot_pct = float('inf')
            speed_sse = float('inf')

        # Distance metrics (during follow mode)
        follow_mask = np.array([m == 'follow' for m in modes])
        follow_distances = distances[follow_mask]
        follow_errors = distance_errors[follow_mask]

        if len(follow_distances) > 0:
            min_distance = np.min(follow_distances)
            final_follow = follow_errors[-100:] if len(follow_errors) > 100 else follow_errors
            distance_sse = np.mean(np.abs(final_follow))
        else:
            min_distance = float('inf')
            distance_sse = float('inf')

        return {
            'rise_time': rise_time,
            'overshoot_pct': overshoot_pct,
            'speed_sse': speed_sse,
            'distance_sse': distance_sse,
            'min_distance': min_distance,
            'cruise_samples': len(cruise_speeds),
            'follow_samples': len(follow_distances),
        }

    def _compute_rise_time(self, speeds, target):
        """Compute time to reach target speed."""
        for i, speed in enumerate(speeds):
            if speed >= target:
                return i * self.dt
        return float('inf')

    def tune(self):
        """Tune PID parameters using coarse grid search.

        Returns:
            dict: Best gains found and metrics
        """
        best_score = float('inf')
        best_params = None

        # Coarse grid search
        kp_speed_range = np.linspace(1.0, 6.0, 6)
        ki_speed_range = np.linspace(0.01, 1.0, 5)
        kd_speed_range = np.linspace(0.0, 1.5, 4)

        kp_distance_range = np.linspace(1.0, 6.0, 6)
        ki_distance_range = np.linspace(0.01, 1.0, 5)
        kd_distance_range = np.linspace(0.0, 1.5, 4)

        print("Starting PID tuning...")
        iterations = 0
        total = (len(kp_speed_range) * len(ki_speed_range) * len(kd_speed_range) *
                 len(kp_distance_range) * len(ki_distance_range) * len(kd_distance_range))

        for kp_s in kp_speed_range:
            for ki_s in ki_speed_range:
                for kd_s in kd_speed_range:
                    pid_speed = {'kp': kp_s, 'ki': ki_s, 'kd': kd_s}

                    for kp_d in kp_distance_range:
                        for ki_d in ki_distance_range:
                            for kd_d in kd_distance_range:
                                pid_distance = {'kp': kp_d, 'ki': ki_d, 'kd': kd_d}

                                metrics = self.evaluate(pid_speed, pid_distance)

                                # Score: weighted sum of metrics
                                score = (
                                    0.3 * min(metrics['rise_time'] / 10.0, 1.0) +
                                    0.3 * (metrics['overshoot_pct'] / 5.0) +
                                    0.2 * (metrics['speed_sse'] / 0.5) +
                                    0.1 * (metrics['distance_sse'] / 2.0) +
                                    0.1 * max(0, (5.0 - metrics['min_distance']) / 5.0)
                                )

                                if score < best_score:
                                    best_score = score
                                    best_params = {
                                        'pid_speed': pid_speed,
                                        'pid_distance': pid_distance,
                                        'metrics': metrics,
                                        'score': score,
                                    }

                                iterations += 1
                                if iterations % 100 == 0:
                                    print(f"  Progress: {iterations}/{total}")

        print(f"\nTuning complete. Best score: {best_score:.4f}")
        return best_params


def main():
    """Run PID tuning and save results."""
    tuner = PIDTuner('/root/vehicle_params.yaml', '/root/sensor_data.csv')
    results = tuner.tune()

    # Convert numpy values to Python floats for clean YAML
    tuning_results = {
        'pid_speed': {
            'kp': float(results['pid_speed']['kp']),
            'ki': float(results['pid_speed']['ki']),
            'kd': float(results['pid_speed']['kd']),
        },
        'pid_distance': {
            'kp': float(results['pid_distance']['kp']),
            'ki': float(results['pid_distance']['ki']),
            'kd': float(results['pid_distance']['kd']),
        },
        'metrics': {
            'rise_time': float(results['metrics']['rise_time']),
            'overshoot_pct': float(results['metrics']['overshoot_pct']),
            'speed_sse': float(results['metrics']['speed_sse']),
            'distance_sse': float(results['metrics']['distance_sse']),
            'min_distance': float(results['metrics']['min_distance']),
            'cruise_samples': int(results['metrics']['cruise_samples']),
            'follow_samples': int(results['metrics']['follow_samples']),
        },
        'score': float(results['score']),
    }

    with open('/root/tuning_results.yaml', 'w') as f:
        yaml.dump(tuning_results, f, default_flow_style=False)

    print("\nTuning Results:")
    print(f"Speed PID: {results['pid_speed']}")
    print(f"Distance PID: {results['pid_distance']}")
    print(f"Metrics: {results['metrics']}")


if __name__ == '__main__':
    main()
