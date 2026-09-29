import os
import asyncio
import base64
import httpx
from app.prompts.counseling import COUNSELING_SYSTEM_PROMPT

MODELS = [
    m.strip()
    for m in os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").split(",")
    if m.strip()
]


def _url(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


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
        headers = {"x-goog-api-key": self.api_key}
        last = "unknown"

        for model in MODELS:
            for attempt in range(2):
                try:
                    r = await self.client.post(_url(model), json=payload, headers=headers)
                except httpx.HTTPError as e:
                    last = type(e).__name__
                    print(f"[GEMINI] {model} {last}", flush=True)
                    await asyncio.sleep(1.5)
                    continue

                if r.status_code == 200:
                    try:
                        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    except (KeyError, IndexError):
                        raise AIError("respons Gemini kosong atau diblokir")

                last = str(r.status_code)
                print(f"[GEMINI] {model} {r.status_code} {r.text[:300]}", flush=True)
                if r.status_code in (429, 500, 503):
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue  # coba lagi model yang sama
                break  # 400/404 dll: langsung ke model berikutnya

        raise AIError(f"Gemini lagi sibuk ({last})")


ai_service = AIService()
