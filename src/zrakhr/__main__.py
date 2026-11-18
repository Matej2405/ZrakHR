"""Naredbeni redak, npr. ``python -m zrakhr collect --source dhmz`` ili ``python -m zrakhr db init``."""

import argparse
import json
import logging
import sys
import xml.etree.ElementTree as ET
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from zrakhr import db
from zrakhr.cities import CITIES, City
from zrakhr.collectors import (
    BaseCollector,
    DhmzCollector,
    OpenMeteoAirQualityCollector,
    OpenMeteoWeatherCollector,
    Record,
)

PREVIEW_ROWS = 5

logger = logging.getLogger(__name__)


def utc_stamp(moment: datetime) -> str:
    """Vremenska oznaka za imena datoteka, npr. 20261117T220000Z."""
    return moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def save_raw(raw: dict[str, Any], source: str, city: City, stamp: str, raw_dir: Path) -> Path:
    """Sprema sirovi odgovor u <raw_dir>/<izvor>_<grad>_<timestamp>.json."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{source}_{city.slug}_{stamp}.json"
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def print_preview(records: list[Record]) -> None:
    """Ispisuje prvih nekoliko zapisa kao tablicu."""
    print(f"  {'location':<20}  {'timestamp':<25}  {'metric':<20}  {'value':>8}  unit")
    for record in records[:PREVIEW_ROWS]:
        print(f"  {record['location']:<20}  {record['timestamp']:<25}  {record['metric']:<20}  "
              f"{record['value']:>8}  {record['unit']}")


def cmd_fetch(args: argparse.Namespace) -> int:
    """Pokreće sve kolektore za zadani grad; vraća 1 ako barem jedan nije uspio."""
    city = CITIES[args.city]
    stamp = utc_stamp(datetime.now(timezone.utc))
    collectors: list[BaseCollector] = [OpenMeteoWeatherCollector(), OpenMeteoAirQualityCollector()]

    failed = 0
    for collector in collectors:
        try:
            raw = collector.fetch(city)
        except requests.RequestException:
            failed += 1  # kolektor je grešku već zapisao u log
            continue
        path = save_raw(raw, collector.source, city, stamp, args.raw_dir)
        records = collector.normalize(raw, city)
        print(f"\n{collector.source} / {city.name}: {len(records)} normaliziranih zapisa")
        print(f"  sirovi odgovor: {path}")
        print_preview(records)
    return 1 if failed else 0


def cmd_collect(args: argparse.Namespace) -> int:
    """Dohvaća tekući sat DHMZ-ova feeda, sprema sirovi XML i zapise u bazu te ispisuje sažetak.

    Vraća 1 ako ne uspije. Prvi redak ispisa je sažetak koji scripts/collect.sh upisuje u log
    prikupljanja. Svako pokretanje, uspješno ili ne, bilježi se u tablici collection_runs.
    """
    collector = DhmzCollector()
    with closing(db.connect(args.db)) as conn:
        run = db.start_run(conn, collector.source)
        try:
            xml = collector.fetch()
        except requests.RequestException as exc:
            db.finish_run(conn, run, ok=False, message=str(exc))
            return 1  # kolektor je grešku već zapisao u log
        args.raw_dir.mkdir(parents=True, exist_ok=True)

        try:
            snapshot = collector.parse(xml)
        except (ET.ParseError, ValueError) as exc:
            # Sirovi odgovor se sprema i kad ga nije moguće obraditi, da podatak ne propadne
            path = args.raw_dir / f"{collector.source}_{utc_stamp(datetime.now(timezone.utc))}_neobradeno.xml"
            path.write_bytes(xml)
            logger.error("%s: odgovor nije moguće obraditi (%s); spremljen je u %s",
                         collector.source, exc, path)
            db.finish_run(conn, run, ok=False, message=f"neobradiv odgovor: {exc}")
            return 1

        # Ime nosi vrijeme opažanja, pa ponovljeno prikupljanje istog sata prepisuje istu datoteku
        path = args.raw_dir / f"{collector.source}_{utc_stamp(snapshot.observed_at)}.xml"
        path.write_bytes(xml)
        for name, (lat, lon) in snapshot.coordinates.items():
            db.save_station(conn, collector.source, name, name, lat, lon)
        stored = db.insert_measurements(conn, snapshot.records)
        db.finish_run(conn, run, ok=True, records=stored, rejected=len(snapshot.rejected))

    print(f"{collector.source} {snapshot.observed_at.isoformat()}: postaje {snapshot.stations}, "
          f"zapisi {len(snapshot.records)}, odbačene vrijednosti {len(snapshot.rejected)}, "
          f"novih u bazi {stored}")
    print(f"  sirovi odgovor: {path}")
    for rejected in snapshot.rejected:
        print(f"  odbačeno: {rejected['location']}, {rejected['metric']} = {rejected['raw']!r} "
              f"({rejected['reason']})")
    print_preview(snapshot.records)
    return 0


def cmd_db_init(args: argparse.Namespace) -> int:
    """Stvara bazu i tablice; na postojećoj bazi ništa ne mijenja."""
    with closing(db.connect(args.db)) as conn:
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    print(f"baza {args.db}: tablice {', '.join(tables)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Definira naredbe i argumente CLI-ja."""
    parser = argparse.ArgumentParser(
        prog="zrakhr",
        description="Prikupljanje podataka o vremenu i kvaliteti zraka za hrvatske gradove.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    fetch = commands.add_parser("fetch", help="dohvati podatke za jedan grad")
    fetch.add_argument("--city", required=True, choices=CITIES, help="naziv grada")
    fetch.add_argument("--raw-dir", type=Path, default=Path("data/raw"),
                       help="mapa za sirove JSON odgovore (zadano: data/raw)")
    fetch.set_defaults(func=cmd_fetch)

    collect = commands.add_parser("collect", help="spremi tekući sat mjerenja s izvora")
    collect.add_argument("--source", required=True, choices=("dhmz",),
                         help="izvor mjerenja (zasad dhmz)")
    collect.add_argument("--raw-dir", type=Path, default=Path("data/raw"),
                         help="mapa za sirove odgovore (zadano: data/raw)")
    collect.add_argument("--db", type=Path, default=db.DEFAULT_PATH,
                         help=f"SQLite baza (zadano: {db.DEFAULT_PATH.as_posix()})")
    collect.set_defaults(func=cmd_collect)

    database = commands.add_parser("db", help="upravljanje bazom")
    database_commands = database.add_subparsers(dest="db_command", required=True)
    init = database_commands.add_parser("init", help="stvori bazu i tablice")
    init.add_argument("--db", type=Path, default=db.DEFAULT_PATH,
                      help=f"SQLite baza (zadano: {db.DEFAULT_PATH.as_posix()})")
    init.set_defaults(func=cmd_db_init)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ulazna točka CLI-ja."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
