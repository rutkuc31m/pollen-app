# 🌿 Pollenflug Alert – Hannover

Tägliche Pollenflug-Benachrichtigung per E-Mail + Web-Dashboard.
Daten: Deutscher Wetterdienst (DWD), kostenlos, kein API-Key nötig.

## Setup

### 1. GitHub Repository erstellen
Neues **öffentliches** Repo auf github.com erstellen, dann:
```bash
cd ~/pollen-app
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/DEIN-USERNAME/pollen-app.git
git push -u origin main
```

### 2. GitHub Secrets setzen
Im Repo: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Wert |
|------|------|
| `GMAIL_ADDRESS` | deine@gmail.com |
| `GMAIL_APP_PASSWORD` | dein-app-passwort |

### 3. GitHub Pages aktivieren
Im Repo: **Settings → Pages → Source: Deploy from branch → main / (root)**

→ Web-Dashboard erreichbar unter `https://DEIN-USERNAME.github.io/pollen-app`

### 4. E-Mail testen
Im Repo: **Actions → Täglicher Pollenflug-Alert → Run workflow**

## Automatisch
- E-Mail täglich um **07:00 Uhr** (läuft in der Cloud, PC muss nicht an sein)
- Web-Dashboard immer aktuell (lädt live von DWD)
