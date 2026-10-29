"""Regression tests for district and temporal boundaries in structured retrieval."""

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


@pytest.mark.parametrize(
    "start_year,end_year",
    [
        (2010, 2023),
        (2023, 2027),
        (2025, 2023),
        (0, 2023),
        (2023, 0),
        (True, 2023),
        (2023, False),
        ("2023", 2025),
        (2023, 2025.5),
    ],
)
def test_invalid_event_year_range_rejected_before_database(monkeypatch, start_year, end_year):
    def unexpected_connection():
        pytest.fail("Invalid year ranges must be rejected before opening the database")

    monkeypatch.setattr(structured_retriever, "get_connection", unexpected_connection)

    result = structured_retriever.get_events_by_type(
        "Cloudburst", "Kangra", start_year, end_year
    )

    assert result["status"] == "NO_SUPPORTED_EVIDENCE"
    assert result["count"] == 0
    assert result["events"] == []


@pytest.fixture
def events_database(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE extreme_weather_events (
            canonical_event_id TEXT, date TEXT, year INTEGER, district TEXT,
            primary_event_type TEXT, tehsil TEXT, panchayat_village TEXT,
            fatalities INTEGER, houses_damaged_fully INTEGER,
            financial_loss_inr_lakh REAL, primary_source TEXT, event_summary TEXT
        )"""
    )
    records = [
        (2010, "Kangra", "Cloudburst"),
        (2011, "Kangra", "Cloudburst"),
        (2023, "Kangra", "Cloudburst"),
        (2026, "Kangra", "Cloudburst"),
        (2027, "Kangra", "Cloudburst"),
        (2023, "Mandi", "Cloudburst"),
        (2023, "Kangra", "Flash Flood"),
    ]
    conn.executemany(
        "INSERT INTO extreme_weather_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (f"EVENT_{index}", f"{year}-07-01", year, district, event_type,
             None, None, 0, 0, 0.0, "TEST_SOURCE", "Fixture event")
            for index, (year, district, event_type) in enumerate(records)
        ],
    )
    monkeypatch.setattr(structured_retriever, "get_connection", lambda: conn)
    yield
    conn.close()


@pytest.mark.parametrize(
    "bounds,expected_years",
    [
        ({}, [2011, 2023]),
        ({"start_year": 2023, "end_year": 2023}, [2023]),
        ({"start_year": None, "end_year": None}, [2011, 2023, 2026]),
        ({"start_year": 2025, "end_year": None}, [2026]),
        ({"start_year": None, "end_year": 2012}, [2011]),
    ],
)
def test_event_year_range_filters_supported_records(events_database, bounds, expected_years):
    result = structured_retriever.get_events_by_type("Cloudburst", "Kangra", **bounds)

    assert result["status"] == "OK"
    assert result["count"] == len(expected_years)
    assert [event["year"] for event in result["events"]] == expected_years
    assert all(event["district"] == "Kangra" for event in result["events"])
    assert all(event["primary_event_type"] == "Cloudburst" for event in result["events"])
