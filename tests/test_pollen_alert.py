"""
Tests für pollen_alert.py
Run: pytest tests/test_pollen_alert.py -v
"""
import sys
import os
import pytest
from datetime import date
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pollen_alert as pa


# ─── fixtures ────────────────────────────────────────────────────────────────

def make_dwd_data(region_id=30, partregion_id=32, extra_regions=None):
    """Minimal DWD-ähnliches JSON mit einer Region."""
    content = [
        {
            "region_id": region_id,
            "partregion_id": partregion_id,
            "region_name": "Niedersachsen",
            "partregion_name": "Östl. Niedersachsen",
            "Pollen": {
                "Birke": {"today": "3", "tomorrow": "2-3", "dayafter_to": "2"},
                "Hasel": {"today": "0", "tomorrow": "0", "dayafter_to": "0"},
                "Erle":  {"today": "1", "tomorrow": "1-2", "dayafter_to": "1"},
                "Esche": {"today": "-1", "tomorrow": "-1", "dayafter_to": "-1"},
                "Graeser":  {"today": "0", "tomorrow": "0", "dayafter_to": "0"},
                "Roggen":   {"today": "0", "tomorrow": "0", "dayafter_to": "0"},
                "Beifuss":  {"today": "0", "tomorrow": "0", "dayafter_to": "0"},
                "Ambrosia": {"today": "0", "tomorrow": "0", "dayafter_to": "0"},
            },
        }
    ]
    if extra_regions:
        content.extend(extra_regions)
    return {"content": content}


# ─── finde_region ────────────────────────────────────────────────────────────

class TestFindeRegion:
    def test_exact_match(self):
        daten = make_dwd_data(region_id=30, partregion_id=32)
        r = pa.finde_region(daten)
        assert r is not None
        assert r["region_id"] == 30
        assert r["partregion_id"] == 32

    def test_fallback_to_region_only(self):
        """Wenn partregion_id nicht passt, nimmt er erste mit region_id=30."""
        daten = make_dwd_data(region_id=30, partregion_id=99)
        r = pa.finde_region(daten)
        assert r is not None
        assert r["region_id"] == 30

    def test_returns_none_when_missing(self):
        daten = make_dwd_data(region_id=99, partregion_id=99)
        r = pa.finde_region(daten)
        assert r is None

    def test_empty_content(self):
        assert pa.finde_region({"content": []}) is None

    def test_prefers_exact_match_over_fallback(self):
        """Exact match (region_id=30, partregion_id=32) beats region-only fallback."""
        daten = {
            "content": [
                {"region_id": 30, "partregion_id": 10, "Pollen": {}},  # partial match
                {"region_id": 30, "partregion_id": 32, "Pollen": {}},  # exact match
            ]
        }
        r = pa.finde_region(daten)
        assert r["partregion_id"] == 32


# ─── format_level ────────────────────────────────────────────────────────────

class TestFormatLevel:
    def test_known_levels(self):
        assert "keine" in pa.format_level("0")
        assert "gering" in pa.format_level("1")
        assert "mittel" in pa.format_level("2")
        assert "hoch" in pa.format_level("3")
        assert "keine bis gering" in pa.format_level("0-1")
        assert "gering bis mittel" in pa.format_level("1-2")
        assert "mittel bis hoch" in pa.format_level("2-3")

    def test_unknown_level_returns_raw(self):
        result = pa.format_level("99")
        assert "99" in result

    def test_minus_one(self):
        result = pa.format_level("-1")
        assert "keine Daten" in result

    def test_emoji_present(self):
        assert "🟢" in pa.format_level("0")
        assert "🔴" in pa.format_level("3")


# ─── erstelle_html ────────────────────────────────────────────────────────────

class TestErstelleHtml:
    def _region(self):
        return make_dwd_data()["content"][0]

    def test_returns_tuple(self):
        html, aktiv = pa.erstelle_html(self._region(), date(2025, 4, 1))
        assert isinstance(html, str)
        assert isinstance(aktiv, list)

    def test_aktiv_contains_active_pollen(self):
        _, aktiv = pa.erstelle_html(self._region(), date(2025, 4, 1))
        # Birke=3, Erle=1 should be active; Hasel=0 should not
        assert "Birke" in aktiv
        assert "Erle" in aktiv
        assert "Hasel" not in aktiv

    def test_no_aktiv_when_all_zero(self):
        region = {
            "region_id": 30, "partregion_id": 32,
            "region_name": "Test", "partregion_name": "Test",
            "Pollen": {k: {"today": "0", "tomorrow": "0", "dayafter_to": "0"}
                       for k in pa.POLLEN_TYPES}
        }
        _, aktiv = pa.erstelle_html(region, date(2025, 7, 1))
        assert aktiv == []

    def test_html_contains_date(self):
        html, _ = pa.erstelle_html(self._region(), date(2025, 4, 1))
        assert "01.04.2025" in html

    def test_html_contains_region_name(self):
        html, _ = pa.erstelle_html(self._region(), date(2025, 4, 1))
        assert "Niedersachsen" in html

    def test_html_contains_warning_when_active(self):
        html, _ = pa.erstelle_html(self._region(), date(2025, 4, 1))
        assert "⚠️" in html

    def test_html_contains_clear_when_none(self):
        region = {
            "region_id": 30, "partregion_id": 32,
            "region_name": "Test", "partregion_name": "Test",
            "Pollen": {k: {"today": "0", "tomorrow": "0", "dayafter_to": "0"}
                       for k in pa.POLLEN_TYPES}
        }
        html, _ = pa.erstelle_html(region, date(2025, 7, 1))
        assert "✅" in html


# ─── sende_email (mocked) ────────────────────────────────────────────────────

class TestSendeEmail:
    def test_calls_smtp_login_and_sendmail(self):
        mock_server = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_server)
        mock_context.__exit__ = MagicMock(return_value=False)

        with patch("smtplib.SMTP_SSL", return_value=mock_context):
            pa.sende_email("test@gmail.com", "pw123", "Betreff", "<p>html</p>")

        mock_server.login.assert_called_once_with("test@gmail.com", "pw123")
        mock_server.sendmail.assert_called_once()
        args = mock_server.sendmail.call_args[0]
        assert args[0] == "test@gmail.com"  # from
        assert args[1] == "test@gmail.com"  # to


# ─── main integration ────────────────────────────────────────────────────────

class TestMain:
    def test_exits_without_env_vars(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.dict(os.environ, {"GMAIL_ADDRESS": "", "GMAIL_APP_PASSWORD": ""}):
                with pytest.raises(SystemExit) as exc:
                    pa.main()
                assert exc.value.code == 1

    def test_no_email_when_no_active_pollen(self):
        """Wenn keine Pollen aktiv, wird keine E-Mail gesendet."""
        region_data = {
            "region_id": 30, "partregion_id": 32,
            "region_name": "Test", "partregion_name": "Test",
            "Pollen": {k: {"today": "0", "tomorrow": "0", "dayafter_to": "0"}
                       for k in pa.POLLEN_TYPES}
        }
        dwd_data = {"content": [region_data]}

        with patch.dict(os.environ, {"GMAIL_ADDRESS": "a@b.com", "GMAIL_APP_PASSWORD": "pw"}):
            with patch.object(pa, "lade_pollendaten", return_value=dwd_data):
                with patch.object(pa, "sende_email") as mock_send:
                    pa.main()
                    mock_send.assert_not_called()

    def test_email_sent_when_pollen_active(self):
        dwd_data = make_dwd_data()  # Birke=3, Erle=1 → aktiv

        with patch.dict(os.environ, {"GMAIL_ADDRESS": "a@b.com", "GMAIL_APP_PASSWORD": "pw"}):
            with patch.object(pa, "lade_pollendaten", return_value=dwd_data):
                with patch.object(pa, "sende_email") as mock_send:
                    pa.main()
                    mock_send.assert_called_once()
                    betreff = mock_send.call_args[0][2]
                    assert "Birke" in betreff or "Erle" in betreff


