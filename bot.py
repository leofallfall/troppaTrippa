import os
import asyncio
import requests
from telegram import Bot
from datetime import datetime, timedelta

TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

bot = Bot(token=TOKEN)

# Per tracciare l'ultimo messaggio di "heartbeat"
last_heartbeat = datetime.min

async def check_availability():
    global last_heartbeat
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
        await bot.send_message(chat_id=CHAT_ID, text=f"❌ Errore durante il check: {e}")
        print("Errore durante il check:", e)
        return

    available = data.get("AvailableDates", [])

    now = datetime.now()

    if available:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=f"🎉 Tavolo trovato!\n\n{available}"
        )
        print("Messaggio inviato: tavolo trovato!")
        last_heartbeat = now  # Aggiorna anche il heartbeat quando inviamo un messaggio
    else:
        # Invia un messaggio di "heartbeat" una volta all'ora
        if now - last_heartbeat > timedelta(hours=1):
            await bot.send_message(chat_id=CHAT_ID, text="✅ Bot attivo, nessun tavolo disponibile.")
            last_heartbeat = now
            print("Messaggio di heartbeat inviato.")
        else:
            print("Nessun tavolo trovato, nessun messaggio inviato.")

async def loop():
    while True:
        await check_availability()
        await asyncio.sleep(300)  # ogni 5 minuti

if __name__ == "__main__":
    asyncio.run(loop())
