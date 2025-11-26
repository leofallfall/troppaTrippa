import os
import asyncio
import requests
from telegram import Bot
from datetime import datetime, timedelta

TOKEN = os.environ["BOT_TOKEN"]
# Lista di chat ID separati da virgola nell'env variable CHAT_IDS
CHAT_IDS = [int(cid) for cid in os.environ["CHAT_IDS"].split(",")]

bot = Bot(token=TOKEN)

# Per tracciare l'ultimo messaggio di "heartbeat"
last_heartbeat = datetime.min
sleeping = False

async def send_all(text: str):
    """Invia un messaggio a tutte le chat registrate"""
    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            print(f"Errore con chat {chat_id}: {e}")

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

    now = datetime.now()

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
        print("Messaggio inviato: tavolo trovato!")
        last_heartbeat = now
    else:
        # Invia un messaggio di "heartbeat" una volta all'ora
        if now - last_heartbeat > timedelta(hours=1):
            await send_all("✅ Bot attivo, nessun tavolo disponibile.")
            last_heartbeat = now
            print("Messaggio di heartbeat inviato.")
        else:
            print("Nessun tavolo trovato, nessun messaggio inviato.")

async def loop():
    global sleeping
    while True:
        now = datetime.now()
        if 0 <= now.hour < 8:
            if not sleeping:
                # Messaggio di disattivazione
                await send_all("💤 Bot in modalità sleep fino alle 8:00.")
                print("Bot in sleep...")
                sleeping = True

            # Dorme fino alle 8 del mattino
            sleep_seconds = (8 - now.hour) * 3600 - now.minute * 60 - now.second
            await asyncio.sleep(sleep_seconds)

            # Messaggio di attivazione
            await send_all("🔔 Buongiorno! Bot riattivato.")
            print("Bot riattivato.")
            sleeping = False
        else:
            await check_availability()
            await asyncio.sleep(300)  # ogni 5 minuti

if __name__ == "__main__":
    asyncio.run(loop())
