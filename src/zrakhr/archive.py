"""Spremanje obrađenih odgovora u bazu, učitavanje arhive sirovih odgovora i dnevna provjera.

Prikupljanje u GitHub Actionsu trajno čuva samo sirove odgovore (grana data); baza se iz njih
gradi naredbom ``zrakhr import``, pa se odgovori spremaju istim funkcijama kao pri prikupljanju.
"""

import json
import logging
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from zrakhr import db
from zrakhr.cities import CITIES, City
from zrakhr.collectors import (
    STATIONS,
    AzoCollector,
    AzoSnapshot,
    DhmzCollector,
    DhmzSnapshot,
    OpenMeteoAirQualityCollector,
    OpenMeteoWeatherCollector,
    Record,
)

logger = logging.getLogger(__name__)

FORECAST_COLLECTORS = {c.source: c for c in (OpenMeteoWeatherCollector(), OpenMeteoAirQualityCollector())}
CITIES_BY_SLUG = {city.slug: city for city in CITIES.values()}

# Koliko se puta dnevno očekuje podatak: mjerenja svaki sat, prognoza svakih 6 sati
EXPECTED_PER_DAY = {"measurement": 24, "forecast": 4}


def store_dhmz(conn: sqlite3.Connection, snapshot: DhmzSnapshot) -> int:
    """Sprema postaje i mjerenja jednog sata DHMZ-ova feeda; vraća broj novih zapisa."""
    for name, (lat, lon) in snapshot.coordinates.items():
        db.save_station(conn, "dhmz", name, name, lat, lon)
    return db.insert_measurements(conn, snapshot.records)


def store_azo(conn: sqlite3.Connection, snapshot: AzoSnapshot) -> int:
    """Sprema AZO-ove postaje (s gradom) i mjerenja; vraća broj novih zapisa."""
    for station in STATIONS:
        db.save_station(conn, "azo", str(station.id), station.name, station.lat, station.lon, station.city)
    return db.insert_measurements(conn, snapshot.records)


def store_forecast(conn: sqlite3.Connection, source: str, city: City, records: list[Record],
                   issued: datetime) -> int:
    """Sprema grad kao postaju i jedno pokretanje prognoze; vraća broj novih zapisa."""
    db.save_station(conn, source, city.name, city.name, city.latitude, city.longitude, city.name)
    return db.insert_forecasts(conn, records, issued)


@dataclass
class ImportStats:
    """Ishod učitavanja datoteka jednog izvora."""

    files: int = 0
    stored: int = 0
    failed: int = 0


def import_raw(conn: sqlite3.Connection, raw_dir: Path) -> dict[str, ImportStats]:
    """Učitava sve sirove odgovore iz raw_dir (i podmapa) u bazu, po izvoru.

    Ponovno učitavanje ne stvara duplikate. Datoteka koju nije moguće obraditi zapisuje se u
    log i broji kao neuspjela, a ostale se učitavaju. Datoteke *_neobradeno.* su već pri
    prikupljanju bile neobradive, pa se preskaču.
    """
    stats: dict[str, ImportStats] = {}
    for path in sorted(raw_dir.rglob("*")):
        if not path.is_file() or "_neobradeno" in path.stem:
            continue
        source = path.stem.split("_")[0]  # dhmz_<vrijeme>, azo_<vrijeme>, <izvor>_<grad>_<vrijeme>
        if source not in db.SOURCES:
            continue
        item = stats.setdefault(source, ImportStats())
        item.files += 1
        try:
            item.stored += _import_file(conn, source, path)
        except (OSError, ET.ParseError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.warning("%s: datoteku nije moguće učitati (%r)", path, exc)
            item.failed += 1
    return stats


def _import_file(conn: sqlite3.Connection, source: str, path: Path) -> int:
    """Učitava jednu sirovu datoteku; vraća broj novih zapisa."""
    if source == "dhmz":
        return store_dhmz(conn, DhmzCollector().parse(path.read_bytes()))
    raw = json.loads(path.read_text(encoding="utf-8"))
    if source == "azo":
        return store_azo(conn, AzoCollector().parse(raw["series"]))
    # <izvor>_<grad>_<vrijeme dohvata>.json; prognoza je izdana u punom satu dohvata
    _, slug, stamp = path.stem.rsplit("_", 2)
    city = CITIES_BY_SLUG[slug]
    fetched = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    issued = fetched.replace(minute=0, second=0)
    return store_forecast(conn, source, city, FORECAST_COLLECTORS[source].normalize(raw, city), issued)


def check_day(conn: sqlite3.Connection, day: date) -> list[tuple[str, bool]]:
    """Redak sažetka po izvoru za jedan dan (UTC) i je li izvor potpun.

    Za mjerenja broji sate s barem jednim zapisom i navodi sate bez zapisa, a za prognoze
    pokretanja prognoze izdana tog dana.
    """
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    bounds = (db.utc(start), db.utc(start + timedelta(days=1)))
    lines: list[tuple[str, bool]] = []
    for source, kind in db.SOURCES.items():
        table, column = ("measurements", "observed_at") if kind == "measurement" else ("forecasts", "issue_time")
        # Tablica i stupac su iz koda, ne od korisnika
        where = (f"FROM {table} JOIN stations ON stations.id = {table}.station_id"
                 f" WHERE stations.source = ? AND {column} >= ? AND {column} < ?")
        hours = {int(row[0]) for row in conn.execute(
            f"SELECT DISTINCT substr({column}, 12, 2) {where}", (source, *bounds))}
        records = conn.execute(f"SELECT count(*) {where}", (source, *bounds)).fetchone()[0]
        expected = EXPECTED_PER_DAY[kind]
        if kind == "measurement":
            line = f"{source} {day}: sati {len(hours)}/24, zapisi {records}"
            missing = _hour_ranges([h for h in range(24) if h not in hours])
            line += f", nedostaju sati (UTC) {missing}" if missing else ""
        else:
            line = f"{source} {day}: pokretanja prognoze {len(hours)}/{expected}, zapisi {records}"
        lines.append((line, len(hours) >= expected))
    return lines


def _hour_ranges(hours: list[int]) -> str:
    """Sati kao rasponi, npr. [0, 1, 2, 5] -> '00-02, 05'."""
    ranges: list[str] = []
    for hour in hours:
        if ranges and int(ranges[-1][-2:]) == hour - 1:
            ranges[-1] = f"{ranges[-1][:2]}-{hour:02d}"
        else:
            ranges.append(f"{hour:02d}")
    return ", ".join(ranges)
