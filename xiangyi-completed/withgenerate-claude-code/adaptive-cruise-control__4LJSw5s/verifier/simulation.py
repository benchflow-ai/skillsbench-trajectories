"""
Vehicle Simulation Runner for ACC System

Reads sensor data, runs ACC controller, and produces simulation results.
"""

import csv
import math
import yaml
import pandas as pd
from acc_system import AdaptiveCruiseControl


class VehicleSimulator:
    """
    Simulates vehicle with ACC control over 150 seconds.
    
    Reads lead vehicle data from sensor_data.csv and computes ego vehicle
    response using ACC controller.
    """
    
    def __init__(self, config_file, sensor_data_file, tuning_file):
        """
        Initialize simulator.
        
        Args:
            config_file: Path to vehicle_params.yaml
            sensor_data_file: Path to sensor_data.csv
            tuning_file: Path to tuning_results.yaml
        """
        # Load configuration
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Load sensor data
        self.sensor_data = pd.read_csv(sensor_data_file)
        
        # Load PID gains from tuning results
        with open(tuning_file, 'r') as f:
            tuning = yaml.safe_load(f)
        
        # Initialize ACC system
        self.acc = AdaptiveCruiseControl(self.config)
        self.acc.set_pid_gains(
            tuning['pid_speed'],
            tuning['pid_distance']
        )
        
        # Simulation parameters
        self.dt = self.config['control']['control_period']
        self.accel_min = self.config['control']['accel_min']
        self.accel_max = self.config['control']['accel_max']
        
        # Results storage
        self.results = []
    
    def run(self):
        """
        Execute simulation over sensor data.
        
        Produces 1501 timesteps (t=0 to t=150s at 0.1s intervals).
        """
        # Start with zero speed
        ego_speed = 0.0
        
        print("Running ACC simulation...")
        
        for idx in range(len(self.sensor_data)):
            row = self.sensor_data.iloc[idx]
            time = row['time']
            
            # Get lead vehicle data
            lead_speed = row['lead_speed']
            distance = row['distance']
            
            # Handle NaN values
            if pd.isna(lead_speed):
                lead_speed = None
            if pd.isna(distance):
                distance = None
            
            # Compute ACC command
            accel_cmd, mode, distance_error = self.acc.compute(
                ego_speed, lead_speed, distance, self.dt
            )
            
            # Update vehicle dynamics
            ego_speed = self._update_vehicle(ego_speed, accel_cmd)
            
            # Compute TTC
            ttc = self._compute_ttc(ego_speed, lead_speed, distance)
            
            # Store result
            result = {
                'time': time,
                'ego_speed': ego_speed,
                'acceleration_cmd': accel_cmd,
                'mode': mode,
                'distance_error': distance_error if distance_error is not None else '',
                'distance': distance if distance is not None else '',
                'ttc': ttc if ttc is not None else ''
            }
            self.results.append(result)
            
            if (idx + 1) % 300 == 0:
                print(f"  {idx + 1}/{len(self.sensor_data)} timesteps completed")
        
        print(f"✓ Simulation complete: {len(self.results)} timesteps")
        return self.results
    
    def _update_vehicle(self, current_speed, accel_cmd):
        """
        Update vehicle speed using kinematics.
        
        Args:
            current_speed: Current speed (m/s)
            accel_cmd: Acceleration command (m/s²)
            
        Returns:
            float: New speed (m/s)
        """
        # Update velocity
        new_speed = current_speed + accel_cmd * self.dt
        
        # Clamp to valid range (can't have negative speed)
        new_speed = max(0.0, new_speed)
        
        return new_speed
    
    def _compute_ttc(self, ego_speed, lead_speed, distance):
        """
        Compute time-to-collision.
        
        Args:
            ego_speed: Current ego speed (m/s)
            lead_speed: Lead vehicle speed (m/s or None)
            distance: Gap to lead vehicle (m or None)
            
        Returns:
            float or None: TTC in seconds, or None if no lead vehicle
        """
        if lead_speed is None or distance is None:
            return None
        
        if math.isnan(lead_speed) or math.isnan(distance):
            return None
        
        relative_velocity = ego_speed - lead_speed
        
        if relative_velocity <= 0:
            return float('inf')  # Safe, not closing gap
        
        return distance / relative_velocity
    
    def save_results(self, output_file):
        """
        Save simulation results to CSV.
        
        Args:
            output_file: Path to output CSV file
        """
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['time', 'ego_speed', 'acceleration_cmd', 'mode',
                           'distance_error', 'distance', 'ttc']
            )
            writer.writeheader()
            writer.writerows(self.results)
        
        print(f"✓ Results saved to {output_file}")


def main():
    """Run simulation and save results."""
    simulator = VehicleSimulator(
        'vehicle_params.yaml',
        'sensor_data.csv',
        'tuning_results.yaml'
    )
    
    results = simulator.run()
    simulator.save_results('simulation_results.csv')
    
    # Print summary
    results_df = pd.DataFrame(results)
    print("\n=== Simulation Summary ===")
    print(f"Final ego speed: {results_df['ego_speed'].iloc[-1]:.2f} m/s")
    print(f"Max ego speed: {results_df['ego_speed'].max():.2f} m/s")
    print(f"Min ego speed: {results_df['ego_speed'].min():.2f} m/s")
    print(f"Max acceleration: {results_df['acceleration_cmd'].max():.2f} m/s²")
    print(f"Min acceleration: {results_df['acceleration_cmd'].min():.2f} m/s²")
    
    # Mode distribution
    mode_counts = results_df['mode'].value_counts()
    print("\nMode distribution:")
    for mode, count in mode_counts.items():
        pct = (count / len(results_df)) * 100
        print(f"  {mode}: {count} ({pct:.1f}%)")


if __name__ == '__main__':
    main()
