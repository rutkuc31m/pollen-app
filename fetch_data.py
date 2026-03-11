#!/usr/bin/env python3
"""
Lädt alle DWD-Pollendaten und speichert sie als data.json.
"""

import json
from urllib.request import urlopen

DWD_URL = "https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json"

with urlopen(DWD_URL, timeout=10) as resp:
    raw = json.loads(resp.read().decode("utf-8"))

regions = []
for r in raw.get("content", []):
    regions.append({
        "region_id":      r.get("region_id"),
        "partregion_id":  r.get("partregion_id"),
        "region_name":    r.get("region_name", ""),
        "partregion_name": r.get("partregion_name", ""),
        "pollen":         r.get("Pollen", {}),
    })

output = {
    "last_update":  raw.get("last_update", ""),
    "next_update":  raw.get("next_update", ""),
    "regions":      regions,
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ data.json aktualisiert – {len(regions)} Regionen.")
