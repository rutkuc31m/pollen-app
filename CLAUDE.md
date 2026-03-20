# Pollen-App – CLAUDE.md

Vollständige technische Dokumentation für KI-Assistenten.

## Projekt-Übersicht

Täglicher Pollenflug-Alert + Web-Dashboard als PWA.
- **Live:** https://rutkuc31m.github.io/pollen-app
- **Repo:** https://github.com/rutkuc31m/pollen-app
- **Nutzer:** rutkuc31m@gmail.com · Hannover 30167

## Architektur

**Single-file PWA** – alles in `index.html` (Vanilla JS, ~3000 Zeilen).
Kein Build-System, kein Framework, kein Node.js. Direkt auf GitHub Pages.

```
pollen-app/
├── index.html          # Komplette App (HTML + CSS + JS in einer Datei)
├── sw.js               # Service Worker – Offline/PWA, Cache-Version: pollen-v7
├── manifest.json       # PWA Manifest (Icons, Theme #16a34a grün)
├── fetch_data.py       # GitHub Action: DWD → data.json
├── pollen_alert.py     # GitHub Action: Discord-Benachrichtigung
├── data.json           # Täglich committet von GitHub Action (alle 27 DWD-Regionen)
├── icon.svg            # App-Icon (grünes Blatt)
├── apple-touch-icon.png
└── .github/workflows/
    └── daily_pollen.yml  # Cron 11:00 UTC täglich
```

## Modi (appMode)

Die App hat 4 Daten-Modi, automatisch erkannt via ipwho.is IP-Geolocation:

| Mode | Trigger | Datenquelle | Pollen-Typen |
|------|---------|-------------|--------------|
| `"de"` | Land = DE | `./data.json` (DWD, täglich via GitHub Action) | 8 Typen |
| `"eu"` | Alles andere | Open-Meteo Air Quality (CAMS, live) | 6 Typen |
| `"us"` | Land = US/CA/MX | Open-Meteo Air Quality (CAMS, live) | 3 Typen |
| `"tr"` | Land = TR | Open-Meteo Air Quality (CAMS, live) | 4 Typen |

**Manueller Override** gespeichert in `localStorage("p_mode")`. Null = Auto.

### Auto-Erkennung (init)
```js
const autoCC = geoInfo?.country_code?.toUpperCase();
const resolvedMode = manualMode ?? (
  autoCC === "DE" ? "de" : autoCC === "TR" ? "tr" :
  (autoCC==="US"||autoCC==="CA"||autoCC==="MX") ? "us" : "eu"
);
```

## Pollen-Daten

### POLLEN_DE (8 Typen, aus DWD data.json)
```js
["hasel","erle","esche","birke","graeser","roggen","beifuss","ambrosia"]
```
DWD-Skala 0–3 direkt verwendet. -1 = keine Daten.

### POLLEN_EU (6 Typen, Open-Meteo CAMS)
birch, alder, grass, mugwort, ragweed, olive

### POLLEN_US (3 Typen, Open-Meteo CAMS)
tree, grass, ragweed

### POLLEN_TR (4 Typen, Open-Meteo CAMS)
olive, grass, mugwort, ragweed

### Open-Meteo Variablen
```js
const OM_VARS = {
  eu: ["alder_pollen","birch_pollen","grass_pollen","mugwort_pollen","ragweed_pollen","olive_pollen"],
  us: ["tree_pollen","grass_pollen","ragweed_pollen"],
  tr: ["grass_pollen","mugwort_pollen","ragweed_pollen","olive_pollen"],
};
```
Schwellwerte grains/m³ → Level (low/mid/high) in `OM_THR`.
**Wichtig:** `pollenAvailable` prüft auf `!== null` (nicht `> 0`), da 0 = off-season aber valide Daten.

### Türkei-Modus (TR)
10 vordefinierte Städte in `TR_CITIES` mit Koordinaten.
`loadTR()` findet nächste Stadt via `Math.hypot(lat-diff, lon-diff)`, zeigt Dropdown.
`fetchTRCity(city)` ruft Open-Meteo für exakte Koordinaten ab.
Offline-Cache in `localStorage("p_cache_tr")`.

## Daten-Flow

### DE-Modus
```
GitHub Action (11:00 UTC täglich)
  → fetch_data.py → DWD API → data.json (committed)
  → pollen_alert.py → Discord Webhook

Browser
  → loadDE() → fetch("./data.json") → render()
```

### EU/US/TR-Modus
```
Browser
  → loadGlobal() / loadTR() → Open-Meteo API (live) → render()
```

## APIs

| API | URL | Key nötig |
|-----|-----|-----------|
| DWD Open Data | `opendata.dwd.de/climate_environment/health/alerts/s31fg.json` | Nein |
| Open-Meteo Air Quality | `air-quality-api.open-meteo.com/v1/air-quality` | Nein |
| Open-Meteo Forecast | `api.open-meteo.com/v1/forecast` | Nein |
| ipwho.is | `ipwho.is/` | Nein |

**Alle APIs kostenlos, kein Key erforderlich.**

## GitHub Action

```yaml
# .github/workflows/daily_pollen.yml
# Cron: 0 11 * * * (11:00 UTC = 12:00 CET / 13:00 CEST)
```

Schritte:
1. `python fetch_data.py` → `data.json` mit allen 27 DWD-Regionen
2. `git add data.json && git commit && git push`
3. `python pollen_alert.py` → Discord-Benachrichtigung

**GitHub Secrets:**
- `DISCORD_WEBHOOK_URL` – Discord Webhook für täglichen Alert

## DWD-Regionen

Hannover = `region_id=30, partregion_id=32` → `rKey = "30-32"`.
Default `rKey` = `"30-32"` (Östl. Niedersachsen).
27 Regionen total in `data.json`.

## State / localStorage

```js
const LS = {
  region: "p_rgn",   // aktuelle DWD-Region z.B. "30-32"
  filter: "p_flt",   // Pollen-Filter Array (aktive Typen)
  syms:   "p_sym",   // Symptom-Einträge nach Datum
  cache:  "p_cache", // data.json Offline-Cache
  theme:  "p_theme", // "dark" | "light"
  hist:   "p_hist",  // Pollen-Verlauf nach Datum
  open:   "p_open",  // aufgeklappte Sections (Set)
  mode:   "p_mode",  // manueller Modus-Override ("de"|"eu"|"us"|"tr"|null)
  sev:    "p_sev",   // Allergie-Schwere pro Pollen ("off"|"mild"|"strong")
  lang:   "p_lang",  // Sprache ("de"|"en"|"tr")
};
// Plus: "p_flt_tr" (TR-spezifischer Filter), "p_cache_om", "p_cache_tr"
```

## Sprachen / i18n

3 Sprachen: DE, EN, TR. Buttons oben rechts im Header.

```js
let lang = localStorage.getItem("p_lang") || (navigator.language.startsWith("de") ? "de" : "en");
function t(key) {
  return STRINGS[lang]?.[key] ?? STRINGS.en?.[key] ?? STRINGS.de[key] ?? key;
}
```

Fallback-Kette: `lang → en → de → key`.
`setLang(newLang)` – aktualisiert Buttons, Logo-Text, ruft `render()` nur wenn `db` geladen.

## Service Worker (sw.js)

```js
const CACHE_VERSION = "pollen-v7";  // erhöhen bei Breaking Changes!
```

- **Network-first:** `data.json` (frische Pollendaten wichtig)
- **Cache-first:** alle statischen Assets
- **Offline:** zeigt gecachte Version mit Offline-Pill

**Wichtig:** Bei Breaking Changes in index.html immer `CACHE_VERSION` erhöhen!

## UI-Komponenten

### Header / Topbar
- Menü-Button (Drawer)
- Logo "🌿 Pollenflug" (DE) / "🌿 Pollen" (EN) / "🌿 Polen" (TR)
- Sprach-Buttons (DE/EN/TR) – joined button group, `border-right:none` auf DE/EN
- Theme-Toggle (🌙/☀️)

### Regionbar
- **DE:** `<select id="region-sel">` mit allen 27 DWD-Regionen + GPS-Button 📍
- **EU/US:** Location-Name + Relocate-Button 🔄
- **TR:** `<select id="tr-city-sel">` mit 10 Städten + GPS-Button 📍
- **Src-Bar darunter:** 🌐 DE EU TR US Buttons + 🔗 Share-Button

### Haupt-Sections (alle collapsible)
1. **Hero-Karte** – persönliches Risiko, Ampel-Farbe
2. **Wetter & Polen-Einfluss** – Open-Meteo Forecast, UV, Wind, Regen
3. **3-Day Strip** – Heute/Morgen/Übermorgen mit Wetter
4. **Pollen-Tabelle** – alle Typen mit Icons, Saison, 3-Tages-Spalten
5. **Verlauf** – Heatmap aus localStorage
6. **Symptom-Tracker** – Niesen/Augen/Atmung 0–5, Pearson-r Korrelation
7. **Saisonkalender** – Monats-Grid, aufklappbar (Standard: zu)
8. **Legende** – aufklappbar (Standard: zu)

### Drawer (Menü)
- Meine Allergien (Pollen-Filter + Schwere: off/mild/strong)
- Export/Import JSON
- Share URL (`?rgn=XX-XX&flt=key1,key2`)
- Legende

## Wichtige Funktionen

```js
init()              // App-Start: ipwho.is → Mode → loadDE/loadGlobal/loadTR
render()            // Alles neu zeichnen (nutzt globales db, filter, rKey, etc.)
loadDE()            // Fetcht data.json, baut Region-Dropdown, ruft render()
loadGlobal()        // EU/US: Open-Meteo Air Quality, ruft render()
loadTR()            // TR: findet nächste Stadt, ruft fetchTRCity()
fetchTRCity(city)   // Open-Meteo für TR-Stadtkoordinaten
renderSrcBar()      // DE/EU/TR/US Buttons + Share-Button
renderTRBar(sel)    // TR Stadtauswahl-Dropdown
setMode(mode)       // Modus wechseln (null = auto), speichert in localStorage
setLang(lang)       // Sprache wechseln, updatet Buttons, ruft render() wenn db geladen
setSeverity(key,lv) // Allergie-Schwere setzen, in-place DOM update (kein collapse!)
personalRisk()      // Gewichtetes Risiko: mild=70%, strong=100%
loadWeather()       // Open-Meteo Forecast für aktuelle Region/Stadt
geoLocate()         // Browser GPS → nächste DWD-Region
relocateTR()        // Browser GPS → nächste TR-Stadt
exportData()        // JSON-Download: Symptome + Verlauf
importData(event)   // JSON-Import
shareUrl()          // ?rgn=...&flt=... in Clipboard
todayISO()          // "YYYY-MM-DD" heute
```

## Allergie-Profil / Severity

```js
// Gespeichert als: { "birke": "strong", "gras": "mild", "hasel": "off" }
// personalRisk() Gewichtung:
//   "off"    → pollen zählt NICHT
//   "mild"   → weight 0.7
//   "strong" → weight 1.0
```

`setSeverity()` macht in-place DOM-Update via `data-sev-key` + `data-sev-val` Attribute
(verhindert dass Drawer-Section einklappt).

## Pegel-System (LV)

```
"-1" → Keine Daten (grau, –)
"0"  → Keine Belastung
"1"  → Geringe Belastung (grün)
"2"  → Mittlere Belastung (gelb)
"3"  → Hohe Belastung (rot)
```

Pollen-Tabelle zeigt auch Übergangswerte ("0-1", "1-2", "2-3") für DWD-Daten.

## Bekannte Eigenheiten / Fallstricke

1. **`setLang()` nur rendern wenn db geladen** – `if (db) { render(); renderSrcBar(); }` sonst Crash
2. **Season-Review Grid:** `repeat(12, minmax(0, 1fr))` nicht `1fr` (sonst ungleiche Spalten durch Text-Breite)
3. **Sprach-Buttons:** DE/EN haben `border-right:none` inline. Für active state `btn.style.border = "1px solid var(--accent)"` setzen (überschreibt border-right:none). Beim Deaktivieren `btn.style.borderRight = "none"` wiederherstellen.
4. **pollenAvailable:** Prüft `!== null`, NICHT `> 0` (0 = off-season = valide Daten)
5. **dayafter_to:** Der dritte Tag heißt im DAYS-Array `"dayafter_to"` (nicht `"dayafter"`)
6. **SW Cache-Version** immer erhöhen wenn index.html breaking changes hat
7. **TR Stadtauswahl:** `tr-city-sel` addEventListener muss nach innerHTML gesetzt werden

## Deployment

Automatisch: Jeder Push auf `main` → GitHub Pages deployed `index.html`.
GitHub Pages aktiviert unter: Settings → Pages → Deploy from branch → main / (root).

## Discord Alert

`pollen_alert.py` liest `data.json` für Region 30-32 (Hannover).
Sendet Webhook nur wenn Belastung > 0 für mindestens einen Pollen.
Enthält: Wetter-Block (Temp, Wind, UV, Regen), Pollen-Liste mit Emoji-Ampel.

## Tests

```
tests/  # Vorhanden aber minimal, manuell testen via GitHub Actions → Run workflow
```
