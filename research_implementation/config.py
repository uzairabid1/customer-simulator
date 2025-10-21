import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    MODEL = "gpt-4.1-mini"
    DAYS = 2  # Increased simulation duration
    CUSTOMERS_PER_DAY = 6  # More customers per day
    LOG_DIR = "data/outputs/logs"
    
    # === CoNF EXPERIMENT SETTINGS ===
    ENABLE_CONF_EXPERIMENT = True  # Enable Cost of Newest First experiment
    CONF_NUM_CUSTOMERS = 100  # Number of customers for CoNF experiment
    CONF_TRUE_QUALITY_A = 0.7  # True product quality for Restaurant A (mu parameter)
    CONF_TRUE_QUALITY_B = 0.7  # True product quality for Restaurant B (mu parameter)
    CONF_USE_DYNAMIC_PRICING = True  # Use actual menu item prices instead of fixed price
    CONF_LIMITED_ATTENTION = 3  # Number of reviews customers read initially
    CONF_SKEPTICAL_REVIEWS = 3  # Additional reviews if skeptical
    CONF_PRIOR_ALPHA = 1.0  # Beta prior parameter
    CONF_PRIOR_BETA = 1.0  # Beta prior parameter
    CONF_THETA_MEAN = 50.0  # Mean idiosyncratic valuation (higher baseline)
    CONF_THETA_STD = 30.0  # Std dev of idiosyncratic valuation (more variation)
    
    # Vertical differentiation ratings
    RESTAURANT_A_RATING = 90  # High-end restaurant
    RESTAURANT_B_RATING = 45  # Basic diner
    # Review policies - can be "highest_rating", "latest", "recent_quality_boost", "newest_first", "random"
    RESTAURANT_A_REVIEW_POLICY = "newest_first"  # Will be dynamically changed for CoNF experiment
    RESTAURANT_B_REVIEW_POLICY = "random"  # Not used in CoNF experiment
    
    # Menu configurations
    # Restaurant A - High-end Italian/French fine dining with premium pricing
    RESTAURANT_A_MENU = {
        "Truffle Risotto": 85,
        "Duck Confit": 95,
        "Lobster Thermidor": 110,
        "Veal Marsala": 90,
        "Coq au Vin": 80,
        "Beef Bourguignon": 100,
        "Crème Brûlée": 25,
        "Wine Flight": 120
    }
    
    # Restaurant B - Basic diner with affordable pricing
    RESTAURANT_B_MENU = {
        "Sushi Platter": 85,
        "Peking Duck": 95,
        "Lobster Pad Thai": 110,
        "Teriyaki Salmon": 90,
        "Kung Pao Chicken": 80,
        "Beef Bulgogi": 100,
        "Mochi Ice Cream": 25,
        "Sake Tasting": 120
    }