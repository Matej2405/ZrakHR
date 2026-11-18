"""Naredbeni redak, npr. ``zrakhr collect --source azo``, ``zrakhr stations`` ili ``zrakhr db init``.

Izlazni kodovi: 0 ako je sve uspjelo, 1 ako izvor nije uspio, 2 za pogrešnu upotrebu.
"""

import argparse
import json
import logging
import sys
import xml.etree.ElementTree as ET
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from zrakhr import archive, db
from zrakhr.cities import CITIES, City
from zrakhr.collectors import (
    AzoCollector,
    BaseCollector,
    DhmzCollector,
    OpenMeteoAirQualityCollector,
    OpenMeteoWeatherCollector,
    Record,
)
from zrakhr.collectors.azo import TIMEZONE as AZO_TIMEZONE

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
    """Dohvaća Open-Meteo prognoze za zadani grad i sprema ih kao novo pokretanje prognoze.

    Vrijeme izdavanja je puni sat dohvata, pa ponovljeni dohvat u istom satu ne stvara duplikate.
    Vraća 1 ako barem jedan kolektor nije uspio.
    """
    city = CITIES[args.city]
    now = datetime.now(timezone.utc)
    stamp = utc_stamp(now)
    issued = now.replace(minute=0, second=0, microsecond=0)
    collectors: list[BaseCollector] = [OpenMeteoWeatherCollector(), OpenMeteoAirQualityCollector()]

    failed = 0
    with closing(db.connect(args.db)) as conn:
        for collector in collectors:
            run = db.start_run(conn, collector.source)
            try:
                raw = collector.fetch(city)
            except requests.RequestException as exc:
                db.finish_run(conn, run, ok=False, message=str(exc))
                failed += 1  # kolektor je grešku već zapisao u log
                continue
            path = save_raw(raw, collector.source, city, stamp, args.raw_dir)
            try:
                records = collector.normalize(raw, city)
            except (KeyError, TypeError, ValueError) as exc:
                logger.error("%s: odgovor nije moguće obraditi (%r); spremljen je u %s",
                             collector.source, exc, path)
                db.finish_run(conn, run, ok=False, message=f"neobradiv odgovor: {exc!r}")
                failed += 1
                continue
            stored = archive.store_forecast(conn, collector.source, city, records, issued)
            db.finish_run(conn, run, ok=True, records=stored)
            print(f"\n{collector.source} / {city.name}: prognoza izdana {issued.isoformat()}, "
                  f"zapisi {len(records)}, novih u bazi {stored}")
            print(f"  sirovi odgovor: {path}")
            print_preview(records)
    return 1 if failed else 0


def cmd_collect(args: argparse.Namespace) -> int:
    """Prikuplja mjerenja s odabranog izvora i sprema ih u bazu.

    Vraća 1 ako ne uspije i 2 za pogrešnu upotrebu. Prvi redak ispisa je sažetak koji
    scripts/collect.sh upisuje u log prikupljanja. Svako pokretanje, uspješno ili ne, bilježi se
    u tablici collection_runs.
    """
    if args.source == "azo":
        return collect_azo(args)
    if args.since is not None:
        logger.error("--since vrijedi samo za izvor azo; DHMZ objavljuje samo tekući sat")
        return 2
    return collect_dhmz(args)


def collect_dhmz(args: argparse.Namespace) -> int:
    """Dohvaća tekući sat DHMZ-ova feeda, sprema sirovi XML i zapise u bazu te ispisuje sažetak."""
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
        stored = archive.store_dhmz(conn, snapshot)
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


def collect_azo(args: argparse.Namespace) -> int:
    """Dohvaća AZO-ove satne nizove od --since (zadano: jučer) do danas, sprema sirovi JSON i zapise.

    Portal čuva povijest, pa isti dohvat služi i za satno prikupljanje i za dohvat unatrag;
    preklapanje s prethodnim pokretanjem ne stvara duplikate u bazi.
    """
    collector = AzoCollector()
    now = datetime.now(timezone.utc)
    today = now.astimezone(AZO_TIMEZONE).date()
    start = args.since or today - timedelta(days=1)
    if start > today:
        logger.error("--since %s je u budućnosti", start)
        return 2

    with closing(db.connect(args.db)) as conn:
        run = db.start_run(conn, collector.source)
        series, failed = collector.fetch(start, today)
        path = None
        if series:
            args.raw_dir.mkdir(parents=True, exist_ok=True)
            path = args.raw_dir / f"{collector.source}_{utc_stamp(now)}.json"
            raw = {"from": start.isoformat(), "to": today.isoformat(), "series": series}
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        try:
            snapshot = collector.parse(series)
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("%s: odgovor nije moguće obraditi (%r); spremljen je u %s",
                         collector.source, exc, path)
            db.finish_run(conn, run, ok=False, message=f"neobradiv odgovor: {exc!r}")
            return 1
        stored = archive.store_azo(conn, snapshot)
        db.finish_run(conn, run, ok=not failed, records=stored, rejected=len(snapshot.rejected),
                      message=f"nedohvaćeni nizovi: {', '.join(failed)}" if failed else None)

    print(f"{collector.source} {start.isoformat()} do {today.isoformat()}: nizovi {len(series)}, "
          f"zapisi {len(snapshot.records)}, odbačene vrijednosti {len(snapshot.rejected)}, "
          f"novih u bazi {stored}" + (f", nedohvaćeni nizovi {len(failed)}" if failed else ""))
    if path:
        print(f"  sirovi odgovor: {path}")
    if failed:
        print(f"  nedohvaćeni nizovi (postaja/tvar): {', '.join(failed)}")
    for rejected in snapshot.rejected:
        print(f"  odbačeno: {rejected['location']}, {rejected['metric']} = {rejected['raw']!r} "
              f"({rejected['reason']})")
    print_preview(snapshot.records[-PREVIEW_ROWS:])
    return 1 if failed else 0


def cmd_db_init(args: argparse.Namespace) -> int:
    """Stvara bazu i tablice; na postojećoj bazi ništa ne mijenja."""
    with closing(db.connect(args.db)) as conn:
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    print(f"baza {args.db}: tablice {', '.join(tables)}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    """Učitava arhivu sirovih odgovora u bazu; vraća 1 ako neku datoteku nije moguće učitati."""
    if not args.raw_dir.is_dir():
        logger.error("mapa %s ne postoji", args.raw_dir)
        return 2
    with closing(db.connect(args.db)) as conn:
        stats = archive.import_raw(conn, args.raw_dir)
    for source, item in stats.items():
        print(f"{source}: datoteke {item.files}, novih u bazi {item.stored}, neučitane {item.failed}")
    if not stats:
        print(f"u {args.raw_dir} nema sirovih odgovora")
    return 1 if any(item.failed for item in stats.values()) else 0


def cmd_check(args: argparse.Namespace) -> int:
    """Ispisuje redak po izvoru za jedan dan; vraća 1 ako nekom izvoru nedostaju sati ili prognoze."""
    day = args.date or datetime.now(timezone.utc).date() - timedelta(days=1)
    with closing(db.connect(args.db)) as conn:
        lines = archive.check_day(conn, day)
    for line, _ in lines:
        print(line)
    return 0 if all(complete for _, complete in lines) else 1


def cmd_stations(args: argparse.Namespace) -> int:
    """Ispisuje postaje iz baze, po izvoru i nazivu; postaje se upisuju pri prikupljanju."""
    query = "SELECT source, external_id, name, city, lat, lon FROM stations"
    params: tuple[str, ...] = ()
    if args.source:
        query += " WHERE source = ?"
        params = (args.source,)
    with closing(db.connect(args.db)) as conn:
        rows = conn.execute(query + " ORDER BY source, name", params).fetchall()
    if not rows:
        print(f"u bazi {args.db} nema postaja; upisuju se pri prikupljanju (zrakhr collect, zrakhr fetch)")
        return 0
    print(f"{'izvor':<22}  {'oznaka':<25}  {'naziv':<25}  {'grad':<15}  {'lat':>9}  {'lon':>9}")
    for source, external_id, name, city, lat, lon in rows:
        coords = f"{lat:>9.4f}  {lon:>9.4f}" if lat is not None and lon is not None else ""
        print(f"{source:<22}  {external_id:<25}  {name or '':<25}  {city or '':<15}  {coords}".rstrip())
    print(f"postaje: {len(rows)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Definira naredbe i argumente CLI-ja."""
    # Opcije zajedničke svim naredbama, da rade i iza naziva naredbe (zrakhr collect -v ...)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=db.DEFAULT_PATH,
                        help=f"SQLite baza (zadano: {db.DEFAULT_PATH.as_posix()})")
    common.add_argument("-v", "--verbose", action="store_true",
                        help="ispiši i pojedinosti rada (npr. svaki HTTP upit), ne samo upozorenja i greške")

    parser = argparse.ArgumentParser(
        prog="zrakhr",
        description="Prikupljanje podataka o vremenu i kvaliteti zraka za hrvatske gradove.",
        epilog="Izlazni kodovi: 0 ako je sve uspjelo, 1 ako izvor nije uspio, 2 za pogrešnu upotrebu.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    fetch = commands.add_parser("fetch", parents=[common], help="dohvati Open-Meteo prognozu za jedan grad")
    fetch.add_argument("--city", required=True, choices=CITIES, help="naziv grada")
    fetch.add_argument("--raw-dir", type=Path, default=Path("data/raw"),
                       help="mapa za sirove JSON odgovore (zadano: data/raw)")
    fetch.set_defaults(func=cmd_fetch)

    collect = commands.add_parser("collect", parents=[common], help="spremi mjerenja s izvora")
    collect.add_argument("--source", required=True, choices=("dhmz", "azo"),
                         help="izvor mjerenja: dhmz (tekući sat) ili azo (od --since do danas)")
    collect.add_argument("--since", type=date.fromisoformat,
                         help="samo za azo: prvi dan dohvata, npr. 2026-10-01 (zadano: jučer)")
    collect.add_argument("--raw-dir", type=Path, default=Path("data/raw"),
                         help="mapa za sirove odgovore (zadano: data/raw)")
    collect.set_defaults(func=cmd_collect)

    load = commands.add_parser("import", parents=[common], help="učitaj arhivu sirovih odgovora u bazu")
    load.add_argument("--raw-dir", type=Path, default=Path("data/raw"),
                      help="mapa sa sirovim odgovorima, pretražuje se i u podmapama (zadano: data/raw)")
    load.set_defaults(func=cmd_import)

    check = commands.add_parser("check", parents=[common],
                                help="provjeri je li za dan u bazi svaki sat mjerenja i svaka prognoza")
    check.add_argument("--date", type=date.fromisoformat,
                       help="dan u UTC-u, npr. 2026-11-20 (zadano: jučer)")
    check.set_defaults(func=cmd_check)

    stations = commands.add_parser("stations", parents=[common], help="ispiši postaje poznate bazi")
    stations.add_argument("--source", choices=db.SOURCES, help="samo postaje ovog izvora")
    stations.set_defaults(func=cmd_stations)

    database = commands.add_parser("db", help="upravljanje bazom")
    database_commands = database.add_subparsers(dest="db_command", required=True)
    init = database_commands.add_parser("init", parents=[common], help="stvori bazu i tablice")
    init.set_defaults(func=cmd_db_init)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ulazna točka CLI-ja."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
