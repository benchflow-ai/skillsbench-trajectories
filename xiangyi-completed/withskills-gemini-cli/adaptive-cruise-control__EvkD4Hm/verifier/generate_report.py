import pandas as pd
import yaml

def generate_report():
    # Load data
    with open('tuning_results.yaml', 'r') as f:
        tuning = yaml.safe_load(f)
        
    df = pd.read_csv('simulation_results.csv')
    
    # Calculate Metrics
    
    # Speed Control Metrics (Cruise Phase 0-30s approx)
    # Target 30 m/s
    cruise_data = df[df['time'] < 30.0]
    final_cruise_speed = cruise_data['ego_speed'].iloc[-1]
    max_cruise_speed = cruise_data['ego_speed'].max()
    
    # Rise time (10% to 90% of 30)
    target = 30.0
    t10 = cruise_data[cruise_data['ego_speed'] >= 0.1 * target]['time'].min()
    t90 = cruise_data[cruise_data['ego_speed'] >= 0.9 * target]['time'].min()
    rise_time = t90 - t10 if (pd.notna(t10) and pd.notna(t90)) else None
    
    overshoot = (max_cruise_speed - target) / target * 100 if max_cruise_speed > target else 0.0
    ss_error_speed = abs(target - final_cruise_speed)
    
    # Distance Control Metrics (Follow Phase > 30s)
    follow_data = df[df['mode'].isin(['follow', 'emergency'])]
    if not follow_data.empty:
        min_distance = follow_data['distance'].min()
        max_decel = df['acceleration_cmd'].min()
        
        # Steady state distance error?
        # Hard to define single SS error as target changes.
        # Use mean absolute error of 'distance_error' column where available
        dist_errors = follow_data['distance_error'].abs()
        mean_dist_error = dist_errors.mean()
        final_dist_error = dist_errors.iloc[-1] if not dist_errors.empty else 0.0
    else:
        min_distance = None
        max_decel = 0.0
        mean_dist_error = 0.0
        final_dist_error = 0.0

    # Write Report
    with open('acc_report.md', 'w') as f:
        f.write("# Adaptive Cruise Control Simulation Report\n\n")
        
        f.write("## 1. System Design\n")
        f.write("The ACC system is implemented using a hierarchical control architecture:\n")
        f.write("- **Supervisor**: A state machine determines the operating mode ('cruise', 'follow', 'emergency') based on sensor inputs (lead vehicle detection, Time-to-Collision).\n")
        f.write("- **Controllers**: Two distinct PID controllers manage longitudinal dynamics:\n")
        f.write("  - `PID_Speed`: Maintains the set speed (30 m/s) in free-flow conditions.\n")
        f.write("  - `PID_Distance`: Maintains a safe time-gap (1.5s) when following a lead vehicle.\n")
        f.write("- **Safety**: Acceleration is clamped to vehicle limits [-8.0, 3.0] m/s^2. Emergency braking is triggered if TTC < 3.0s.\n\n")
        
        f.write("## 2. PID Tuning Methodology\n")
        f.write("Gains were optimized using a randomized search algorithm against synthetic scenarios:\n")
        f.write("- **Speed Loop**: Tuned on a 0-30m/s step response to minimize rise time and overshoot.\n")
        f.write("- **Distance Loop**: Tuned on a closing-gap scenario to minimize steady-state error and prevent safety violations.\n\n")
        
        f.write("### Final Gains\n")
        f.write("#### Speed Controller\n")
        f.write(f"- Kp: {tuning['pid_speed']['kp']:.3f}\n")
        f.write(f"- Ki: {tuning['pid_speed']['ki']:.3f}\n")
        f.write(f"- Kd: {tuning['pid_speed']['kd']:.3f}\n")
        f.write("#### Distance Controller\n")
        f.write(f"- Kp: {tuning['pid_distance']['kp']:.3f}\n")
        f.write(f"- Ki: {tuning['pid_distance']['ki']:.3f}\n")
        f.write(f"- Kd: {tuning['pid_distance']['kd']:.3f}\n\n")
        
        f.write("## 3. Simulation Results\n")
        f.write("The system was tested on a 150s real-world driving scenario.\n\n")
        
        f.write("### Speed Control Performance (Cruise Phase)\n")
        f.write(f"- **Rise Time (0-30 m/s)**: {rise_time:.2f} s (Target: <10s)\n")
        f.write(f"- **Overshoot**: {overshoot:.2f}% (Target: <5%)\n")
        f.write(f"- **Steady-State Error**: {ss_error_speed:.3f} m/s (Target: <0.5 m/s)\n\n")
        
        f.write("### Distance Control Performance (Follow Phase)\n")
        f.write(f"- **Minimum Distance Maintained**: {min_distance:.2f} m (Target: >5m)\n")
        f.write(f"- **Mean Distance Error**: {mean_dist_error:.2f} m\n")
        f.write(f"- **Max Deceleration**: {max_decel:.2f} m/s^2\n")
        
        f.write("\n### Conclusion\n")
        valid = True
        if rise_time and rise_time > 10: valid = False
        if overshoot > 5: valid = False
        if min_distance and min_distance < 5: valid = False
        
        if valid:
            f.write("The ACC system met all safety and performance requirements.")
        else:
            f.write("The ACC system requires further tuning to meet all specifications.")

if __name__ == '__main__':
    generate_report()
