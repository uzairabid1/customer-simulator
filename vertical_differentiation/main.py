from simulation.engine import RestaurantSimulation
from config import Config
import os
from datetime import datetime
import sys
sys.dont_write_bytecode = True


def get_output_folder_name():
    """Prompt user for output folder name with validation"""
    while True:
        folder_name = input("Enter a name for the output folder (or press Enter for default): ").strip()
        
        if not folder_name:
            # Use timestamp as default
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"simulation_{timestamp}"
        
        # Clean the folder name (remove invalid characters)
        folder_name = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        folder_name = folder_name.replace(' ', '_')
        
        if not folder_name:
            print("Please enter a valid folder name.")
            continue
            
        # Check if folder already exists
        output_path = os.path.join("data", "outputs", folder_name)
        if os.path.exists(output_path):
            overwrite = input(f"Folder '{folder_name}' already exists. Overwrite? (y/N): ").strip().lower()
            if overwrite != 'y':
                continue
        
        return folder_name

def main():
    print("Starting restaurant simulation...")
    
    # Display current review policy settings from config
    print(f"Review policies from config:")
    print(f"- Restaurant A (High-end): {Config.RESTAURANT_A_REVIEW_POLICY}")
    print(f"- Restaurant B (Basic diner): {Config.RESTAURANT_B_REVIEW_POLICY}")
    print()
    
    # Get output folder name from user
    output_folder = get_output_folder_name()
    print(f"Output will be saved to: data/outputs/{output_folder}")
    
    # Create simulation with custom output folder
    simulation = RestaurantSimulation(output_folder)
    simulation.run_simulation()
    print(f"Simulation complete! Results saved to data/outputs/{output_folder}")

if __name__ == "__main__":
    main()