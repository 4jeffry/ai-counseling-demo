import os
import base64
import httpx
from app.prompts.counseling import COUNSELING_SYSTEM_PROMPT

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


class AIError(Exception):
    pass


class AIService:
    def __init__(self):
        self.api_key = os.getenv("AI_API_KEY", "").strip()
        self.client = httpx.AsyncClient(timeout=45)

    async def generate_response(self, messages: list) -> str:
        if not self.api_key:
            raise AIError("AI_API_KEY belum terpasang")

        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            if msg.get("audio_bytes"):
                b64 = base64.b64encode(msg["audio_bytes"]).decode()
                parts = [
                    {"inlineData": {"mimeType": "audio/ogg", "data": b64}},
                    {"text": "Dengarkan pesan suara ini dan balas sebagai konselor."},
                ]
            else:
                parts = [{"text": msg.get("content") or "-"}]
            contents.append({"role": role, "parts": parts})

        payload = {
            "system_instruction": {"parts": [{"text": COUNSELING_SYSTEM_PROMPT}]},
            "contents": contents,
        }

        try:
            r = await self.client.post(
                URL, json=payload, headers={"x-goog-api-key": self.api_key}
            )
        except httpx.HTTPError as e:
            print(f"[GEMINI] {type(e).__name__}", flush=True)
            raise AIError("koneksi ke Gemini gagal atau timeout")

        if r.status_code != 200:
            print(f"[GEMINI] {r.status_code} {r.text[:500]}", flush=True)
            raise AIError(f"Gemini error {r.status_code}")

        try:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise AIError("respons Gemini kosong atau diblokir")


ai_service = AIService()
