from simulation.engine import RestaurantSimulation
from config import Config

def main():
    print("Starting restaurant simulation...")
    simulation = RestaurantSimulation()
    simulation.run_simulation()
    print(f"Simulation complete! Results saved to {Config.LOG_DIR}")

if __name__ == "__main__":
    main()