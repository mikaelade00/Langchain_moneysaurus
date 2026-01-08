import logging
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.webhook import router
from app.db.database import init_db
from app.bot.handlers import bot
from app.config import WEBHOOK_URL, WEBHOOK_SECRET

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_db()
    if WEBHOOK_URL:
        webhook_path = f"{WEBHOOK_URL.rstrip('/')}/webhook"
        await bot.set_webhook(url=webhook_path, secret_token=WEBHOOK_SECRET)
        logger.info(f"Webhook set to: {webhook_path}")
    logger.info("Bot started and DB initialized.")
    yield
    # Shutdown logic (optional)
    logger.info("Bot shutting down.")

app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
