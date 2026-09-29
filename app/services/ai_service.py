import os
import requests
from app.prompts.counseling import COUNSELING_SYSTEM_PROMPT

class AIService:
    def __init__(self):
        self.demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
        self.api_key = os.getenv("AI_API_KEY", "")

    async def generate_response(self, messages: list) -> str:
        if self.demo_mode or not self.api_key:
            return self._get_mock_response(messages)

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
            
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

            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            else:
                return "Terima kasih sudah berbagi. Bisakah Anda menceritakan lebih lanjut?"
        except Exception:
            return self._get_mock_response(messages)

    def _get_mock_response(self, messages: list) -> str:
        last_message = messages[-1]["content"].lower() if messages else ""
        if "cemas" in last_message or "stres" in last_message:
            return "Saya memahami perasaan tersebut. Beban yang Anda rasakan pasti sangat berat. Apa hal utama yang paling memicu perasaan itu saat ini?"
        return "Terima kasih sudah bercerita. Saya mendengarkan Anda. Bagaimana perasaan Anda setelah menyampaikan hal tersebut?"

ai_service = AIService()
