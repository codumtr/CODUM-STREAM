"""
Kick Official API & Webhook Handler
Kick'in resmî Developer API'si ve Webhook altyapısıyla çalışır.
Görevi: Chat'te '!audio', '!dub', '!dil' komutlarını yakalayıp izleyicileri
Chrome uzantısına yönlendirmektir. Dublaj sesini dağıtmaz.
"""

import os
import hmac
import hashlib
import aiohttp
from fastapi import APIRouter, Request, Header, HTTPException
from pydantic import BaseModel

kick_router = APIRouter(prefix="/api/kick", tags=["Kick Bot"])

KICK_CLIENT_ID = os.getenv("KICK_CLIENT_ID", "")
KICK_CLIENT_SECRET = os.getenv("KICK_CLIENT_SECRET", "")
KICK_WEBHOOK_SECRET = os.getenv("KICK_WEBHOOK_SECRET", "")
KICK_BOT_TOKEN = os.getenv("KICK_BOT_TOKEN", "")

EXTENSION_STORE_URL = "https://chromewebstore.google.com/detail/streamdub-kick"

async def send_kick_chat_message(broadcaster_id: str, message: str):
    """Kick Official Chat API üzerinden bota mesaj attırır."""
    if not KICK_BOT_TOKEN:
        print(f"[Kick Bot Simülasyonu -> Chat]: {message}")
        return

    url = "https://api.kick.com/public/v1/chat"
    headers = {
        "Authorization": f"Bearer {KICK_BOT_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "broadcaster_id": broadcaster_id,
        "content": message
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status not in (200, 201):
                    print(f"❌ Kick Chat API Hatası: {await resp.text()}")
    except Exception as e:
        print(f"❌ Kick Chat Bağlantı Hatası: {e}")

@kick_router.post("/webhook")
async def handle_kick_webhook(request: Request, x_kick_signature: str = Header(None)):
    """
    Kick resmî 'chat.message.sent' webhook dinleyicisi.
    """
    body_bytes = await request.body()

    # Webhook imza doğrulaması (güvenlik)
    if KICK_WEBHOOK_SECRET and x_kick_signature:
        expected_sig = hmac.new(KICK_WEBHOOK_SECRET.encode(), body_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, x_kick_signature):
            raise HTTPException(status_code=401, detail="Geçersiz Webhook İmzası")

    try:
        data = await request.json()
    except Exception:
        return {"status": "ignored"}

    event_type = data.get("event")
    event_data = data.get("data", {})

    # chat.message.sent olayı
    if event_type == "chat.message.sent":
        content = event_data.get("content", "").strip()
        sender = event_data.get("sender", {}).get("username", "")
        broadcaster_id = str(event_data.get("broadcaster_user_id", ""))

        # Komut Yakalama
        if content.lower().startswith("!audio") or content.lower().startswith("!dub") or content.lower().startswith("!çeviri"):
            reply = (
                f"@{sender} 🎙️ This stream is live-dubbed in English! "
                f"Install the free CODUM StreamDub Chrome extension to listen: {EXTENSION_STORE_URL}"
            )
            await send_kick_chat_message(broadcaster_id, reply)

    return {"status": "ok"}
