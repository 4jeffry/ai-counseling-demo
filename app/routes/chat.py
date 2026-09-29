from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import requests
import base64
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api", tags=["Chat"])

sessions_db = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str
    mode: Optional[str] = "efficient"

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    audio_base64: Optional[str] = None

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    print(f"=== [REQ] Mode: {req.mode} | Msg: {req.message} ===", flush=True)
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong.")

    if req.session_id not in sessions_db:
        sessions_db[req.session_id] = []

    history = sessions_db[req.session_id]
    history.append({"role": "user", "content": req.message})

    ai_reply = await ai_service.generate_response(history)
    history.append({"role": "assistant", "content": ai_reply})

    audio_data = None

    if req.mode == "premium":
        elevenlabs_key = os.getenv("EL", os.getenv("ELEVENLABS_API_KEY", "")).strip()
        print(f"[ELEVENLABS] Key Exists: {bool(elevenlabs_key)}", flush=True)

        if elevenlabs_key:
            try:
                # Menggunakan Premade Voice ID yang GRATIS untuk akun Free (George)
                voice_id = "JBFqnCBsd6RMkjVDRZzb"
                tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": elevenlabs_key
                }
                body = {
                    "text": ai_reply,
                    "model_id": "eleven_multilingual_v2"
                }
                
                print("[ELEVENLABS] Calling API...", flush=True)
                res = requests.post(tts_url, json=body, headers=headers, timeout=12)
                print(f"[ELEVENLABS] Status: {res.status_code}", flush=True)
                
                if res.status_code == 200:
                    audio_data = base64.b64encode(res.content).decode("utf-8")
                    print(f"[ELEVENLABS] Audio Generated! Length: {len(audio_data)}", flush=True)
                else:
                    print(f"[ELEVENLABS ERROR] Response: {res.text}", flush=True)
            except Exception as e:
                print(f"[ELEVENLABS EXCEPTION] {str(e)}", flush=True)
        else:
            print("[ELEVENLABS WARN] Key empty!", flush=True)

    return ChatResponse(
        session_id=req.session_id,
        reply=ai_reply,
        audio_base64=audio_data
    )
