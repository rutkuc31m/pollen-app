#!/usr/bin/env python3
"""
Täglicher Pollenflug-Alert für Hannover via DWD-Daten.
Läuft als GitHub Action – Credentials kommen aus Environment Variables.
"""

import json
import os
import smtplib
import sys
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.error import URLError
from urllib.request import urlopen

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


def erstelle_html(region_data, today):
    region_name = region_data.get("region_name", "")
    partregion_name = region_data.get("partregion_name", "")
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    pollen_obj = region_data.get("Pollen", {})

    rows = ""
    aktiv = []
    for key in POLLEN_TYPES:
        if key not in pollen_obj:
            continue
        daten = pollen_obj[key]
        heute_val = daten.get("today", "-1")
        morgen_val = daten.get("tomorrow", "-1")
        uebermorgen_val = daten.get("dayafter_to", "-1")
        name = POLLEN_NAMEN.get(key, key)

        def cell_color(v):
            colors = {
                "0": "#e8f5e9", "0-1": "#fff9c4", "1": "#fff9c4",
                "1-2": "#ffe0b2", "2": "#ffe0b2", "2-3": "#ffcdd2", "3": "#ffcdd2"
            }
            return colors.get(str(v), "#f5f5f5")

        rows += f"""
        <tr>
          <td style="padding:8px 12px;font-weight:500">{name}</td>
          <td style="padding:8px 12px;text-align:center;background:{cell_color(heute_val)}">{format_level(heute_val)}</td>
          <td style="padding:8px 12px;text-align:center;background:{cell_color(morgen_val)}">{format_level(morgen_val)}</td>
          <td style="padding:8px 12px;text-align:center;background:{cell_color(uebermorgen_val)}">{format_level(uebermorgen_val)}</td>
        </tr>"""

        if heute_val not in ("-1", "0"):
            aktiv.append(name)

    hinweis = (
        f"<p style='color:#c62828'>⚠️ Heute aktiv: {', '.join(aktiv)}</p>"
        if aktiv else
        "<p style='color:#2e7d32'>✅ Heute keine nennenswerte Pollenbelastung.</p>"
    )

    html = f"""
<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:20px">
  <h2 style="color:#2e7d32">🌿 Pollenflug-Vorhersage</h2>
  <p><strong>{region_name}</strong><br><small>{partregion_name}</small></p>
  <p style="color:#666">Stand: {today.strftime('%d.%m.%Y')}</p>
  <table style="border-collapse:collapse;width:100%;margin-top:16px">
    <thead>
      <tr style="background:#e8f5e9">
        <th style="padding:10px 12px;text-align:left">Pollen</th>
        <th style="padding:10px 12px">Heute<br><small>{today.strftime('%d.%m.')}</small></th>
        <th style="padding:10px 12px">Morgen<br><small>{tomorrow.strftime('%d.%m.')}</small></th>
        <th style="padding:10px 12px">Übermorgen<br><small>{day_after.strftime('%d.%m.')}</small></th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  {hinweis}
  <hr style="margin-top:24px">
  <p style="color:#999;font-size:12px">Quelle: Deutscher Wetterdienst (DWD) – opendata.dwd.de</p>
</body></html>"""
    return html, aktiv


def sende_email(gmail, password, betreff, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = betreff
    msg["From"] = f"Pollenflug Alert <{gmail}>"
    msg["To"] = gmail
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail, password)
        server.sendmail(gmail, gmail, msg.as_string())
    print("✅ E-Mail erfolgreich gesendet.")


def main():
    gmail = os.environ.get("GMAIL_ADDRESS", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()

    if not gmail or not password:
        print("❌ GMAIL_ADDRESS und GMAIL_APP_PASSWORD müssen als Env-Variablen gesetzt sein.", file=sys.stderr)
        sys.exit(1)

    today = date.today()
    print("Lade DWD-Pollendaten...")
    daten = lade_pollendaten()

    region_data = finde_region(daten)
    if not region_data:
        print("❌ Region nicht gefunden.", file=sys.stderr)
        sys.exit(1)

    html, aktiv = erstelle_html(region_data, today)
    if not aktiv:
        print("✅ Heute keine nennenswerte Pollenbelastung – keine E-Mail gesendet.")
        return
    betreff = f"🌿 Pollenflug {today.strftime('%d.%m.%Y')} – {', '.join(aktiv)}"
    sende_email(gmail, password, betreff, html)


if __name__ == "__main__":
    main()
