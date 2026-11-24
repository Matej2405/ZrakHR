"""Testovi snimke zadnjih mjerenja za dashboard (zrakhr live), na bazi u privremenoj mapi."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from zrakhr import db
from zrakhr.__main__ import main
from zrakhr.collectors import Record
from zrakhr.live import build_snapshot

NOW = datetime(2026, 11, 24, 9, 5, tzinfo=timezone.utc)
UG = "μg/m³"


def record(source: str, location: str, metric: str, timestamp: str, value: float, unit: str) -> Record:
    return Record(source=source, location=location, metric=metric, timestamp=timestamp, value=value,
                  unit=unit)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "zrakhr.db"
    conn = db.connect(path)
    db.insert_measurements(conn, [
        record("azo", "155", "pm10", "2026-11-24T07:00:00+00:00", 31.0, UG),
        record("azo", "155", "pm10", "2026-11-24T06:00:00+00:00", 28.0, UG),
        # Starije od 48 sati: ne ulazi u trend
        record("azo", "155", "pm10", "2026-11-21T06:00:00+00:00", 99.0, UG),
        record("azo", "155", "pm2_5", "2026-11-24T07:00:00+00:00", 20.5, UG),
        # DHMZ sprema lokalno vrijeme s pomakom; u snimci je sve u UTC-u
        record("dhmz", "Zagreb-Maksimir", "temperature_2m", "2026-11-24T09:00:00+01:00", 4.2, "°C"),
        # Zadnje mjerenje starije od 24 sata: postaja nema trenutnih vrijednosti
        record("dhmz", "Stara postaja", "temperature_2m", "2026-11-22T09:00:00+00:00", 1.0, "°C"),
    ])
    conn.close()
    return path


@pytest.fixture
def conn(db_path: Path) -> sqlite3.Connection:
    connection = db.connect(db_path)
    yield connection
    connection.close()


def station(snapshot: dict, source: str, external_id: str) -> dict:
    [found] = [s for s in snapshot["stations"]
               if s["source"] == source and s["external_id"] == external_id]
    return found


def test_latest_value_per_metric_with_its_time(conn: sqlite3.Connection) -> None:
    """Za svaku metriku postaje ide zadnja vrijednost, s vremenom mjerenja u UTC-u."""
    azo = station(build_snapshot(conn, NOW), "azo", "155")

    assert azo["values"] == {
        "pm10": {"value": 31.0, "unit": UG, "observed_at": "2026-11-24T07:00:00Z"},
        "pm2_5": {"value": 20.5, "unit": UG, "observed_at": "2026-11-24T07:00:00Z"},
    }


def test_times_are_utc(conn: sqlite3.Connection) -> None:
    """DHMZ-ovo lokalno vrijeme (+01:00) u snimci je pretvoreno u UTC."""
    maksimir = station(build_snapshot(conn, NOW), "dhmz", "Zagreb-Maksimir")

    assert maksimir["values"]["temperature_2m"]["observed_at"] == "2026-11-24T08:00:00Z"


def test_pm10_trend_covers_last_48_hours(conn: sqlite3.Connection) -> None:
    """Trend PM10 ima vrijednosti iz zadnjih 48 sati, poredane po vremenu."""
    azo = station(build_snapshot(conn, NOW), "azo", "155")

    assert azo["trend"] == [["2026-11-24T06:00:00Z", 28.0], ["2026-11-24T07:00:00Z", 31.0]]
    assert station(build_snapshot(conn, NOW), "dhmz", "Zagreb-Maksimir")["trend"] == []


def test_stations_without_recent_measurements_are_left_out(conn: sqlite3.Connection) -> None:
    """Vrijednost starija od 24 sata nije trenutna, pa postaje nema u snimci."""
    snapshot = build_snapshot(conn, NOW)

    assert {(s["source"], s["external_id"]) for s in snapshot["stations"]} == {
        ("azo", "155"),
        ("dhmz", "Zagreb-Maksimir"),
    }
    assert snapshot["generated_at"] == "2026-11-24T09:05:00Z"


def test_live_command_writes_snapshot_and_summary(
    db_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Naredba zapisuje JSON i u prvi redak ispisuje sažetak za log prikupljanja."""
    out = tmp_path / "live" / "latest.json"

    assert main(["live", "--db", str(db_path), "--out", str(out)]) == 0

    snapshot = json.loads(out.read_text(encoding="utf-8"))
    assert {s["source"] for s in snapshot["stations"]} <= {"azo", "dhmz"}
    assert capsys.readouterr().out.splitlines()[0].startswith("live: postaje s mjerenjima DHMZ ")
