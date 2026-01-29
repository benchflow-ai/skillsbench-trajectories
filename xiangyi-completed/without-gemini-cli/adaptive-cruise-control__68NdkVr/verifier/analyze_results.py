import csv

def analyze(filename):
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    speeds = [float(r['ego_speed']) for r in rows]
    times = [float(r['time']) for r in rows]
    modes = [r['mode'] for r in rows]
    dist_errs = [float(r['distance_error']) if r['distance_error'] else None for r in rows]
    distances = [float(r['distance']) if r['distance'] else None for r in rows]
    
    rise_time = next((t for t, v in zip(times, speeds) if v >= 27.0), None)
    max_speed = max(speeds)
    overshoot = (max_speed - 30.0) / 30.0 * 100 if max_speed > 30.0 else 0.0
    
    # SS Speed Error (cruise at t=20-30)
    ss_v_err = sum(abs(v - 30.0) for v, t, m in zip(speeds, times, modes) if m == 'cruise' and t > 20 and t < 30) / 100
    
    # SS Dist Error (follow at t=110-125)
    # Lead vehicle is slower than 30 at the very end before it disappears
    follow_errs = [abs(e) for e, t, m in zip(dist_errs, times, modes) if m == 'follow' and t > 120 and e is not None]
    ss_d_err = sum(follow_errs) / len(follow_errs) if follow_errs else 0.0
    
    min_dist = min([d for d in distances if d is not None]) if any(d is not None for d in distances) else 0.0
    
    print(f"Rise Time: {rise_time}")
    print(f"Overshoot: {overshoot:.2f}%")
    print(f"SS Speed Error: {ss_v_err:.2f} m/s")
    print(f"SS Distance Error: {ss_d_err:.2f} m")
    print(f"Min Distance: {min_dist:.2f} m")

if __name__ == "__main__":
    analyze('simulation_results.csv')
