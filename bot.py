import os
import asyncio
import requests
from telegram import Bot

TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

bot = Bot(token=TOKEN)

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

    r = requests.post(url, json=payload)
    data = r.json()

    available = data.get("AvailableDates", [])

    if available:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=f"🎉 Tavolo trovato!\n\n{available}"
        )
        print("Messaggio inviato!")
    else:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=f"🎉 Tavolo trovato!\n\n{available}"
        )
        print("Nessun tavolo trovato.")

async def loop():
    while True:
        try:
            await check_availability()
        except Exception as e:
            print("Errore:", e)

        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(loop())
