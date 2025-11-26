import os
import asyncio
import requests
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime, timedelta

TOKEN = os.environ["BOT_TOKEN"]

bot = Bot(token=TOKEN)

last_heartbeat = datetime.min
sleeping = False
CHAT_IDS_FILE = "chat_ids.txt"

# Carica gli ID delle chat da file
if os.path.exists(CHAT_IDS_FILE):
    with open(CHAT_IDS_FILE, "r") as f:
        chat_ids = [int(line.strip()) for line in f.readlines()]
else:
    chat_ids = []

# Funzione per salvare gli ID
def save_chat_ids():
    with open(CHAT_IDS_FILE, "w") as f:
        for chat_id in chat_ids:
            f.write(f"{chat_id}\n")

# Comando /start per registrare l'utente
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in chat_ids:
        chat_ids.append(chat_id)
        save_chat_ids()
        await update.message.reply_text("✅ Bot registrato! Riceverai i messaggi di disponibilità e heartbeat.")
    else:
        await update.message.reply_text("👍 Sei già registrato!")

# Funzione per inviare messaggi a tutte le chat registrate
async def send_to_all(message):
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            print(f"Errore inviando a {chat_id}: {e}")

# Controllo disponibilità
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
        await send_to_all(f"❌ Errore durante il check: {e}")
        print("Errore durante il check:", e)
        return

    available = data.get("AvailableDates", [])
    now = datetime.now()

    if available:
        await send_to_all(f"🎉 Tavolo trovato!\n\n{available}")
        print("Messaggio inviato: tavolo trovato!")
        last_heartbeat = now
    else:
        if now - last_heartbeat > timedelta(hours=1):
            await send_to_all("✅ Bot attivo, nessun tavolo disponibile.")
            last_heartbeat = now
            print("Messaggio di heartbeat inviato.")
        else:
            print("Nessun tavolo trovato, nessun messaggio inviato.")

# Loop principale
async def loop():
    global sleeping
    while True:
        now = datetime.now()
        if 0 <= now.hour < 8:
            if not sleeping:
                await send_to_all("💤 Bot in modalità sleep fino alle 8:00.")
                print("Bot in sleep...")
                sleeping = True

            # Dorme fino alle 8 del mattino
            sleep_seconds = (8 - now.hour) * 3600 - now.minute * 60 - now.second
            await asyncio.sleep(sleep_seconds)

            await send_to_all("🔔 Buongiorno! Bot riattivato.")
            print("Bot riattivato.")
            sleeping = False
        else:
            await check_availability()
            await asyncio.sleep(300)  # ogni 5 minuti

# Setup bot con handler /start
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Avvia il loop in background
    asyncio.create_task(loop())
    app.run_polling()
