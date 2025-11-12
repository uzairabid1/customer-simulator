import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    MODEL = "gpt-4.1-mini"
    DAYS = 1  # Increased simulation duration
    CUSTOMERS_PER_DAY = 5  # More customers per day
    LOG_DIR = "data/outputs/logs"
    
    # === CoNF EXPERIMENT SETTINGS ===
    ENABLE_CONF_EXPERIMENT = True  # Enable Cost of Newest First experiment
    CONF_NUM_CUSTOMERS = 5  # Number of customers for CoNF experiment
    CONF_TRUE_QUALITY_A = 0.7  # True product quality for Restaurant A (mu parameter)
    CONF_TRUE_QUALITY_B = 0.7  # True product quality for Restaurant B (mu parameter)
    CONF_USE_DYNAMIC_PRICING = True  # Use actual menu item prices instead of fixed price
    CONF_LIMITED_ATTENTION = 3  # Number of reviews customers read initially
    CONF_SKEPTICAL_REVIEWS = 3  # Additional reviews if skeptical
    CONF_PRIOR_ALPHA = 1.0  # Beta prior parameter
    CONF_PRIOR_BETA = 1.0  # Beta prior parameter
    CONF_THETA_MEAN = 50.0  # Mean idiosyncratic valuation (higher baseline)
    CONF_THETA_STD = 30.0  # Std dev of idiosyncratic valuation (more variation)
    
    # === CUSTOMER CRITICALITY SETTINGS ===
    CUSTOMER_CRITICALITY = "medium"  # Options: "easy", "medium", "critical"
    
    # Vertical differentiation ratings
    RESTAURANT_A_RATING = 45
    RESTAURANT_B_RATING = 45
    # Review policies - can be "highest_rating", "latest", "recent_quality_boost", "newest_first", "random"
    RESTAURANT_A_REVIEW_POLICY = "random"
    RESTAURANT_B_REVIEW_POLICY = "highest_rating"
    
    # Restaurant Information
    RESTAURANT_A_NAME = "Bella Vista"
    RESTAURANT_A_DESCRIPTION = "Upscale casual dining with Italian-American cuisine, known for fresh ingredients and generous portions"
    RESTAURANT_A_CUISINE_TYPE = "Italian-American"
    RESTAURANT_A_PRICE_RANGE = "$$-$$$"
    
    RESTAURANT_B_NAME = "Coastal Breeze" 
    RESTAURANT_B_DESCRIPTION = "Contemporary bistro featuring seasonal dishes with ocean-inspired flavors and modern presentation"
    RESTAURANT_B_CUISINE_TYPE = "Contemporary American"
    RESTAURANT_B_PRICE_RANGE = "$$-$$$"
    
    # Menu configurations
    # Restaurant A
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
    
    # Restaurant B
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