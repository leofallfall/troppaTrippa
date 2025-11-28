import os
import asyncio
import requests
from datetime import datetime, timedelta

from telegram import Bot, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

# --- ENV ---
TOKEN = os.environ["BOT_TOKEN"]
CHAT_IDS = [int(cid) for cid in os.environ["CHAT_IDS"].split(",")]

bot = Bot(token=TOKEN)

# --- STATUS VARIABLES ---
last_heartbeat = datetime.min
last_found = None
bot_start_time = datetime.now()
next_check_eta = "N/D"
sleeping = False

# ============================================================
# 📌 FUNZIONI UTILI
# ============================================================

async def send_all(text: str):
    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            print(f"Errore con chat {chat_id}: {e}")

# ============================================================
# 📌 COMMAND HANDLERS
# ============================================================

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Sono attivo!")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *Comandi Disponibili*\n\n"
        "/ping – Testa se il bot è online\n"
        "/status – Stato attuale del bot\n"
        "/nextcheck – Quando sarà il prossimo controllo\n"
        "/uptime – Da quanto il bot è attivo\n"
        "/sleep – Forza la modalità notte\n"
        "/wake – Riattiva manualmente\n"
        "/help – Mostra questo menu\n"
    )
    await update.message.reply_markdown(help_text)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📊 *Stato del Bot*\n\n"
        f"• Modalità sleep: {'🛌 Sì' if sleeping else '☀️ No'}\n"
        f"• Ultima disponibilità trovata: {last_found if last_found else 'Mai'}\n"
        f"• Ultimo controllo effettuato: {last_heartbeat}\n"
        f"• Prossimo controllo: {next_check_eta}\n"
    )
    await update.message.reply_markdown(text)

async def cmd_uptime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    delta = datetime.now() - bot_start_time
    await update.message.reply_text(f"⏱️ Uptime: {delta}")

async def cmd_nextcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🔍 Prossimo check: {next_check_eta}")

async def cmd_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global sleeping
    sleeping = True
    await update.message.reply_text("😴 Sleep mode attivata manualmente.")

async def cmd_wake(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global sleeping
    sleeping = False
    await update.message.reply_text("🔔 Bot riattivato manualmente!")

# ============================================================
# 📌 CORE LOGIC: CHECK DISPONIBILITÀ
# ============================================================

async def check_availability():
    global last_heartbeat, last_found, next_check_eta

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
        print("❌ Errore durante il check:", e)
        return

    available = data.get("AvailableDates", [])
    last_heartbeat = now
    next_check_eta = now + timedelta(minutes=5)

    if available:
        last_found = now
        await send_all(f"🎉 *Tavolo trovato!*\n\n{available}")
        print("Messaggio inviato: tavolo trovato!")
        return

    # Heartbeat SOLO nei log
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Heartbeat OK – nessuna disponibilità")

# ============================================================
# 📌 MAIN LOOP
# ============================================================

async def loop():
    global sleeping, next_check_eta

    while True:
        now = datetime.now()

        # Modalità sleep automatica
        if 0 <= now.hour < 8 and not sleeping:
            sleeping = True
            await send_all("💤 Bot in modalità sleep fino alle 8:00.")
            print("Bot in sleep...")

        # Se sleep, non fare controlli
        if sleeping:
            print(f"[{now.strftime('%H:%M:%S')}] Sleep heartbeat")
            await asyncio.sleep(1800)

            if now.hour >= 8:
                sleeping = False
                await send_all("🔔 Buongiorno! Bot riattivato.")
                print("Bot riattivato.")
            continue

        # Controllo normale
        await check_availability()
        await asyncio.sleep(300)

# ============================================================
# 📌 ENTRYPOINT CORRETTO
# ============================================================

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("uptime", cmd_uptime))
    app.add_handler(CommandHandler("nextcheck", cmd_nextcheck))
    app.add_handler(CommandHandler("sleep", cmd_sleep))
    app.add_handler(CommandHandler("wake", cmd_wake))

    # Avvia polling Telegram
    asyncio.create_task(app.run_polling())

    # Esegui check immediato (se non è notte)
    hour = datetime.now().hour
    if not (0 <= hour < 8):
        print("Eseguo check immediato all’avvio...")
        await check_availability()
    else:
        print("Avvio in sleep, nessun check iniziale")

    # Avvia il loop principale
    await loop()

if __name__ == "__main__":
    asyncio.run(main())
