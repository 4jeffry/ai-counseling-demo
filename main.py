import os
import requests
import tempfile
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app.services.ai_service import ai_service

# Ambil keys dari Railway
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Dictionary untuk menyimpan riwayat chat per user
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Saya AI Counselor dari ixiera.id.\n"
        "Silakan ceritakan apa yang sedang Anda rasakan hari ini, saya siap mendengarkan."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    # Inisialisasi sesi jika belum ada
    if chat_id not in user_sessions:
        user_sessions[chat_id] = []
        
    history = user_sessions[chat_id]
    history.append({"role": "user", "content": user_text})
    
    # Kasih status "typing..." di Telegram
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')
    
    # 1. Panggil Gemini
    reply_text = await ai_service.generate_response(history)
    history.append({"role": "assistant", "content": reply_text})
    
    # 2. Balas dengan Teks
    await update.message.reply_text(reply_text)
    
    # 3. Balas dengan Voice Note (ElevenLabs)
    if ELEVENLABS_API_KEY:
        await context.bot.send_chat_action(chat_id=chat_id, action='record_voice')
        try:
            voice_id = "JBFqnCBsd6RMkjVDRZzb" # Voice gratis (George)
            tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": ELEVENLABS_API_KEY
            }
            body = {
                "text": reply_text,
                "model_id": "eleven_multilingual_v2"
            }
            
            res = requests.post(tts_url, json=body, headers=headers, timeout=15)
            if res.status_code == 200:
                # Simpan audio sementara
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                    f.write(res.content)
                    temp_path = f.name
                
                # Kirim sebagai Voice Note (bukan file mp3 biasa)
                with open(temp_path, "rb") as audio:
                    await context.bot.send_voice(chat_id=chat_id, voice=audio)
                
                os.remove(temp_path)
            else:
                print(f"[ELEVENLABS ERROR] {res.text}")
        except Exception as e:
            print(f"[VOICE ERROR] {str(e)}")

def main():
    if not TELEGRAM_TOKEN:
        print("[FATAL] TELEGRAM_TOKEN tidak ditemukan!")
        return

    print("Memulai Telegram Bot...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Jalankan bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
