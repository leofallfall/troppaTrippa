import os
import time
import requests
import telegram

TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))

bot = telegram.Bot(token=TOKEN)

def check_availability():
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
        bot.send_message(chat_id=CHAT_ID, text=f"🎉 Tavolo trovato!\n\n{available}")
    else:
        print("Nessun tavolo trovato.")
        bot.send_message(chat_id=CHAT_ID, text=f"🎉 Tavolo trovato!\n\n{available}")

def loop():
    while True:
        try:
            check_availability()
        except Exception as e:
            print("Errore:", e)

        time.sleep(300)  # 5 minuti

if __name__ == "__main__":
    loop()
