from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://api.openai.com/")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
