import io
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app.services.ai_service import ai_service, AIError

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", os.getenv("EL", "")).strip()
VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
MAX_HISTORY = 20  # harus genap

user_sessions = {}
http = httpx.AsyncClient(timeout=30)


class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Telegram Aktif!")

    def log_message(self, format, *args):
        pass


def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), DummyHandler).serve_forever()


threading.Thread(target=run_dummy_server, daemon=True).start()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Saya AI Counselor dari ixiera.id.\n"
        "Kirim teks untuk balasan teks, atau kirim Voice Note untuk balasan suara."
    )


async def text_to_voice(text: str):
    r = await http.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        json={"text": text, "model_id": "eleven_multilingual_v2"},
        headers={"Accept": "audio/mpeg", "xi-api-key": ELEVENLABS_API_KEY},
    )
    r.raise_for_status()
    return io.BytesIO(r.content)


async def handle_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    history = user_sessions.setdefault(chat_id, [])
    is_voice = bool(update.message.voice)

    # audio lama dibuang, cuma audio terbaru yang dikirim ke Gemini
    for m in history:
        if "audio_bytes" in m:
            m.pop("audio_bytes")
            m["content"] = "[Pesan suara sebelumnya]"

    if is_voice:
        await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
        f = await update.message.voice.get_file()
        audio = bytes(await f.download_as_bytearray())
        history.append({"role": "user", "audio_bytes": audio, "content": "[Pesan suara]"})
    else:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        history.append({"role": "user", "content": update.message.text})

    try:
        reply = await ai_service.generate_response(history[-MAX_HISTORY:])
    except AIError as e:
        history.pop()  # jangan biarkan pesan gagal ngotorin sesi
        await update.message.reply_text(f"Maaf, lagi ada kendala: {e}. Coba kirim lagi ya.")
        return

    history.append({"role": "assistant", "content": reply})
    del history[:-MAX_HISTORY]

    if is_voice and ELEVENLABS_API_KEY:
        try:
            await context.bot.send_voice(chat_id=chat_id, voice=await text_to_voice(reply))
            return
        except Exception as e:
            print(f"[TTS] gagal: {type(e).__name__}", flush=True)
    await update.message.reply_text(reply)  # teks biasa, atau fallback kalau TTS gagal


def main():
    if not TELEGRAM_TOKEN:
        print("[FATAL] TELEGRAM_TOKEN tidak ditemukan!", flush=True)
        return
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler((filters.TEXT | filters.VOICE) & ~filters.COMMAND, handle_interaction))
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
