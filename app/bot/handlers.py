import logging
from telegram import Update, Bot
from app.services.agent import get_agent_response
from app.config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

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
