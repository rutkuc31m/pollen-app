# Pollen App

PWA für Pollenflug-Monitoring mit Wetter, Symptom-Tracking und persönlichen Auslösern.

**Live:** https://pollenapp.is-a.dev · https://rutkuc31m.github.io/pollen-app

---

## Features

### Pollen-Tab
- **Hero-Karte** mit aktuellem Belastungslevel (Balken-System)
- **3-Tages-Streifen** mit Tagesauswahl
- **Pollen-Liste** mit Tag-Dropdown (Heute / Morgen / Übermorgen)
- **Verlaufschart** (letzte 7 Tage)
- **Nearby-Regionen** mit Vergleich
- **Saisonkalender**
- **Allergieprofil** — eigene Sensitivität je Pollen einstellen
- **Korrelations-Insight** — persönliche Auslöser aus Symptomhistorie (Pearson-r, letzte 90 Tage)

### Wetter-Tab
- **Aktuelle Bedingungen** (Temp, Wind, Feuchte, Regen, UV)
- **Sonne/Mond-Zeile** (Aufgang, Untergang, Mondphase, Gefühlte Temp, Windrichtung)
- **3-Tage-Vorschau** direkt in der Wetter-Karte
- **7-Tage-Vorschau** als eigene Karte (jeder Tag eine Zeile)
- **Temperaturkurve** stündlich (SVG, 00–21 Uhr)
- **Regenwahrscheinlichkeit** stündlich
- **Luftqualität** (AQI, PM10, PM2.5 via Open-Meteo)
- **Beste Zeit draußen** (nur DE, basierend auf Pollenbelastung + Wetter)

### Symptom-Tracker (Drawer)
- Täglich Symptome erfassen: Niesen, Augen, Atmung, Müdigkeit (Skala 0–3)
- **Medikamenten-Tracking** (Antihistamin, Augentropfen, Nasenspray, Cortison)
- **Wirksamkeitsanalyse** — Ø Symptomreduktion mit vs. ohne Medikament
- **Symptomverlauf** (Punktediagramm)
- **Prognose** für morgen basierend auf Verlauf

### Technisch
- Vanilla JS, Single-File PWA (`index.html`, ~4000 Zeilen)
- **Nur Dark Mode** — kein Theme-Toggle
- Offline-fähig via Service Worker
- Automatische Standorterkennung (ipwho.is + Nominatim)
- i18n: Deutsch · English · Türkçe

---

## Datenmodi

| Modus | Quelle | Regionen |
|-------|--------|----------|
| `de` | DWD Open Data | 27 deutsche Regionen |
| `om` | Open-Meteo CAMS | Weltweit |

Standard beim Start: Auto-Erkennung via IP — `de` für Deutschland, `om` sonst.

---

## Projektstruktur

```
pollen-app/
├── index.html              # PWA (Vanilla JS, Single File)
├── sw.js                   # Service Worker (pollen-v12)
├── manifest.json           # PWA Manifest
├── icon.svg                # App-Icon
├── apple-touch-icon.png    # iOS Icon
├── fetch_data.py           # Holt alle 27 DWD-Regionen → data.json
├── pollen_alert.py         # E-Mail Alert (Gmail)
├── data.json               # Täglich via GitHub Actions aktualisiert
├── test_app.py             # Test-Agent (83 Tests)
├── CNAME                   # pollenapp.is-a.dev
└── .github/workflows/
    └── daily_pollen.yml    # Täglich: fetch → commit → E-Mail
```

---

## Setup (Fork)

### 1. Repository forken

```bash
git clone https://github.com/rutkuc31m/pollen-app.git
cd pollen-app
```

### 2. GitHub Secrets setzen

**Settings → Secrets and variables → Actions**

| Secret | Beschreibung |
|--------|-------------|
| `GMAIL_ADDRESS` | Gmail-Adresse für den Alert |
| `GMAIL_APP_PASSWORD` | Gmail App-Passwort (nicht das normale Passwort) |

### 3. GitHub Pages aktivieren

**Settings → Pages → Source: Deploy from branch → `main` / (root)**

Dashboard erreichbar unter `https://USERNAME.github.io/pollen-app`

### 4. Region anpassen

In `fetch_data.py` und `pollen_alert.py` die Region-ID anpassen.
DWD-Regionen: `region_id` + `partregion_id` aus der [DWD-API](https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json).

---

## GitHub Actions

Die Action läuft täglich um **11:00 UTC** (12:00 CET / 13:00 CEST):

1. `fetch_data.py` — aktualisiert `data.json` mit allen 27 DWD-Regionen
2. Committet `data.json` automatisch
3. `pollen_alert.py` — sendet E-Mail falls Belastung aktiv

Manuell auslösen: **Actions → Täglicher Pollenflug-Alert → Run workflow**

---

## Datenquellen

- **DWD Open Data** — kostenlos, kein API-Key: `opendata.dwd.de/climate_environment/health/alerts/s31fg.json`
- **Open-Meteo** — Wetter + Luftqualität + CAMS Pollen: `open-meteo.com`
- **ipwho.is** — Standorterkennung via IP
- **Nominatim** — Reverse Geocoding (Stadtname)
