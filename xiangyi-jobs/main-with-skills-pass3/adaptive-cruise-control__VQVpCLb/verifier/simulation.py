import yaml
import pandas as pd
import math
from acc_system import AdaptiveCruiseControl

def rise_time(times, values, target):
    """Calculate rise time (10% to 90% of target)."""
    t10 = t90 = None
    
    for t, v in zip(times, values):
        if t10 is None and v >= 0.1 * target:
            t10 = t
        if t90 is None and v >= 0.9 * target:
            t90 = t
            break
    
    if t10 is not None and t90 is not None:
        return t90 - t10
    return None

def overshoot_percent(values, target):
    """Calculate overshoot percentage."""
    max_val = max(values)
    if max_val <= target:
        return 0.0
    return ((max_val - target) / target) * 100

def steady_state_error(values, target, final_fraction=0.1):
    """Calculate steady-state error using final portion of data."""
    n = len(values)
    start = int(n * (1 - final_fraction))
    if start >= n:
        start = max(0, n - 1)
    final_avg = sum(values[start:]) / len(values[start:])
    return abs(target - final_avg)

def load_config(filepath):
    """Load YAML configuration file."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)

def load_pid_gains(filepath):
    """Load PID gains from tuning results."""
    try:
        with open(filepath, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None

def run_simulation(config, pid_gains=None):
    """Run the ACC simulation.
    
    Args:
        config: Configuration dict from vehicle_params.yaml
        pid_gains: Optional PID gains from tuning_results.yaml
        
    Returns:
        List of result dictionaries
    """
    # Update config with tuned PID gains if provided
    if pid_gains:
        if 'pid_speed' in pid_gains:
            config['pid_speed'] = pid_gains['pid_speed']
        if 'pid_distance' in pid_gains:
            config['pid_distance'] = pid_gains['pid_distance']
    
    # Initialize ACC system
    acc = AdaptiveCruiseControl(config)
    dt = config['simulation']['dt']
    
    # Load sensor data
    sensor_df = pd.read_csv('sensor_data.csv')
    
    # Initialize simulation state
    ego_speed = 0.0
    results = []
    
    # Run simulation for each timestep
    for idx, row in sensor_df.iterrows():
        time = row['time']
        lead_speed = row['lead_speed'] if pd.notna(row['lead_speed']) else None
        distance = row['distance'] if pd.notna(row['distance']) else None
        
        # Compute ACC command
        accel_cmd, mode, distance_error = acc.compute(ego_speed, lead_speed, distance, dt)
        
        # Update ego speed using kinematic equation
        new_speed = ego_speed + accel_cmd * dt
        new_speed = max(0.0, new_speed)  # Speed cannot be negative
        
        # Calculate TTC if lead vehicle present
        ttc = None
        if lead_speed is not None and distance is not None:
            relative_speed = ego_speed - lead_speed
            if relative_speed > 0 and distance > 0:
                ttc = distance / relative_speed
        
        # Store result
        result = {
            'time': time,
            'ego_speed': new_speed,
            'acceleration_cmd': accel_cmd,
            'mode': mode,
            'distance_error': distance_error,
            'distance': distance,
            'ttc': ttc
        }
        results.append(result)
        
        # Update state for next iteration
        ego_speed = new_speed
    
    return results

def main():
    """Main simulation entry point."""
    print("Loading configuration...")
    config = load_config('vehicle_params.yaml')
    
    print("Checking for tuned PID gains...")
    pid_gains = load_pid_gains('tuning_results.yaml')
    if pid_gains:
        print(f"Loaded tuned PID gains from tuning_results.yaml")
    else:
        print("Using default PID gains from vehicle_params.yaml")
    
    print("Running simulation...")
    results = run_simulation(config, pid_gains)
    
    # Write results to CSV
    print(f"Writing {len(results)} results to simulation_results.csv...")
    df_results = pd.DataFrame(results)
    df_results.to_csv('simulation_results.csv', index=False)
    
    # Calculate metrics
    print("\n=== Simulation Results ===")
    print(f"Total timesteps: {len(results)}")
    print(f"Simulation duration: {results[-1]['time']} seconds")
    
    # Speed metrics
    speeds = [r['ego_speed'] for r in results]
    set_speed = config['acc_settings']['set_speed']
    
    # Calculate rise time (from start of simulation)
    rt = rise_time([r['time'] for r in results], speeds, set_speed)
    print(f"\nSpeed Control:")
    print(f"  Target speed: {set_speed} m/s")
    print(f"  Rise time (10%-90%): {rt:.2f}s" if rt else "  Rise time: N/A")
    print(f"  Overshoot: {overshoot_percent(speeds, set_speed):.2f}%")
    print(f"  Steady-state error: {steady_state_error(speeds, set_speed):.3f} m/s")
    
    # Distance metrics (only during follow mode)
    follow_results = [r for r in results if r['mode'] == 'follow']
    if follow_results:
        distances = [r['distance'] for r in follow_results]
        distance_errors = [r['distance_error'] for r in follow_results if r['distance_error'] is not None]
        
        print(f"\nDistance Control (Follow Mode):")
        print(f"  Follow mode duration: {len(follow_results) * config['simulation']['dt']:.1f}s")
        if distance_errors:
            print(f"  Distance error (steady-state): {abs(distance_errors[-1]):.3f} m")
        print(f"  Minimum distance: {min(distances):.2f} m")
        print(f"  Maximum distance: {max(distances):.2f} m")
    
    # Safety metrics
    ttc_values = [r['ttc'] for r in results if r['ttc'] is not None]
    if ttc_values:
        min_ttc = min(ttc_values)
        print(f"\nSafety Metrics:")
        print(f"  Minimum TTC: {min_ttc:.2f}s")
        print(f"  Emergency threshold: {config['acc_settings']['emergency_ttc_threshold']}s")
    
    print("\nSimulation complete!")

if __name__ == '__main__':
    main()
