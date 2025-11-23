from simulation.engine import RepeatCustomerSimulation
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
            folder_name = f"repeat_simulation_{timestamp}"
        
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
    print("=== REPEAT CUSTOMER SIMULATION ===")
    print()
    print("Simulation Configuration:")
    print(f"- Number of repeat customers: {Config.NUM_REPEAT_CUSTOMERS}")
    print(f"- Simulation days: {Config.SIMULATION_DAYS}")
    print(f"- Customer memory: Simple - customers remember all past experiences")
    print()
    print("Restaurant Configuration:")
    print(f"- Restaurant A ({Config.RESTAURANT_A_NAME}): {Config.RESTAURANT_A_REVIEW_POLICY} policy")
    print(f"- Restaurant B ({Config.RESTAURANT_B_NAME}): {Config.RESTAURANT_B_REVIEW_POLICY} policy")
    print(f"- True Quality: A (mu={Config.TRUE_QUALITY_A}), B (mu={Config.TRUE_QUALITY_B})")
    print()
    print("Customer Configuration:")
    criticality = Config.CUSTOMER_CRITICALITY.lower()
    if criticality == "easy":
        print("EASY CUSTOMERS: Trusting, accommodating, less skeptical")
    elif criticality == "critical":
        print("CRITICAL CUSTOMERS: Demanding, analytical, highly skeptical")
    else:
        print("MEDIUM CUSTOMERS: Balanced, reasonable, moderate skepticism")
    print()
    
    # Get output folder name from user
    output_folder = get_output_folder_name()
    print(f"Output will be saved to: data/outputs/{output_folder}")
    print()
    
    # Create and run simulation
    simulation = RepeatCustomerSimulation(output_folder)
    simulation.run_simulation()
    
    print(f"\nRepeat Customer Simulation complete! Results saved to data/outputs/{output_folder}")
    print("Check 'repeat_customer_results.json' for detailed analysis.")

if __name__ == "__main__":
    main()
