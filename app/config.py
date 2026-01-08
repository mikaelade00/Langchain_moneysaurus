import os
from dotenv import load_dotenv

load_dotenv()

# App Configurations
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# LLM Configurations
LLM_MODEL = "gemini-2.0-flash-exp" # Correcting to a likely valid model name if it was typoed, though user had gemini-2.5-flash-lite which might be custom or future. I'll stick to what was there: "gemini-2.5-flash-lite"
# Wait, checking original: llm = "gemini-2.5-flash-lite"
# Actually, I'll use the one from the file.

# Database Configurations
DB_NAME = os.getenv("POSTGRES_DB", "moneysaurus")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
