"""Adaptive Cruise Control simulation."""

import csv
import yaml
from acc_system import AdaptiveCruiseControl


class ACCSimulation:
    """Runs Adaptive Cruise Control simulation with sensor data."""

    def __init__(self, config_path, sensor_data_path, tuning_results_path):
        """Initialize simulation.

        Args:
            config_path (str): Path to vehicle_params.yaml
            sensor_data_path (str): Path to sensor_data.csv
            tuning_results_path (str): Path to tuning_results.yaml with PID gains
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Load tuning results to override PID gains
        with open(tuning_results_path, 'r') as f:
            tuning_results = yaml.safe_load(f)
            self.config['pid_speed'] = tuning_results['pid_speed']
            self.config['pid_distance'] = tuning_results['pid_distance']

        # Load sensor data
        self.sensor_data = self._load_sensor_data(sensor_data_path)

        # Initialize ACC system
        self.acc = AdaptiveCruiseControl(self.config)

        # Simulation parameters
        self.dt = self.config['simulation']['dt']

    def _load_sensor_data(self, sensor_data_path):
        """Load sensor data from CSV.

        Args:
            sensor_data_path (str): Path to sensor_data.csv

        Returns:
            list: List of dicts with keys: time, ego_speed, lead_speed, distance
        """
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

    def run(self):
        """Run the simulation.

        Returns:
            list: Simulation results with columns:
                time, ego_speed, acceleration_cmd, mode, distance_error, distance, ttc
        """
        results = []

        for i, sensor_row in enumerate(self.sensor_data):
            time = sensor_row['time']
            ego_speed = sensor_row['ego_speed']
            lead_speed = sensor_row['lead_speed']
            distance = sensor_row['distance']

            # Compute ACC command
            accel_cmd, mode, distance_error = self.acc.compute(
                ego_speed, lead_speed, distance, self.dt
            )

            # Compute TTC if lead vehicle present
            ttc = None
            if lead_speed is not None and distance is not None:
                relative_speed = ego_speed - lead_speed
                if relative_speed > 0 and distance > 0:
                    ttc = distance / relative_speed

            # Record result
            result = {
                'time': time,
                'ego_speed': ego_speed,
                'acceleration_cmd': accel_cmd,
                'mode': mode,
                'distance_error': distance_error,
                'distance': distance,
                'ttc': ttc,
            }
            results.append(result)

        return results

    def save_results(self, results, output_path):
        """Save simulation results to CSV.

        Args:
            results (list): Simulation results from run()
            output_path (str): Path to output CSV file
        """
        with open(output_path, 'w', newline='') as f:
            fieldnames = ['time', 'ego_speed', 'acceleration_cmd', 'mode',
                         'distance_error', 'distance', 'ttc']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in results:
                row = {}
                for field in fieldnames:
                    value = result[field]
                    # Write empty string for None values
                    row[field] = '' if value is None else value
                writer.writerow(row)
