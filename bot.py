import os
import time
import json
import requests
from datetime import datetime, timedelta

# --- CONFIG from env ---
API_URL = "https://booking.resdiary.com/api/Restaurant/TRATTORIATRIPPA/AvailabilityForDateRange"
TELEGRAM_TOKEN = os.getenv("8252130109:AAENcVUyBTVWHBeLI06Yj3yj6ePheBBp-kA")  # es. set via flyctl secrets
CHAT_ID = os.getenv("299064562")                # es. "@nomeCanale" or numeric id
PARTY_SIZE = int(os.getenv("PARTY_SIZE", "2"))
CHECK_DAYS = int(os.getenv("CHECK_DAYS", "7"))
POLL_SECONDS = int(os.getenv("POLL_SECONDS", str(5 * 60)))  # default 5 minuti
LAST_SEEN_FILE = os.getenv("LAST_SEEN_FILE", "last_seen.json")

# --- helpers ---
def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("TELEGRAM_TOKEN o CHAT_ID non impostati, salto invio.")
        return
    url = f"https://api.telegram.org/bot8252130109:AAENcVUyBTVWHBeLI06Yj3yj6ePheBBp-kA/sendMessage"
    try:
        resp = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print("Errore invio Telegram:", e)

def iso_date(dt: datetime):
    return dt.strftime("%Y-%m-%dT00:00:00")

def build_payload(start: datetime, end: datetime):
    return {
        "DateFrom": iso_date(start),
        "DateTo": iso_date(end),
        "PartySize": PARTY_SIZE,
        "ChannelCode": "ONLINE",
        "AreaId": None,
        "AvailabilityType": "Reservation",
        "PromotionId": None
    }

def normalize_available_item(item):
    """
    Ritorna una stringa identificativa dell'elemento di AvailableDates.
    Gestisce:
      - stringhe semplici
      - oggetti con chiavi comuni (Date, date, availableDate, Slot, Time)
    """
    if item is None:
        return ""
    if isinstance(item, str):
        return item
    if isinstance(item, (int, float)):
        return str(item)

    # dict -> cerca campi noti
    if isinstance(item, dict):
        # possibili chiavi
        for key in ("Date", "date", "AvailableDate", "availableDate", "Day"):
            if key in item and item[key]:
                return str(item[key])
        # cerca info sugli slot
        if "Slots" in item and isinstance(item["Slots"], list) and item["Slots"]:
            # crea una descrizione compatta
            slots = []
            for s in item["Slots"]:
                if isinstance(s, str):
                    slots.append(s)
                elif isinstance(s, dict):
                    # prova a leggere time/Start/StartTime
                    for k in ("Time","time","Start","start","StartTime","startTime"):
                        if k in s:
                            slots.append(str(s[k])); break
            return f"{item.get('Date','')}: " + ", ".join(slots) if slots else json.dumps(item)
        # fallback: serializza
        try:
            return json.dumps(item, ensure_ascii=False)
        except Exception:
            return str(item)

    # fallback
    return str(item)

def load_last_seen():
    try:
        with open(LAST_SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("seen", []))
    except FileNotFoundError:
        return set()
    except Exception as e:
        print("Errore caricamento last_seen:", e)
        return set()

def save_last_seen(seen_set):
    try:
        with open(LAST_SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump({"seen": list(seen_set)}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Errore salvataggio last_seen:", e)

# --- main check loop ---
def check_once():
    start = datetime.utcnow().date()
    end = start + timedelta(days=CHECK_DAYS)
    payload = build_payload(datetime.combine(start, datetime.min.time()),
                            datetime.combine(end, datetime.min.time()))
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    try:
        r = requests.post(API_URL, json=payload, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print("[ERROR] Chiamata API fallita:", e)
        return None

    # cerca AvailableDates (fallback a diversi nomi)
    available = data.get("AvailableDates") if isinstance(data, dict) else None
    if available is None:
        # gestioni alternative
        for key in ("availableDates", "AvailableDates", "available_dates", "dates"):
            if isinstance(data, dict) and key in data:
                available = data[key]
                break
    if available is None:
        # se il body è semplicemente una lista
        if isinstance(data, list):
            available = data
    if available is None:
        print("[WARN] Response senza AvailableDates previste:", data)
        return None

    # normalizza
    normalized = [normalize_available_item(x) for x in available]
    # rimuovi vuoti
    normalized = [n for n in normalized if n]

    return normalized

def main_loop():
    print("Bot avviato: controllo disponibilità ogni", POLL_SECONDS, "secondi")
    last_seen = load_last_seen()
    backoff = 1
    while True:
        try:
            items = check_once()
            if items is None:
                # errore nella chiamata -> backoff
                print("Nessun dato ottenuto. Backoff:", backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 300)  # fino a 5 min
                continue

            backoff = 1  # reset backoff on success
            current_set = set(items)
            new = current_set - last_seen
            if new:
                # crea messaggio leggibile
                text = "*🎉 TAVOLI DISPONIBILI!* \n\n"
                text += f"Persone: {PARTY_SIZE}\nPeriodo: {datetime.utcnow().date()} → {datetime.utcnow().date() + timedelta(days=CHECK_DAYS)}\n\n"
                text += "Nuove disponibilità trovate:\n"
                for n in sorted(new):
                    text += f"• {n}\n"
                text += "\n(Questo messaggio è automatico)"
                send_telegram_message(text)

                # aggiorna seen
                last_seen |= new
                save_last_seen(last_seen)
            else:
                print(f"[{datetime.utcnow().isoformat()}] Nessuna nuova disponibilità.")
        except Exception as e:
            print("Errore inatteso nel loop:", e)
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main_loop()
