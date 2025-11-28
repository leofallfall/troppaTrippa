import os
import asyncio
import requests
from telegram import Bot
from datetime import datetime, timedelta

TOKEN = os.environ["BOT_TOKEN"]
CHAT_IDS = [int(cid) for cid in os.environ["CHAT_IDS"].split(",")]

bot = Bot(token=TOKEN)

sleeping = False
last_log = datetime.min  # per heartbeat log ogni 30 minuti

async def send_all(text: str):
    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            print(f"Errore con chat {chat_id}: {e}")

async def check_availability():
    url = "https://booking.resdiary.com/api/Restaurant/TRATTORIATRIPPA/AvailabilityForDateRange"
    payload = {
        "DateFrom": "2025-10-20T00:00:00",
        "DateTo": "2025-12-12T00:00:00",
        "PartySize": 2,
        "ChannelCode": "ONLINE",
        "AreaId": None,
        "PromotionId": None
    }

    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        await send_all(f"❌ Errore durante il check: {e}")
        print("Errore durante il check:", e)
        return

    available = data.get("AvailableDates", [])

    if available:
        await send_all(f"🎉 Tavolo trovato!\n\n{available}")
        print("Tavolo trovato e notificato!")
    else:
        print("Check ok, nessun tavolo – nessun messaggio inviato.")

async def loop():
    global sleeping, last_log

    while True:
        now = datetime.now()

        # 💤 MODALITÀ NOTTE 00:00–08:00
        if 0 <= now.hour < 8:
            if not sleeping:
                await send_all("💤 Bot in modalità sleep fino alle 8:00.")
                print("Bot in sleep...")
                sleeping = True

            # Log ogni 30 minuti per evitare sleep su Railway
            if now - last_log > timedelta(minutes=30):
                print(f"[{now}] Heartbeat notturno: bot vivo.")
                last_log = now

            await asyncio.sleep(60)  # controlla ogni minuto il passaggio delle 8
            continue

        # ☀️ MODALITÀ GIORNO
        if sleeping:
            await send_all("🔔 Buongiorno! Bot riattivato.")
            print("Bot riattivato.")
            sleeping = False

        await check_availability()
        await asyncio.sleep(300)  # controlla ogni 5 minuti

if __name__ == "__main__":
    asyncio.run(loop())
