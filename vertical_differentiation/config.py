import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    MODEL = "gpt-4.1-mini"
    DAYS = 2
    CUSTOMERS_PER_DAY = 4
    LOG_DIR = "data/outputs/logs"
    # Vertical differentiation ratings (Michelin-style)
    RESTAURANT_A_RATING = 90  # High-end restaurant
    RESTAURANT_B_RATING = 60  # Local diner