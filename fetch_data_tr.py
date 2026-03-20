#!/usr/bin/env python3
"""
Lädt Pollen-Daten für Türkei via Google Pollen API → data_tr.json
Wird täglich von der GitHub Action ausgeführt (API-Key aus Secret).
"""

import json
import os
from urllib.request import urlopen, Request
from datetime import datetime, timezone

API_KEY = os.environ.get("GOOGLE_POLLEN_API_KEY", "")

CITIES = [
    {"name": "İstanbul",    "lat": 41.0082, "lon": 28.9784},
    {"name": "Ankara",      "lat": 39.9208, "lon": 32.8541},
    {"name": "İzmir",       "lat": 38.4192, "lon": 27.1287},
    {"name": "Antalya",     "lat": 36.8969, "lon": 30.7133},
    {"name": "Bursa",       "lat": 40.1885, "lon": 29.0610},
    {"name": "Adana",       "lat": 37.0000, "lon": 35.3213},
    {"name": "Konya",       "lat": 37.8746, "lon": 32.4932},
    {"name": "Trabzon",     "lat": 41.0053, "lon": 39.7228},
    {"name": "Erzurum",     "lat": 39.9043, "lon": 41.2679},
    {"name": "Diyarbakır",  "lat": 37.9144, "lon": 40.2306},
]

POLLEN_MAP = {
    "OLIVE":              "olive",
    "CYPRESS":            "cypress",
    "PLANE_OR_PLANETREE": "plane",
    "GRAMINALES":         "grass",
    "MUGWORT":            "mugwort",
    "RAGWEED":            "ragweed",
}


def upi_to_level(val):
    if val == 0: return "0"
    if val <= 2: return "1"
    if val <= 3: return "2"
    return "3"


def fetch_city(city):
    url = (
        f"https://pollen.googleapis.com/v1/forecast:lookup"
        f"?key={API_KEY}"
        f"&location.longitude={city['lon']}"
        f"&location.latitude={city['lat']}"
        f"&days=3"
        f"&languageCode=en"
    )
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    pollen = {k: {"today": "0", "tomorrow": "0", "dayafter": "0"} for k in POLLEN_MAP.values()}
    day_keys = ["today", "tomorrow", "dayafter"]

    for i, day in enumerate(data.get("dailyInfo", [])[:3]):
        dk = day_keys[i]
        for plant in day.get("plantInfo", []):
            mapped_key = POLLEN_MAP.get(plant.get("code"))
            if not mapped_key:
                continue
            val = plant.get("indexInfo", {}).get("value", 0)
            pollen[mapped_key][dk] = upi_to_level(val)

    return pollen


if not API_KEY:
    print("⚠️  GOOGLE_POLLEN_API_KEY not set – skipping TR data fetch.")
    raise SystemExit(0)

cities_data = []
for city in CITIES:
    try:
        pollen = fetch_city(city)
        cities_data.append({
            "name":   city["name"],
            "lat":    city["lat"],
            "lon":    city["lon"],
            "pollen": pollen,
        })
        print(f"✅ {city['name']}")
    except Exception as e:
        print(f"❌ {city['name']}: {e}")

output = {
    "last_update": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "cities":      cities_data,
}

with open("data_tr.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ data_tr.json updated – {len(cities_data)} cities.")
