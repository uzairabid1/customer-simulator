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
    if Config.ENABLE_CONF_EXPERIMENT:
        print("=== COST OF NEWEST FIRST (CoNF) EXPERIMENT ===")
        print()
        print("Experiment Configuration:")
        print(f"- Two restaurants competing:")
        print(f"  Restaurant A: {Config.RESTAURANT_A_REVIEW_POLICY}")
        print(f"  Restaurant B: {Config.RESTAURANT_B_REVIEW_POLICY}")
        print(f"- True Quality: Restaurant A (μ={Config.CONF_TRUE_QUALITY_A}), Restaurant B (μ={Config.CONF_TRUE_QUALITY_B})")
        print(f"- Dynamic Pricing: Customers choose menu items with actual prices")
        print(f"- Total customers: {Config.CONF_NUM_CUSTOMERS}")
        print(f"- Limited attention: {Config.CONF_LIMITED_ATTENTION} + {Config.CONF_SKEPTICAL_REVIEWS} skeptical reviews")
        print(f"- Beta prior: α={Config.CONF_PRIOR_ALPHA}, β={Config.CONF_PRIOR_BETA}")
        
        # Customer criticality info
        print()
        criticality = Config.CUSTOMER_CRITICALITY.lower()
        if criticality == "easy":
            print("😊 EASY CUSTOMERS: Trusting, accommodating, less skeptical (-2 skepticism)")
        elif criticality == "critical":
            print("🔥 CRITICAL CUSTOMERS: Demanding, analytical, highly skeptical (+3 skepticism)")
        else:
            print("📝 MEDIUM CUSTOMERS: Balanced, reasonable, moderate skepticism")
        
        print()
    else:
        print("Starting restaurant simulation...")
        print(f"Review policies from config:")
        print(f"- Restaurant A: {Config.RESTAURANT_A_REVIEW_POLICY}")
        print(f"- Restaurant B: {Config.RESTAURANT_B_REVIEW_POLICY}")
        print()
    
    # Get output folder name from user
    output_folder = get_output_folder_name()
    print(f"Output will be saved to: data/outputs/{output_folder}")
    
    # Create simulation with custom output folder
    simulation = RestaurantSimulation(output_folder)
    simulation.run_simulation()
    
    if Config.ENABLE_CONF_EXPERIMENT:
        print(f"\nCoNF Experiment complete! Results saved to data/outputs/{output_folder}")
        print("Check 'conf_experiment_results.json' for detailed analysis.")
    else:
        print(f"Simulation complete! Results saved to data/outputs/{output_folder}")

if __name__ == "__main__":
    main()