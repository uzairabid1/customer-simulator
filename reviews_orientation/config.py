import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    MODEL = "gpt-4.1-mini"
    DAYS = 2
    CUSTOMERS_PER_DAY = 4
    LOG_DIR = "data/outputs/logs"
    
    # Review policies - can be "highest_rating", "latest", or "recent_quality_boost"
    RESTAURANT_A_REVIEW_POLICY = "highest_rating"  # Default: show highest rated reviews first
    RESTAURANT_B_REVIEW_POLICY = "latest"  # Default: show most recent reviews first
    # To test the new algorithm, change RESTAURANT_B_REVIEW_POLICY to "recent_quality_boost"
    
    # Menu configuration - both restaurants use the same menu in reviews_orientation
    RESTAURANT_MENU = {
        "Burger": 10,
        "Pizza": 12,
        "Salad": 8,
        "Pasta": 11,
        "Steak": 18,
        "Sushi Platter": 22,
        "Chicken Wings": 9,
        "Vegetable Stir Fry": 13,
        "Ramen": 14,
        "Tacos": 10,
        "Caesar Salad": 9,
        "Grilled Salmon": 20,
        "Margherita Pizza": 15,
        "Cheesecake": 7,
        "Ice Cream Sundae": 6,
        "Club Sandwich": 11,
        "French Fries": 5,
        "Onion Rings": 6,
        "Mushroom Risotto": 16,
        "Chocolate Cake": 8,
        "Fish and Chips": 14,
        "Vegetable Curry": 12
    }