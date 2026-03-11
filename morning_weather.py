#!/usr/bin/env python3
"""
Täglicher Morgen-Wetterbericht für Hannover via Open-Meteo.
Schickt eine ausführliche Telegram-Nachricht mit allem was der Tag bringt.
"""

import json
import os
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError

LAT, LON = 52.37, 9.73
CITY = "Hannover"

WEATHER_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&current=temperature_2m,relative_humidity_2m,apparent_temperature"
    ",precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m,weather_code"
    "&daily=temperature_2m_max,temperature_2m_min"
    ",apparent_temperature_max,apparent_temperature_min"
    ",sunrise,sunset"
    ",precipitation_sum,precipitation_probability_max"
    ",wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant"
    ",uv_index_max,weather_code"
    "&timezone=Europe%2FBerlin&forecast_days=3"
)

WMO = {
    0:  ("☀️",  "Klar"),
    1:  ("🌤",  "Überwiegend klar"),
    2:  ("⛅",  "Teilweise bewölkt"),
    3:  ("☁️",  "Bewölkt"),
    45: ("🌫",  "Nebel"),
    48: ("🌫",  "Raureifnebel"),
    51: ("🌦",  "Leichter Nieselregen"),
    53: ("🌦",  "Nieselregen"),
    55: ("🌧",  "Starker Nieselregen"),
    61: ("🌧",  "Leichter Regen"),
    63: ("🌧",  "Regen"),
    65: ("🌧",  "Starker Regen"),
    71: ("🌨",  "Leichter Schneefall"),
    73: ("🌨",  "Schneefall"),
    75: ("❄️",  "Starker Schneefall"),
    77: ("🌨",  "Schneekörner"),
    80: ("🌦",  "Leichte Schauer"),
    81: ("🌧",  "Regenschauer"),
    82: ("⛈",  "Starke Schauer"),
    85: ("🌨",  "Leichte Schneeschauer"),
    86: ("❄️",  "Schneeschauer"),
    95: ("⛈",  "Gewitter"),
    96: ("⛈",  "Gewitter mit Hagel"),
    99: ("⛈",  "Gewitter mit Hagel"),
}

DAY_NAMES = ["Heute", "Morgen", "Übermorgen"]


def wmo(code):
    return WMO.get(code, ("🌡", f"Code {code}"))


def wind_dir(deg):
    dirs = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]
    return dirs[round(deg / 45) % 8]


def uv_kat(uv):
    if uv is None: return ""
    if uv <= 2:    return "niedrig"
    if uv <= 5:    return "mäßig"
    if uv <= 7:    return "hoch"
    if uv <= 10:   return "sehr hoch"
    return "extrem"


def zeitstr(iso):
    """'2026-03-11T06:42' → '06:42'"""
    return iso[11:16] if iso and "T" in iso else iso


def lade_wetter():
    try:
        with urlopen(WEATHER_URL, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        print(f"Fehler beim Laden der Wetterdaten: {e}", file=sys.stderr)
        sys.exit(1)


def erstelle_nachricht(data):
    c  = data["current"]
    d  = data["daily"]
    lines = []

    # Header
    cur_emoji, cur_desc = wmo(c["weather_code"])
    lines += [
        f"{cur_emoji} <b>Wetter {CITY}</b>",
        "",
        f"<b>Jetzt:</b> {round(c['temperature_2m'])}°C  "
        f"(gefühlt {round(c['apparent_temperature'])}°C)  "
        f"{cur_desc}",
        f"💧 Feuchte: {c['relative_humidity_2m']}%  "
        f"💨 {round(c['wind_speed_10m'])} km/h {wind_dir(c['wind_direction_10m'])}  "
        f"Böen {round(c['wind_gusts_10m'])} km/h",
    ]
    if c["precipitation"] > 0:
        lines.append(f"🌧 Aktuell: {c['precipitation']} mm")

    # 3-Tages-Forecast
    for i in range(3):
        d_emoji, d_desc = wmo(d["weather_code"][i])
        uv   = d["uv_index_max"][i]
        rain = d["precipitation_sum"][i]
        prob = d["precipitation_probability_max"][i]
        wmax = round(d["wind_speed_10m_max"][i])
        gust = round(d["wind_gusts_10m_max"][i])
        wdir = wind_dir(d["wind_direction_10m_dominant"][i])
        tmax = round(d["temperature_2m_max"][i])
        tmin = round(d["temperature_2m_min"][i])
        fmax = round(d["apparent_temperature_max"][i])
        fmin = round(d["apparent_temperature_min"][i])
        rise = zeitstr(d["sunrise"][i])
        sset = zeitstr(d["sunset"][i])

        lines += [
            "",
            f"<b>── {DAY_NAMES[i]} ──</b>",
            f"{d_emoji} {d_desc}",
            f"🌡 {tmin}° – {tmax}°C  (gefühlt {fmin}° – {fmax}°)",
        ]
        if rain > 0 or prob > 20:
            lines.append(f"🌧 Regen: {prob}%  |  {rain} mm")
        else:
            lines.append("🌧 Kein Regen erwartet")
        lines += [
            f"💨 Wind: {wmax} km/h {wdir}  |  Böen {gust} km/h",
            f"☀️ UV {uv} – {uv_kat(uv)}",
            f"🌅 {rise}  🌇 {sset}",
        ]

    lines += ["", '🔗 <a href="https://rutkuc31m.github.io/pollen-app">Pollen-Forecast</a>']
    return "\n".join(lines)


def sende_telegram(text):
    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("⚠️  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID nicht gesetzt.")
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
                print("✅ Telegram-Wetterbericht gesendet.")
    except Exception as e:
        print(f"❌ Telegram-Fehler: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    print("Lade Wetterdaten...")
    data = lade_wetter()
    text = erstelle_nachricht(data)
    print(text)
    sende_telegram(text)


if __name__ == "__main__":
    main()
