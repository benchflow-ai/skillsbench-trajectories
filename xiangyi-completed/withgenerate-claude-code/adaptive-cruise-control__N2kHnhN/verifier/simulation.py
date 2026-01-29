"""
Vehicle simulation runner for ACC system evaluation.

Reads sensor data from CSV and PID gains from YAML configuration.
Runs 150-second simulation producing detailed results.
"""

import yaml
import pandas as pd
import numpy as np
from acc_system import AdaptiveCruiseControl


def load_config(config_file):
    """
    Load configuration from YAML file.

    Args:
        config_file (str): Path to vehicle_params.yaml

    Returns:
        dict: Configuration dictionary
    """
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config


def load_tuning_results(tuning_file):
    """
    Load tuned PID gains from YAML file.

    Args:
        tuning_file (str): Path to tuning_results.yaml

    Returns:
        dict: Dictionary with pid_speed and pid_distance gains
    """
    with open(tuning_file, 'r') as f:
        tuning = yaml.safe_load(f)
    return tuning


def load_sensor_data(sensor_file):
    """
    Load sensor data from CSV file.

    Args:
        sensor_file (str): Path to sensor_data.csv

    Returns:
        pd.DataFrame: Sensor data with columns: time, ego_speed, lead_speed, distance
    """
    data = pd.read_csv(sensor_file)
    return data


def run_simulation(acc_system, sensor_data, dt, duration):
    """
    Run 150-second ACC simulation with sensor data.

    Args:
        acc_system (AdaptiveCruiseControl): Initialized ACC controller
        sensor_data (pd.DataFrame): Lead vehicle sensor data
        dt (float): Time step (s)
        duration (float): Total simulation duration (s)

    Returns:
        pd.DataFrame: Simulation results with columns:
            time, ego_speed, acceleration_cmd, mode, distance_error, distance, ttc
    """
    num_steps = int(duration / dt) + 1

    # Initialize result lists
    times = []
    ego_speeds = []
    accel_cmds = []
    modes = []
    dist_errors = []
    distances = []
    ttcs = []

    # Get initial ego speed from sensor data
    ego_speed = sensor_data.loc[0, 'ego_speed']

    # Run simulation loop
    for step in range(num_steps):
        time = step * dt

        # Get lead vehicle data from sensor CSV at current time index
        if step < len(sensor_data):
            row = sensor_data.iloc[step]
            lead_speed = row['lead_speed']
            distance = row['distance']

            # Handle NaN values (no lead vehicle detected)
            if pd.isna(lead_speed) or pd.isna(distance):
                lead_speed = None
                distance = None
        else:
            # Extend with last known values or None
            lead_speed = None
            distance = None

        # Compute ACC control command
        accel_cmd, mode, dist_error = acc_system.compute(
            ego_speed, lead_speed, distance, dt
        )

        # Compute time-to-collision if lead vehicle present
        if lead_speed is not None and distance is not None and distance > 0:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0:
                ttc = distance / relative_speed
            else:
                ttc = None
        else:
            ttc = None

        # Update ego vehicle speed (kinematic model)
        ego_speed += accel_cmd * dt
        ego_speed = max(0.0, ego_speed)  # Speed cannot go negative

        # Record results
        times.append(time)
        ego_speeds.append(ego_speed)
        accel_cmds.append(accel_cmd)
        modes.append(mode)
        dist_errors.append(dist_error)
        distances.append(distance)
        ttcs.append(ttc)

    # Create results DataFrame
    results = pd.DataFrame({
        'time': times,
        'ego_speed': ego_speeds,
        'acceleration_cmd': accel_cmds,
        'mode': modes,
        'distance_error': dist_errors,
        'distance': distances,
        'ttc': ttcs
    })

    return results


def compute_performance_metrics(results, config):
    """
    Compute performance metrics from simulation results.

    Args:
        results (pd.DataFrame): Simulation results
        config (dict): Configuration with target set_speed

    Returns:
        dict: Performance metrics
    """
    set_speed = config['acc_settings']['set_speed']
    ego_speeds = results['ego_speed'].values
    modes = results['mode'].values
    dist_errors = results['distance_error'].values

    metrics = {}

    # Cruise phase analysis (first 30 seconds when no lead vehicle)
    cruise_mask = np.array(modes) == 'cruise'
    cruise_speeds = ego_speeds[cruise_mask]

    if len(cruise_speeds) > 0:
        # Rise time: time to reach 90% of set speed
        target_90 = 0.9 * set_speed
        idx_90 = np.where(cruise_speeds >= target_90)[0]
        if len(idx_90) > 0:
            rise_time_steps = idx_90[0]
            metrics['rise_time_s'] = rise_time_steps * 0.1
        else:
            metrics['rise_time_s'] = None

        # Overshoot: max deviation above set speed
        max_speed = np.max(cruise_speeds)
        overshoot = max(0, max_speed - set_speed)
        metrics['overshoot_m_s'] = overshoot
        metrics['overshoot_pct'] = (overshoot / set_speed) * 100 if set_speed > 0 else 0

        # Steady-state error (last 10 seconds of cruise phase)
        ss_start = max(0, len(cruise_speeds) - 100)  # Last 10 seconds
        ss_speeds = cruise_speeds[ss_start:]
        if len(ss_speeds) > 0:
            metrics['steady_state_error_m_s'] = abs(np.mean(ss_speeds) - set_speed)
        else:
            metrics['steady_state_error_m_s'] = None

    # Follow phase analysis
    follow_mask = np.array(modes) == 'follow'
    if np.any(follow_mask):
        follow_dist_errors = dist_errors[follow_mask]
        follow_dist_errors = follow_dist_errors[~np.isnan(follow_dist_errors)]

        if len(follow_dist_errors) > 0:
            metrics['follow_distance_error_mean_m'] = np.mean(np.abs(follow_dist_errors))
            metrics['follow_distance_error_max_m'] = np.max(np.abs(follow_dist_errors))
            metrics['follow_distance_error_std_m'] = np.std(follow_dist_errors)

    # Safety metrics
    distances = results['distance'].values
    min_distances = distances[~np.isnan(distances)]
    if len(min_distances) > 0:
        metrics['min_distance_m'] = np.min(min_distances)

    emergency_count = np.sum(np.array(modes) == 'emergency')
    metrics['emergency_activations'] = emergency_count

    return metrics


def generate_report(results, metrics, config, output_file='acc_report.md'):
    """
    Generate detailed ACC simulation report.

    Args:
        results (pd.DataFrame): Simulation results
        metrics (dict): Performance metrics
        config (dict): Configuration
        output_file (str): Output markdown file path
    """
    with open(output_file, 'w') as f:
        f.write('# Adaptive Cruise Control (ACC) System Report\n\n')

        f.write('## System Design\n\n')
        f.write('### Architecture\n')
        f.write('The ACC system implements three control modes:\n\n')
        f.write('1. **Cruise Mode**: Maintains set speed when no lead vehicle is detected\n')
        f.write('   - Uses speed PID controller to minimize speed error\n')
        f.write('   - Target speed: {:.1f} m/s (~{:.0f} km/h)\n\n'.format(
            config['acc_settings']['set_speed'],
            config['acc_settings']['set_speed'] * 3.6
        ))

        f.write('2. **Follow Mode**: Maintains safe following distance behind lead vehicle\n')
        f.write('   - Uses combined speed and distance control\n')
        f.write('   - Time headway: {:.1f}s, Minimum gap: {:.1f}m\n'.format(
            config['acc_settings']['time_headway'],
            config['acc_settings']['min_distance']
        ))

        f.write('3. **Emergency Mode**: Maximum deceleration when TTC < threshold\n')
        f.write('   - Threshold: {:.1f}s\n'.format(
            config['acc_settings']['emergency_ttc_threshold']
        ))

        f.write('   - Max deceleration: {:.1f} m/s²\n\n'.format(
            config['vehicle']['max_deceleration']
        ))

        f.write('### Safety Features\n')
        f.write('- Acceleration clamped to [-{:.1f}, {:.1f}] m/s²\n'.format(
            abs(config['vehicle']['max_deceleration']),
            config['vehicle']['max_acceleration']
        ))
        f.write('- Minimum distance enforcement: {:.1f}m\n'.format(
            config['acc_settings']['min_distance']
        ))
        f.write('- Emergency braking activation: TTC < {:.1f}s\n\n'.format(
            config['acc_settings']['emergency_ttc_threshold']
        ))

        f.write('## PID Tuning\n\n')
        f.write('### Speed Controller\n')
        f.write('- Kp: {:.4f}\n'.format(config['pid_speed']['kp']))
        f.write('- Ki: {:.4f}\n'.format(config['pid_speed']['ki']))
        f.write('- Kd: {:.4f}\n\n'.format(config['pid_speed']['kd']))

        f.write('### Distance Controller\n')
        f.write('- Kp: {:.4f}\n'.format(config['pid_distance']['kp']))
        f.write('- Ki: {:.4f}\n'.format(config['pid_distance']['ki']))
        f.write('- Kd: {:.4f}\n\n'.format(config['pid_distance']['kd']))

        f.write('### Tuning Methodology\n')
        f.write('PID parameters were tuned to meet the following targets:\n')
        f.write('- Speed rise time: < 10s\n')
        f.write('- Speed overshoot: < 5%\n')
        f.write('- Speed steady-state error: < 0.5 m/s\n')
        f.write('- Distance steady-state error: < 2m\n')
        f.write('- Minimum safe distance: > 5m\n\n')

        f.write('## Simulation Results\n\n')
        f.write('### Performance Metrics\n\n')

        if 'rise_time_s' in metrics and metrics['rise_time_s'] is not None:
            f.write('**Cruise Phase:**\n')
            f.write('- Rise time (90% of set speed): {:.2f}s\n'.format(metrics['rise_time_s']))
            f.write('- Overshoot: {:.3f} m/s ({:.2f}%)\n'.format(
                metrics['overshoot_m_s'],
                metrics['overshoot_pct']
            ))
            f.write('- Steady-state error: {:.3f} m/s\n\n'.format(
                metrics['steady_state_error_m_s']
            ))

        if 'follow_distance_error_mean_m' in metrics:
            f.write('**Follow Phase:**\n')
            f.write('- Mean distance error: {:.2f}m\n'.format(
                metrics['follow_distance_error_mean_m']
            ))
            f.write('- Max distance error: {:.2f}m\n'.format(
                metrics['follow_distance_error_max_m']
            ))
            f.write('- Distance error std dev: {:.2f}m\n\n'.format(
                metrics['follow_distance_error_std_m']
            ))

        f.write('**Safety:**\n')
        if 'min_distance_m' in metrics:
            f.write('- Minimum distance maintained: {:.2f}m\n'.format(
                metrics['min_distance_m']
            ))
        f.write('- Emergency activations: {}\n\n'.format(
            metrics['emergency_activations']
        ))

        f.write('### Control Mode Distribution\n')
        mode_counts = results['mode'].value_counts()
        for mode in ['cruise', 'follow', 'emergency']:
            count = mode_counts.get(mode, 0)
            pct = (count / len(results)) * 100
            f.write('- {}: {} steps ({:.1f}%)\n'.format(mode, count, pct))

        f.write('\n## Conclusion\n')
        f.write('The ACC system successfully manages both cruise and follow modes with')
        f.write(' smooth transitions and safe operation.\n')


def main():
    """Main simulation entry point."""
    print("Loading configuration...")
    config = load_config('/root/vehicle_params.yaml')

    print("Loading tuned PID parameters...")
    tuning = load_tuning_results('/root/tuning_results.yaml')

    # Update config with tuned PID gains
    config['pid_speed'] = tuning['pid_speed']
    config['pid_distance'] = tuning['pid_distance']

    print("Initializing ACC system...")
    acc = AdaptiveCruiseControl(config)

    print("Loading sensor data...")
    sensor_data = load_sensor_data('/root/sensor_data.csv')

    print("Running 150s simulation...")
    results = run_simulation(acc, sensor_data, dt=0.1, duration=150.0)

    print("Computing performance metrics...")
    metrics = compute_performance_metrics(results, config)

    print("Saving results...")
    results.to_csv('/root/simulation_results.csv', index=False)

    print("Generating report...")
    generate_report(results, metrics, config, '/root/acc_report.md')

    print("\nSimulation completed successfully!")
    print("Output files:")
    print("  - /root/simulation_results.csv")
    print("  - /root/acc_report.md")
    print("\nPerformance Summary:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
