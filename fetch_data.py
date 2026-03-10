#!/usr/bin/env python3
"""
Lädt DWD-Pollendaten und speichert relevante Region als data.json.
Wird von der GitHub Action täglich ausgeführt.
"""

import json
from datetime import date
from urllib.request import urlopen

DWD_URL = "https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json"
REGION_ID = 30
PARTREGION_ID = 32

with urlopen(DWD_URL, timeout=10) as resp:
    data = json.loads(resp.read().decode("utf-8"))

region = next(
    (r for r in data["content"]
     if r["region_id"] == REGION_ID and r["partregion_id"] == PARTREGION_ID),
    next((r for r in data["content"] if r["region_id"] == REGION_ID), None)
)

output = {
    "updated": date.today().isoformat(),
    "region_name": region["region_name"],
    "partregion_name": region["partregion_name"],
    "pollen": region["Pollen"],
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("✅ data.json aktualisiert.")
