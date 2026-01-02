import os
import logging
from fastapi import FastAPI, Request, BackgroundTasks
from telegram import Update, Bot
from financial_recorder import get_agent_response, init_db
from dotenv import load_dotenv

load_dotenv()

from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_db()
    webhook_path = f"{WEBHOOK_URL.rstrip('/')}/webhook"
    await bot.set_webhook(url=webhook_path, secret_token=WEBHOOK_SECRET)
    logger.info(f"Webhook set to: {webhook_path}")
    logger.info("Bot started and DB initialized.")
    yield
    # Shutdown logic (optional)
    logger.info("Bot shutting down.")

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        data = await request.json()
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if len(data) > 2_000_000:  # 2 MB
        raise HTTPException(status_code=413, detail="Payload too large")
    update = Update.de_json(data, bot)
    
    if update.message:
        background_tasks.add_task(handle_message, update)
    
    return {"status": "ok"}

async def handle_message(update: Update):
    chat_id = update.message.chat_id
    text = update.message.text
    photo = update.message.photo
    
    try:
        response = ""
        if photo:
            # Handle photo (take the largest one)
            file = await bot.get_file(photo[-1].file_id)
            img_bytes = await file.download_as_bytearray()
            response = await get_agent_response(
                text_or_image=bytes(img_bytes),
                chat_id=chat_id,
                is_image=True
            )
        elif text:
            response = await get_agent_response(
                text_or_image=text,
                chat_id=chat_id,
                is_image=False
            )
        else:
            response = "Maaf, saya hanya bisa memproses teks atau foto nota/struk."

        if not response or not response.strip():
            response = "Maaf, saya tidak mendapatkan respon teks dari AI. Silakan coba lagi atau periksa input Anda."
        
        await bot.send_message(
            chat_id=chat_id, 
            text=response,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text="Terjadi kesalahan sistem. Silakan coba lagi nanti."
        )

@app.get("/")
async def root():
    return {"message": "Financial Recorder Bot is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
