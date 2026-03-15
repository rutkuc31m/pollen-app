# 🌿 Pollenflug – Hannover

Täglicher Pollenflug-Alert via Discord + Web-Dashboard.
Daten: Deutscher Wetterdienst (DWD), kostenlos, kein API-Key nötig.

**Live:** https://rutkuc31m.github.io/pollen-app

## Features

- 🌐 Web-Dashboard mit 3-Tages-Vorschau, Symptom-Tracker, Verlauf-Heatmap
- 📱 PWA – als App auf dem Homescreen speicherbar (iOS & Android)
- 🌍 DE / EU / US Modus (DWD + Open-Meteo)
- 💬 Tägliche Discord-Benachrichtigung (nur bei aktiver Belastung)
- 🌤 Wettereinfluss auf Pollenflug (Wind, Regen, UV)
- 📊 Symptom-Korrelation mit Pearson-r
- 🔌 Offline-fähig (Service Worker Cache)

## Setup

### 1. Repository forken / klonen

```bash
git clone https://github.com/rutkuc31m/pollen-app.git
cd pollen-app
```

### 2. GitHub Secret setzen

Im Repo: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Wert |
|------|------|
| `DISCORD_WEBHOOK_URL` | Webhook-URL aus Discord (Kanal → Einstellungen → Integrationen → Webhooks) |

### 3. GitHub Pages aktivieren

Im Repo: **Settings → Pages → Source: Deploy from branch → main / (root)**

→ Dashboard erreichbar unter `https://DEIN-USERNAME.github.io/pollen-app`

### 4. Testen

Im Repo: **Actions → Täglicher Pollenflug-Alert → Run workflow**

## Automatisch

- Discord-Alert täglich um **12:15 Uhr** (1h nach DWD-Update)
- Keine Nachricht bei keiner aktiver Pollenbelastung
- `data.json` wird täglich automatisch committet

## Projektstruktur

```
pollen-app/
├── index.html              # Web-Dashboard (Vanilla JS, Single File)
├── pollen_alert.py         # Discord-Alert (liest DWD-Daten, sendet Webhook)
├── fetch_data.py           # Holt alle 27 DWD-Regionen → data.json
├── data.json               # Täglich aktualisiert via GitHub Actions
├── sw.js                   # Service Worker (Offline / PWA)
├── manifest.json           # PWA Manifest
└── .github/workflows/
    └── daily_pollen.yml    # Action: fetch → commit → Discord
```

## Datenquelle

DWD Open Data – kostenlos, kein API-Key:
`https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json`
