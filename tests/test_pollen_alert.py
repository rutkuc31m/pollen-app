"""
Tests für pollen_alert.py
Run: pytest tests/test_pollen_alert.py -v
"""
import sys
import os
import pytest
from datetime import date
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pollen_alert as pa


# ─── fixtures ────────────────────────────────────────────────────────────────

def make_dwd_data(region_id=30, partregion_id=32):
    return {"content": [{
        "region_id": region_id,
        "partregion_id": partregion_id,
        "region_name": "Niedersachsen",
        "partregion_name": "Östl. Niedersachsen",
        "Pollen": {
            "Birke":    {"today": "3", "tomorrow": "2-3", "dayafter_to": "2"},
            "Hasel":    {"today": "0", "tomorrow": "0",   "dayafter_to": "0"},
            "Erle":     {"today": "1", "tomorrow": "1-2", "dayafter_to": "1"},
            "Esche":    {"today": "-1","tomorrow": "-1",  "dayafter_to": "-1"},
            "Graeser":  {"today": "0", "tomorrow": "0",   "dayafter_to": "0"},
            "Roggen":   {"today": "0", "tomorrow": "0",   "dayafter_to": "0"},
            "Beifuss":  {"today": "0", "tomorrow": "0",   "dayafter_to": "0"},
            "Ambrosia": {"today": "0", "tomorrow": "0",   "dayafter_to": "0"},
        },
    }]}


# ─── finde_region ────────────────────────────────────────────────────────────

class TestFindeRegion:
    def test_exact_match(self):
        r = pa.finde_region(make_dwd_data(30, 32))
        assert r is not None and r["partregion_id"] == 32

    def test_fallback_to_region_only(self):
        r = pa.finde_region(make_dwd_data(30, 99))
        assert r is not None and r["region_id"] == 30

    def test_returns_none_when_missing(self):
        assert pa.finde_region(make_dwd_data(99, 99)) is None

    def test_empty_content(self):
        assert pa.finde_region({"content": []}) is None

    def test_prefers_exact_match(self):
        daten = {"content": [
            {"region_id": 30, "partregion_id": 10, "Pollen": {}},
            {"region_id": 30, "partregion_id": 32, "Pollen": {}},
        ]}
        assert pa.finde_region(daten)["partregion_id"] == 32


# ─── format_level ────────────────────────────────────────────────────────────

class TestFormatLevel:
    def test_known_levels(self):
        assert "keine" in pa.format_level("0")
        assert "gering" in pa.format_level("1")
        assert "mittel" in pa.format_level("2")
        assert "hoch" in pa.format_level("3")
        assert "keine bis gering" in pa.format_level("0-1")

    def test_unknown_returns_raw(self):
        assert "99" in pa.format_level("99")

    def test_emojis_present(self):
        assert "🟢" in pa.format_level("0")
        assert "🔴" in pa.format_level("3")


# ─── erstelle_zusammenfassung ────────────────────────────────────────────────

class TestErstelleZusammenfassung:
    def _region(self):
        return make_dwd_data()["content"][0]

    def test_returns_tuple(self):
        text, aktiv = pa.erstelle_zusammenfassung(self._region(), date(2025, 4, 1))
        assert isinstance(text, str) and isinstance(aktiv, list)

    def test_aktiv_contains_active_pollen(self):
        _, aktiv = pa.erstelle_zusammenfassung(self._region(), date(2025, 4, 1))
        assert "Birke" in aktiv
        assert "Erle" in aktiv
        assert "Hasel" not in aktiv

    def test_no_aktiv_when_all_zero(self):
        region = {**self._region(), "Pollen": {
            k: {"today": "0", "tomorrow": "0", "dayafter_to": "0"}
            for k in pa.POLLEN_TYPES
        }}
        _, aktiv = pa.erstelle_zusammenfassung(region, date(2025, 7, 1))
        assert aktiv == []

    def test_text_contains_region(self):
        text, _ = pa.erstelle_zusammenfassung(self._region(), date(2025, 4, 1))
        assert "Niedersachsen" in text

    def test_text_contains_date(self):
        text, _ = pa.erstelle_zusammenfassung(self._region(), date(2025, 4, 1))
        assert "01.04.2025" in text

    def test_clear_message_when_no_pollen(self):
        region = {**self._region(), "Pollen": {
            k: {"today": "0", "tomorrow": "0", "dayafter_to": "0"}
            for k in pa.POLLEN_TYPES
        }}
        text, _ = pa.erstelle_zusammenfassung(region, date(2025, 7, 1))
        assert "✅" in text


# ─── main ────────────────────────────────────────────────────────────────────

class TestMain:
    def test_no_notification_when_no_active_pollen(self, capsys):
        region = {
            "region_id": 30, "partregion_id": 32,
            "region_name": "Test", "partregion_name": "Test",
            "Pollen": {k: {"today": "0", "tomorrow": "0", "dayafter_to": "0"}
                       for k in pa.POLLEN_TYPES}
        }
        with patch.object(pa, "lade_pollendaten", return_value={"content": [region]}):
            pa.main()
        out = capsys.readouterr().out
        assert "keine Benachrichtigung" in out

    def test_summary_printed_when_active(self, capsys):
        with patch.object(pa, "lade_pollendaten", return_value=make_dwd_data()):
            pa.main()
        out = capsys.readouterr().out
        assert "Birke" in out or "Erle" in out
