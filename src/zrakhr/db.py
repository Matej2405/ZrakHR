"""Pohrana u SQLite: postaje, mjerenja, prognoze i evidencija prikupljanja.

Sva vremena spremaju se u UTC-u kao tekst oblika 2026-11-17T22:00:00Z, pa se leksikografski
poredak poklapa s vremenskim i rasponi se mogu tražiti običnim usporedbama nizova.
Ponovljeno spremanje istog podatka ne stvara duplikat (INSERT OR IGNORE na prirodnom ključu).
"""

import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from zrakhr.collectors import Record

DEFAULT_PATH = Path("data/zrakhr.db")

# Povećava se uz svaku promjenu sheme; stara baza tada traži migraciju
SCHEMA_VERSION = 1

# Izvori i jesu li mjerenja ili prognoze; nazivi su isti kao atribut source kolektora
SOURCES = {
    "dhmz": "measurement",
    "azo": "measurement",
    "open-meteo-weather": "forecast",
    "open-meteo-air-quality": "forecast",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    name TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('measurement', 'forecast'))
);

CREATE TABLE IF NOT EXISTS stations (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL REFERENCES sources (name),
    external_id TEXT NOT NULL,  -- oznaka postaje u izvoru (DHMZ nema šifre, pa je to naziv)
    name TEXT NOT NULL,
    lat REAL,
    lon REAL,
    city TEXT,  -- grad projekta kojem postaja pripada; puni se pridruživanjem postaja gradovima
    UNIQUE (source, external_id)
);

-- Primarni ključ je ujedno indeks za upit "jedna postaja, jedna metrika, raspon vremena"
CREATE TABLE IF NOT EXISTS measurements (
    station_id INTEGER NOT NULL REFERENCES stations (id),
    metric TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    PRIMARY KEY (station_id, metric, observed_at)
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS measurements_observed_at ON measurements (observed_at);

-- Svako pokretanje prognoze (issue_time) čuva se zasebno, da se kasnije može ocijeniti
CREATE TABLE IF NOT EXISTS forecasts (
    station_id INTEGER NOT NULL REFERENCES stations (id),
    metric TEXT NOT NULL,
    issue_time TEXT NOT NULL,
    valid_time TEXT NOT NULL,
    lead_hours INTEGER NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    PRIMARY KEY (station_id, metric, issue_time, valid_time)
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS forecasts_valid_time ON forecasts (station_id, metric, valid_time);

CREATE TABLE IF NOT EXISTS collection_runs (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL REFERENCES sources (name),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'ok', 'failed')),
    records INTEGER NOT NULL DEFAULT 0,  -- novi zapisi; ponovljeni se ne broje
    rejected INTEGER NOT NULL DEFAULT 0,
    message TEXT
);
"""


def utc(moment: datetime | str) -> str:
    """Vrijeme s pomakom (datetime ili ISO 8601) u obliku koji se sprema, npr. 2026-11-17T22:00:00Z."""
    if isinstance(moment, str):
        moment = datetime.fromisoformat(moment)
    if moment.tzinfo is None:
        raise ValueError(f"vrijeme bez vremenske zone: {moment.isoformat()}")
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: Path = DEFAULT_PATH) -> sqlite3.Connection:
    """Otvara bazu (i stvara je ako ne postoji) s uključenim stranim ključevima."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Stvara tablice i upisuje izvore; ponovljeno pokretanje ništa ne mijenja."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise RuntimeError(f"baza ima shemu verzije {version}, a kod podržava {SCHEMA_VERSION}")
    conn.executescript(SCHEMA)
    conn.executemany("INSERT OR IGNORE INTO sources (name, kind) VALUES (?, ?)", SOURCES.items())
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()


def save_station(conn: sqlite3.Connection, source: str, external_id: str, name: str | None = None,
                 lat: float | None = None, lon: float | None = None, city: str | None = None) -> int:
    """Dodaje postaju ili joj osvježava podatke; vraća njezin id. Nepoznate vrijednosti se ne brišu."""
    conn.execute(
        """
        INSERT INTO stations (source, external_id, name, lat, lon, city) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (source, external_id) DO UPDATE SET
            name = excluded.name,
            lat = coalesce(excluded.lat, lat),
            lon = coalesce(excluded.lon, lon),
            city = coalesce(excluded.city, city)
        """,
        (source, external_id, name or external_id, lat, lon, city),
    )
    row = conn.execute("SELECT id FROM stations WHERE source = ? AND external_id = ?",
                       (source, external_id)).fetchone()
    return int(row[0])


def _station_ids(conn: sqlite3.Connection, records: list[Record]) -> dict[tuple[str, str], int]:
    """Id postaje za svaki (izvor, lokacija) iz zapisa; postaje koje ne postoje se dodaju."""
    ids: dict[tuple[str, str], int] = {}
    for record in records:
        key = (record["source"], record["location"])
        if key not in ids:
            row = conn.execute("SELECT id FROM stations WHERE source = ? AND external_id = ?",
                               key).fetchone()
            ids[key] = int(row[0]) if row else save_station(conn, *key)
    return ids


def insert_measurements(conn: sqlite3.Connection, records: Iterable[Record]) -> int:
    """Sprema mjerenja; vraća broj novih, a već spremljena (ista postaja, metrika i sat) preskače."""
    records = list(records)
    ids = _station_ids(conn, records)
    before = conn.total_changes
    conn.executemany(
        "INSERT OR IGNORE INTO measurements (station_id, metric, observed_at, value, unit) "
        "VALUES (?, ?, ?, ?, ?)",
        [(ids[(r["source"], r["location"])], r["metric"], utc(r["timestamp"]), r["value"], r["unit"])
         for r in records],
    )
    conn.commit()
    return conn.total_changes - before


def insert_forecasts(conn: sqlite3.Connection, records: Iterable[Record], issue_time: datetime) -> int:
    """Sprema jedno pokretanje prognoze izdano u issue_time; vraća broj novih zapisa."""
    records = list(records)
    ids = _station_ids(conn, records)
    issued = utc(issue_time)
    rows = []
    for r in records:
        valid = datetime.fromisoformat(r["timestamp"])
        lead_hours = round((valid - issue_time).total_seconds() / 3600)
        rows.append((ids[(r["source"], r["location"])], r["metric"], issued, utc(valid), lead_hours,
                     r["value"], r["unit"]))
    before = conn.total_changes
    conn.executemany(
        "INSERT OR IGNORE INTO forecasts "
        "(station_id, metric, issue_time, valid_time, lead_hours, value, unit) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return conn.total_changes - before


def measurements_between(conn: sqlite3.Connection, station_id: int, metric: str,
                         start: datetime, end: datetime) -> list[sqlite3.Row]:
    """Mjerenja jedne postaje i metrike od start (uključivo) do end (isključivo), po vremenu."""
    return conn.execute(
        "SELECT observed_at, value, unit FROM measurements "
        "WHERE station_id = ? AND metric = ? AND observed_at >= ? AND observed_at < ? "
        "ORDER BY observed_at",
        (station_id, metric, utc(start), utc(end)),
    ).fetchall()


def start_run(conn: sqlite3.Connection, source: str) -> int:
    """Bilježi početak prikupljanja; vraća id pokretanja za finish_run."""
    cursor = conn.execute(
        "INSERT INTO collection_runs (source, started_at, status) VALUES (?, ?, 'running')",
        (source, utc(datetime.now(timezone.utc))),
    )
    conn.commit()
    return int(cursor.lastrowid or 0)


def finish_run(conn: sqlite3.Connection, run_id: int, ok: bool, records: int = 0, rejected: int = 0,
               message: str | None = None) -> None:
    """Bilježi kraj prikupljanja: uspjeh, broj novih i odbačenih zapisa te poruku o grešci."""
    conn.execute(
        "UPDATE collection_runs SET finished_at = ?, status = ?, records = ?, rejected = ?, message = ? "
        "WHERE id = ?",
        (utc(datetime.now(timezone.utc)), "ok" if ok else "failed", records, rejected, message, run_id),
    )
    conn.commit()
