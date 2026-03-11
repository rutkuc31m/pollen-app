#!/usr/bin/env python3
"""
Täglicher Pollenflug-Alert – Hannover via DWD-Daten.
Notification-Kanal: wird ergänzt (Telegram geplant).
"""

import json
import os
import sys
from datetime import date, timedelta
from urllib.error import URLError
from urllib.request import urlopen, Request

DWD_URL = "https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json"

LEVEL_MAP = {
    "-1": ("⬜", "keine Daten"),
    "0":  ("🟢", "keine"),
    "0-1": ("🟡", "keine bis gering"),
    "1":  ("🟡", "gering"),
    "1-2": ("🟠", "gering bis mittel"),
    "2":  ("🟠", "mittel"),
    "2-3": ("🔴", "mittel bis hoch"),
    "3":  ("🔴", "hoch"),
}

POLLEN_NAMEN = {
    "Graeser": "Gräser",
    "Roggen": "Roggen",
    "Ambrosia": "Ambrosia",
    "Beifuss": "Beifuß",
    "Birke": "Birke",
    "Erle": "Erle",
    "Hasel": "Hasel",
    "Esche": "Esche",
}

POLLEN_TYPES = ["Graeser", "Roggen", "Birke", "Erle", "Hasel", "Esche", "Beifuss", "Ambrosia"]
REGION_ID = 30
PARTREGION_ID = 32  # Östl. Niedersachsen (Hannover)


def lade_pollendaten():
    try:
        with urlopen(DWD_URL, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        print(f"Fehler beim Laden der DWD-Daten: {e}", file=sys.stderr)
        sys.exit(1)


def finde_region(daten):
    for eintrag in daten.get("content", []):
        if (eintrag.get("region_id") == REGION_ID and
                eintrag.get("partregion_id") == PARTREGION_ID):
            return eintrag
    for eintrag in daten.get("content", []):
        if eintrag.get("region_id") == REGION_ID:
            return eintrag
    return None


def format_level(wert):
    emoji, text = LEVEL_MAP.get(str(wert), ("❓", str(wert)))
    return f"{emoji} {text}"


SCORE_MAP = {"-1": 0, "0": 0, "0-1": 1, "1": 1, "1-2": 2, "2": 2, "2-3": 3, "3": 3}

def max_score(pollen_obj, day_key):
    return max((SCORE_MAP.get(str(p.get(day_key, "-1")), 0) for p in pollen_obj.values()), default=0)

def erstelle_zusammenfassung(region_data, today):
    """Gibt (text, aktiv) zurück – text ist HTML-formatiert für Telegram."""
    pollen_obj = region_data.get("Pollen", {})
    aktiv = []
    heute_zeilen = []
    morgen_zeilen = []

    for key in POLLEN_TYPES:
        if key not in pollen_obj:
            continue
        name = POLLEN_NAMEN.get(key, key)
        heute_val  = pollen_obj[key].get("today",    "-1")
        morgen_val = pollen_obj[key].get("tomorrow", "-1")

        if heute_val not in ("-1", "0"):
            aktiv.append(name)
            heute_zeilen.append(f"{format_level(heute_val)}  <b>{name}</b>")

        if morgen_val not in ("-1", "0"):
            morgen_zeilen.append(f"{format_level(morgen_val)}  {name}")

    region_name = region_data.get("partregion_name") or region_data.get("region_name", "")
    tomorrow    = today + timedelta(days=1)

    # Trend arrow
    sc_heute  = max_score(pollen_obj, "today")
    sc_morgen = max_score(pollen_obj, "tomorrow")
    trend = " ↑" if sc_morgen > sc_heute else (" ↓" if sc_morgen < sc_heute else "")

    lines = [
        f"🌿 <b>Pollenflug · {today.strftime('%d.%m.%Y')}</b>",
        f"📍 {region_name}",
        "",
    ]

    if aktiv:
        lines.append(f"<b>Heute{trend}</b>")
        lines += heute_zeilen
    else:
        lines.append("✅ <b>Keine nennenswerte Belastung heute.</b>")

    if morgen_zeilen:
        lines += ["", f"<b>Morgen · {tomorrow.strftime('%d.%m.')}</b>"]
        lines += morgen_zeilen

    # Tip
    if sc_heute >= 2:
        lines += ["", "💊 Antihistaminikum empfohlen"]
    if sc_heute >= 3:
        lines.append("🪟 Fenster geschlossen halten")

    lines += [
        "",
        f'🔗 <a href="https://rutkuc31m.github.io/pollen-app">Forecast öffnen</a>',
    ]

    return "\n".join(lines), aktiv


def main():
    today = date.today()
    print("Lade DWD-Pollendaten...")
    daten = lade_pollendaten()

    region_data = finde_region(daten)
    if not region_data:
        print("❌ Region nicht gefunden.", file=sys.stderr)
        sys.exit(1)

    text, aktiv = erstelle_zusammenfassung(region_data, today)
    print(text)

    if not aktiv:
        print("Keine aktiven Pollen – keine Benachrichtigung gesendet.")
        return

    sende_telegram(text)


def sende_telegram(text):
    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("⚠️  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID nicht gesetzt – übersprungen.")
        return
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()
    req = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                print("✅ Telegram-Nachricht gesendet.")
    except Exception as e:
        print(f"❌ Telegram-Fehler: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
