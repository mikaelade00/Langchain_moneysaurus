import logging
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from telegram import Update
from app.bot.handlers import handle_message, bot
from app.config import WEBHOOK_SECRET

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
        
    if len(str(data)) > 2_000_000:  # Simple check for payload size
        raise HTTPException(status_code=413, detail="Payload too large")
        
    update = Update.de_json(data, bot)
    
    if update.message:
        background_tasks.add_task(handle_message, update)
    
    return {"status": "ok"}

@router.get("/")
async def root():
    return {"message": "Financial Recorder Bot is running."}
