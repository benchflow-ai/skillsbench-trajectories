import csv

def debug_120():
    ego_speed_sim = 0.0
    ego_pos_sim = -150.0
    sensor_ego_pos = 0.0
    dt = 0.1
    
    with open('sensor_data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = float(row['time'])
            v_ego_sensor = float(row['ego_speed'])
            
            # Simulation would have updated speed and pos before this
            # but let's just approximate or follow the simulation.py logic.
            
            # This is hard to do without the actual acceleration commands.
            # Let's just read the simulation_results.csv instead.
            pass

def check_results():
    with open('simulation_results.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['time'] == '119.9':
                print(f"119.9: speed={row['ego_speed']}, dist={row['distance']}")
            if row['time'] == '120.0':
                print(f"120.0: speed={row['ego_speed']}, dist={row['distance']}")

if __name__ == "__main__":
    check_results()
