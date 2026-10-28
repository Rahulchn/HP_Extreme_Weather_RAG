"""Regression tests for district boundaries in structured retrieval."""

import sqlite3

import pytest

from scripts import structured_retriever


@pytest.mark.parametrize("district", ["Delhi", "Atlantis", "   "])
def test_unsupported_telemetry_district_rejected_before_database(monkeypatch, district):
    def unexpected_connection():
        pytest.fail("Unsupported districts must be rejected before opening the database")

    monkeypatch.setattr(structured_retriever, "get_connection", unexpected_connection)

    result = structured_retriever.get_telemetry_2026(district)

    assert result["status"] == "NO_SUPPORTED_EVIDENCE"
    assert result["records_count"] == 0
    assert result["records"] == []


@pytest.fixture
def telemetry_database(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE telemetry_rainfall (
            station_name TEXT, district TEXT, date TEXT, year INTEGER,
            timestamp_ist TEXT, rainfall_mm REAL, source_document TEXT
        )"""
    )
    conn.executemany(
        "INSERT INTO telemetry_rainfall VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("Kangra station", "Kangra", "2026-09-01", 2026,
             "2026-09-01T10:00:00", 12.5, "Kangra telemetry"),
            ("Mandi station", "Mandi", "2026-09-02", 2026,
             "2026-09-02T10:00:00", 25.0, "Mandi telemetry"),
        ],
    )
    monkeypatch.setattr(structured_retriever, "get_connection", lambda: conn)
    yield
    conn.close()


@pytest.mark.parametrize("district", ["Kangra", " kangra "])
def test_supported_telemetry_district_returns_only_its_records(telemetry_database, district):
    result = structured_retriever.get_telemetry_2026(district)

    assert result["status"] == "OK"
    assert result["records_count"] == 1
    assert result["records"][0]["district"] == "Kangra"
    assert result["records"][0]["rainfall_mm"] == 12.5
    assert result["year_status"] == "PARTIAL"


def test_omitted_telemetry_district_returns_all_records(telemetry_database):
    result = structured_retriever.get_telemetry_2026()

    assert result["status"] == "OK"
    assert result["records_count"] == 2
    assert [record["district"] for record in result["records"]] == ["Mandi", "Kangra"]
    assert result["year_status"] == "PARTIAL"
