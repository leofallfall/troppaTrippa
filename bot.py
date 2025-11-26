import os
import asyncio
import json
import requests
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime, timedelta

TOKEN = os.environ["BOT_TOKEN"]
bot = Bot(token=TOKEN)

# File locale per salvare tutti i chat ID
CHAT_FILE = "chats.json"

# Stato
last_heartbeat = datetime.min
sleeping = False


# -------------------------------
# GESTIONE CHAT MULTIPLE
# -------------------------------

def load_chats():
    if os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return []
    return []


def save_chats(chats):
    with open(CHAT_FILE, "w") as f:
        json.dump(chats, f)


async def register_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registra un nuovo chat_id quando un utente fa /start"""
    chat_id = update.effective_chat.id
    chats = load_chats()

    if chat_id not in chats:
        chats.append(chat_id)
        save_chats(chats)
        print(f"Nuova chat registrata: {chat_id}")

    await update.message.reply_text("🟢 Bot attivo! Riceverai notifiche sulla disponibilità tavoli.")


async def send_all(text: str):
    """Invia un messaggio a TUTTE le chat registrate"""
    chats = load_chats()
    for chat_id in chats:
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            print(f"Errore con chat {chat_id}: {e}")


# -------------------------------
# CHECK DISPONIBILITÀ
# -------------------------------

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
        # heartbeat ogni ora
        #if now - last_heartbeat > timedelta(hours=1):
            await send_all("✅ Bot attivo, nessun tavolo disponibile.")
            last_heartbeat = now
            print("Heartbeat inviato.")


# -------------------------------
# LOOP PRINCIPALE
# -------------------------------

async def main_loop():
    global sleeping

    while True:
        now = datetime.now()

        # Modalità sleep dalle 00:00 alle 08:00
        if 0 <= now.hour < 8:
            if not sleeping:
                await send_all("💤 Bot in modalità sleep fino alle 8:00.")
                print("Bot in sleep.")
                sleeping = True

            # calcola quanto dormire fino alle 8
            sleep_seconds = (8 - now.hour) * 3600 - now.minute * 60 - now.second
            await asyncio.sleep(max(60, sleep_seconds))  # minimo 1 minuto (sicurezza)

            await send_all("🔔 Buongiorno! Bot riattivato.")
            print("Bot riattivato.")
            sleeping = False

        else:
            await check_availability()
            await asyncio.sleep(300)  # ogni 5 min


# -------------------------------
# START BOT TELEGRAM
# -------------------------------

async def start_bot():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", register_chat))

    # Avvia Telegram polling in parallelo
    await application.initialize()
    await application.start()
    print("📡 Telegram bot avviato.")

    # Avvia il loop principale
    await main_loop()


if __name__ == "__main__":
    asyncio.run(start_bot())
