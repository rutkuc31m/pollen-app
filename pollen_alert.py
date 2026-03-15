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

DWD_URL     = "https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json"
WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=52.37&longitude=9.73"
    "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
    "precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,"
    "uv_index_max,weather_code"
    "&timezone=Europe%2FBerlin&forecast_days=2"
)

WMO = {
    0:"☀️", 1:"🌤", 2:"⛅", 3:"☁️",
    45:"🌫", 48:"🌫",
    51:"🌦", 53:"🌦", 55:"🌧",
    61:"🌧", 63:"🌧", 65:"🌧",
    71:"🌨", 73:"🌨", 75:"❄️",
    80:"🌦", 81:"🌧", 82:"⛈",
    95:"⛈", 96:"⛈", 99:"⛈",
}

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


def lade_wetter():
    try:
        with urlopen(WEATHER_URL, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        d = data["daily"]
        return {
            "temp_max": d["temperature_2m_max"][0],
            "temp_min": d["temperature_2m_min"][0],
            "rain":     d["precipitation_sum"][0],
            "rain_prob":d["precipitation_probability_max"][0],
            "wind":     d["wind_speed_10m_max"][0],
            "gusts":    d["wind_gusts_10m_max"][0],
            "uv":       d["uv_index_max"][0],
            "icon":     WMO.get(d["weather_code"][0], "🌡"),
        }
    except Exception:
        return None


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

def uv_kategorie(uv):
    if uv is None:  return ""
    if uv <= 2:     return "niedrig"
    if uv <= 5:     return "mäßig"
    if uv <= 7:     return "hoch"
    if uv <= 10:    return "sehr hoch"
    return "extrem"


def erstelle_zusammenfassung(region_data, today, wetter=None):
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
        f"<b>{today.strftime('%d.%m.%Y')} · {region_name}</b>",
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

    # Wetter
    if wetter:
        uv_kat = uv_kategorie(wetter['uv'])
        regen = f"🌧 {wetter['rain']} mm ({wetter['rain_prob']}%)" if wetter['rain'] > 0 else f"🌂 Kein Regen ({wetter['rain_prob']}%)"
        lines += [
            "",
            f"<b>Wetter heute</b>",
            f"{wetter['icon']} {wetter['temp_min']}° – {wetter['temp_max']}°C",
            f"💨 {wetter['wind']} km/h  ·  Böen {wetter['gusts']} km/h",
            f"{regen}",
            f"☀️ UV {wetter['uv']} – {uv_kat}",
        ]

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

    print("Lade Wetterdaten...")
    wetter = lade_wetter()

    text, aktiv = erstelle_zusammenfassung(region_data, today, wetter)
    print(text)

    if not aktiv:
        print("Keine aktiven Pollen – keine Benachrichtigung gesendet.")
        return

    sende_discord(text)


def sende_discord(text):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip().replace("\n", "").replace("\r", "").replace(" ", "")
    if not webhook_url:
        print("⚠️  DISCORD_WEBHOOK_URL nicht gesetzt – übersprungen.")
        return
    # Discord verwendet Markdown, kein HTML – einfache Konvertierung
    import re
    md = text.replace("<b>", "**").replace("</b>", "**") \
             .replace("<i>", "*").replace("</i>", "*")
    md = re.sub(r'<a href="([^"]+)">([^<]+)</a>', r'[\2](\1)', md)
    payload = json.dumps({"content": md, "username": "🌿 Pollenflug"}).encode()
    req = Request(webhook_url, data=payload, headers={"Content-Type": "application/json", "User-Agent": "PollenflugBot/1.0"})
    try:
        with urlopen(req, timeout=10) as resp:
            if resp.status in (200, 204):
                print("✅ Discord-Nachricht gesendet.")
    except Exception as e:
        print(f"❌ Discord-Fehler: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
