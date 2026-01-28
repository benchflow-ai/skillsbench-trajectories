"""Run ACC simulation and generate output files."""

from simulation import ACCSimulation


def main():
    """Run simulation and save results."""
    sim = ACCSimulation(
        '/root/vehicle_params.yaml',
        '/root/sensor_data.csv',
        '/root/tuning_results.yaml'
    )

    print("Running 150s ACC simulation...")
    results = sim.run()
    print(f"Simulation complete. Generated {len(results)} samples.")

    print("Saving results to simulation_results.csv...")
    sim.save_results(results, '/root/simulation_results.csv')
    print("Done!")


if __name__ == '__main__':
    main()
