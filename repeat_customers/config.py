import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    MODEL = "gpt-4.1-mini"
    
    # === REPEAT CUSTOMER SIMULATION SETTINGS ===
    ENABLE_REPEAT_CUSTOMERS = True  # Enable repeat customer simulation
    NUM_REPEAT_CUSTOMERS = 50  # Number of customers that repeat daily
    SIMULATION_DAYS = 7  # Number of days to simulate
    
    # Customer memory settings - keep it simple
    # No complex memory decay - customers just remember all their experiences
    
    # Review reading settings (same as original)
    LIMITED_ATTENTION = 3  # Number of reviews customers read initially
    SKEPTICAL_REVIEWS = 3  # Additional reviews if skeptical
    
    # Beta-Bernoulli belief update parameters
    PRIOR_ALPHA = 1.0  # Beta prior parameter
    PRIOR_BETA = 1.0  # Beta prior parameter
    
    # Customer valuation parameters
    THETA_MEAN = 50.0  # Mean idiosyncratic valuation
    THETA_STD = 30.0  # Std dev of idiosyncratic valuation
    
    # Restaurant quality parameters
    TRUE_QUALITY_A = 0.1  # True product quality for Restaurant A (mu parameter)
    TRUE_QUALITY_B = 0.9  # True product quality for Restaurant B (mu parameter)
    
    # === CUSTOMER CRITICALITY SETTINGS ===
    CUSTOMER_CRITICALITY = "medium"  # Options: "easy", "medium", "critical"
    
    # Restaurant ratings (0-100 scale, converted to stars internally)
    RESTAURANT_A_RATING = 10
    RESTAURANT_B_RATING = 90
    
    # Review policies - can be "highest_rating", "latest", "recent_quality_boost", "newest_first", "random"
    RESTAURANT_A_REVIEW_POLICY = "highest_rating"
    RESTAURANT_B_REVIEW_POLICY = "newest_first"
    
    # Restaurant Information
    RESTAURANT_A_NAME = "Bella Vista"
    RESTAURANT_A_DESCRIPTION = "Upscale casual dining with Italian-American cuisine, known for fresh ingredients and generous portions"
    RESTAURANT_A_CUISINE_TYPE = "Italian-American"
    RESTAURANT_A_PRICE_RANGE = "$$-$$$"
    
    RESTAURANT_B_NAME = "Coastal Breeze" 
    RESTAURANT_B_DESCRIPTION = "Contemporary bistro featuring seasonal dishes with ocean-inspired flavors and modern presentation"
    RESTAURANT_B_CUISINE_TYPE = "Contemporary American"
    RESTAURANT_B_PRICE_RANGE = "$$-$$$"
    
    # Menu configurations (same for both restaurants)
    RESTAURANT_A_MENU = {
        "Avocado Eggrolls": 14,
        "Bacon-Bacon Cheeseburger": 18,
        "Club Sandwich": 17,
        "Chicken Parmesan Pasta": 23,
        "Chicken Madeira": 24,
        "Grilled Salmon": 28,
        "Original Cheesecake": 9,
        "Fresh Strawberry Cheesecake": 10
    }
    
    RESTAURANT_B_MENU = {
        "Avocado Eggrolls": 14,
        "Bacon-Bacon Cheeseburger": 18,
        "Club Sandwich": 17,
        "Chicken Parmesan Pasta": 23,
        "Chicken Madeira": 24,
        "Grilled Salmon": 28,
        "Original Cheesecake": 9,
        "Fresh Strawberry Cheesecake": 10
    }
    
    # Logging
    LOG_DIR = "data/outputs/logs"
