import os
import requests
from app.prompts.counseling import COUNSELING_SYSTEM_PROMPT

class AIService:
    def __init__(self):
        self.api_key = os.getenv("AI_API_KEY", "").strip()

    async def generate_response(self, messages: list) -> str:
        if not self.api_key:
            return "ERROR: Kunci AI_API_KEY belum terpasang di Railway."

        try:
            # Menggunakan Gemini 3.8 Flash sesuai dokumentasi API terbaru
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={self.api_key}"
            
            contents = []
            for msg in messages:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}]
                })

            payload = {
                "system_instruction": {
                    "parts": [{"text": COUNSELING_SYSTEM_PROMPT}]
                },
                "contents": contents
            }

            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"[GEMINI ERROR] {response.text}", flush=True)
                return f"Gemini Error {response.status_code}: Model API salah atau limit habis."
        except Exception as e:
            return f"Koneksi ke Gemini gagal: {str(e)}"

ai_service = AIService()
