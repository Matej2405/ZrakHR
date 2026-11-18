"""Testovi pohrane u SQLite (zrakhr.db) i naredbi koje pišu u bazu, bez mreže."""

import sqlite3
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from zrakhr import db
from zrakhr.__main__ import main
from zrakhr.collectors import DhmzCollector, Record

FIXTURE = Path(__file__).parent / "fixtures" / "hrvatska_n.xml"
CET = timezone(timedelta(hours=1))


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = db.connect(tmp_path / "test.db")
    yield connection
    connection.close()


def record(location: str, timestamp: str, value: float, metric: str = "pm10",
           source: str = "azo") -> Record:
    return Record(source=source, location=location, metric=metric, timestamp=timestamp,
                  value=value, unit="µg/m³")


def count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])


def test_init_is_idempotent_and_sets_schema_version(conn: sqlite3.Connection) -> None:
    """Ponovljeni init ne mijenja ništa, a izvori se upisuju samo jednom."""
    db.init_db(conn)

    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"sources", "stations", "measurements", "forecasts", "collection_runs"} <= tables
    assert count(conn, "sources") == len(db.SOURCES)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION


def test_newer_schema_is_refused(conn: sqlite3.Connection) -> None:
    """Stariji kod ne smije pisati u bazu novije sheme."""
    conn.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 1}")

    with pytest.raises(RuntimeError, match="verzije"):
        db.init_db(conn)


def test_times_are_stored_in_utc() -> None:
    """Lokalno vrijeme s pomakom pretvara se u UTC; vrijeme bez zone je greška."""
    assert db.utc("2026-11-17T23:00:00+01:00") == "2026-11-17T22:00:00Z"
    assert db.utc(datetime(2026, 7, 15, 14, tzinfo=timezone(timedelta(hours=2)))) == "2026-07-15T12:00:00Z"
    with pytest.raises(ValueError, match="zone"):
        db.utc("2026-11-17T23:00:00")


def test_repeated_measurements_are_not_duplicated(conn: sqlite3.Connection) -> None:
    """Isti sat iste postaje i metrike sprema se jednom, a novi sat se dodaje."""
    first = [record("Zagreb-Đorđićeva", "2026-11-17T23:00:00+01:00", 31.0)]

    assert db.insert_measurements(conn, first) == 1
    assert db.insert_measurements(conn, first) == 0
    assert db.insert_measurements(conn, [record("Zagreb-Đorđićeva", "2026-11-18T00:00:00+01:00", 28.0)]) == 1
    assert count(conn, "measurements") == 2
    assert count(conn, "stations") == 1


def test_station_details_are_kept_when_missing_in_update(conn: sqlite3.Connection) -> None:
    """Ponovno spremanje postaje bez koordinata ne briše postojeće."""
    station = db.save_station(conn, "dhmz", "Rijeka", "Rijeka", 45.337, 14.443)

    assert db.save_station(conn, "dhmz", "Rijeka") == station
    row = conn.execute("SELECT lat, lon FROM stations WHERE id = ?", (station,)).fetchone()
    assert (row["lat"], row["lon"]) == (45.337, 14.443)


def test_range_query_returns_one_week_in_order(conn: sqlite3.Connection) -> None:
    """Upit vraća samo traženu postaju, metriku i raspon [start, end), poredano po vremenu."""
    start = datetime(2026, 11, 2, tzinfo=CET)
    hours = [start + timedelta(hours=h) for h in range(-24, 8 * 24)]
    db.insert_measurements(conn, [record("Split-Polje", t.isoformat(), float(i))
                                  for i, t in enumerate(reversed(hours))])
    db.insert_measurements(conn, [record("Split-Polje", start.isoformat(), 1.0, metric="pm2_5"),
                                  record("Osijek-1", start.isoformat(), 1.0)])
    station = db.save_station(conn, "azo", "Split-Polje")

    rows = db.measurements_between(conn, station, "pm10", start, start + timedelta(days=7))

    assert len(rows) == 7 * 24
    assert rows[0]["observed_at"] == "2026-11-01T23:00:00Z"
    assert rows[-1]["observed_at"] == "2026-11-08T22:00:00Z"
    assert [r["observed_at"] for r in rows] == sorted(r["observed_at"] for r in rows)


def test_range_query_uses_the_primary_key_index(conn: sqlite3.Connection) -> None:
    """Upit za raspon ide po indeksu, pa ne usporava s rastom tablice."""
    plan = " ".join(row[-1] for row in conn.execute(
        "EXPLAIN QUERY PLAN SELECT observed_at, value, unit FROM measurements "
        "WHERE station_id = 1 AND metric = 'pm10' AND observed_at >= 'a' AND observed_at < 'b' "
        "ORDER BY observed_at"))

    assert "USING PRIMARY KEY" in plan
    assert "TEMP B-TREE" not in plan  # poredak dolazi iz indeksa, bez dodatnog sortiranja


def test_forecasts_keep_every_run_with_lead_time(conn: sqlite3.Connection) -> None:
    """Svako pokretanje prognoze je zaseban zapis; vrijeme unaprijed je u satima od izdavanja."""
    valid = "2026-11-18T12:00:00+01:00"
    morning = datetime(2026, 11, 18, 0, tzinfo=CET)
    noon = datetime(2026, 11, 18, 6, tzinfo=CET)
    forecast = [record("zagreb", valid, 40.0, source="open-meteo-air-quality")]

    assert db.insert_forecasts(conn, forecast, morning) == 1
    assert db.insert_forecasts(conn, forecast, morning) == 0
    assert db.insert_forecasts(conn, forecast, noon) == 1

    leads = [row[0] for row in conn.execute("SELECT lead_hours FROM forecasts ORDER BY issue_time")]
    assert leads == [12, 6]


def test_collect_stores_measurements_stations_and_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Prikupljanje sprema zapise, postaje s koordinatama i pokretanje; ponovljeno ne dodaje ništa."""
    monkeypatch.setattr(DhmzCollector, "fetch", lambda self: FIXTURE.read_bytes())
    args = ["collect", "--source", "dhmz", "--raw-dir", str(tmp_path / "raw"),
            "--db", str(tmp_path / "zrakhr.db")]

    assert main(args) == 0
    assert main(args) == 0

    summaries = [line for line in capsys.readouterr().out.splitlines() if line.startswith("dhmz ")]
    assert summaries[0].endswith("novih u bazi 26")
    assert summaries[1].endswith("novih u bazi 0")
    with sqlite3.connect(tmp_path / "zrakhr.db") as conn:
        assert count(conn, "measurements") == 26
        assert conn.execute("SELECT lat, lon FROM stations WHERE external_id = 'Rijeka'").fetchone() == (
            45.337, 14.443)
        runs = conn.execute("SELECT status, records, rejected FROM collection_runs ORDER BY id").fetchall()
        assert runs == [("ok", 26, 4), ("ok", 0, 4)]


def test_failed_collect_is_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Neobradiv odgovor bilježi neuspjelo pokretanje s razlogom."""
    monkeypatch.setattr(DhmzCollector, "fetch", lambda self: b"<Hrvatska></Hrvatska>")

    assert main(["collect", "--source", "dhmz", "--raw-dir", str(tmp_path),
                 "--db", str(tmp_path / "zrakhr.db")]) == 1
    with sqlite3.connect(tmp_path / "zrakhr.db") as conn:
        status, message = conn.execute("SELECT status, message FROM collection_runs").fetchone()
    assert status == "failed"
    assert "neobradiv" in message


def test_db_init_command_creates_database(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "nova" / "zrakhr.db"

    assert main(["db", "init", "--db", str(path)]) == 0

    assert path.exists()
    assert "measurements" in capsys.readouterr().out
