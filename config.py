import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    MODEL = "gpt-4.1-mini"
    DAYS = 10
    CUSTOMERS_PER_DAY = 10
    LOG_DIR = "data/outputs/logs"