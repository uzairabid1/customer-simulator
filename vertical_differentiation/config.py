import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    MODEL = "gpt-4.1-mini"
    DAYS = 3  # Increased simulation duration
    CUSTOMERS_PER_DAY = 6  # More customers per day
    LOG_DIR = "data/outputs/logs"
    # Vertical differentiation ratings
    RESTAURANT_A_RATING = 90  # High-end restaurant
    RESTAURANT_B_RATING = 45  # Basic diner
    # Review policies - can be "highest_rating" or "latest"
    RESTAURANT_A_REVIEW_POLICY = "highest_rating"  # Default: show highest rated reviews first
    RESTAURANT_B_REVIEW_POLICY = "highest_rating"  # Default: show highest rated reviews first
    
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