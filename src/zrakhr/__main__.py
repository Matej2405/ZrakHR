"""Naredbeni redak, npr. ``python -m zrakhr fetch --city Zagreb``."""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from zrakhr.cities import CITIES, City
from zrakhr.collectors import (
    BaseCollector,
    OpenMeteoAirQualityCollector,
    OpenMeteoWeatherCollector,
    Record,
)

PREVIEW_ROWS = 5


def save_raw(raw: dict[str, Any], source: str, city: City, stamp: str, raw_dir: Path) -> Path:
    """Sprema sirovi odgovor u <raw_dir>/<izvor>_<grad>_<timestamp>.json."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{source}_{city.slug}_{stamp}.json"
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def print_preview(records: list[Record]) -> None:
    """Ispisuje prvih nekoliko zapisa kao tablicu."""
    print(f"  {'timestamp':<25}  {'metric':<20}  {'value':>8}  unit")
    for record in records[:PREVIEW_ROWS]:
        print(f"  {record['timestamp']:<25}  {record['metric']:<20}  "
              f"{record['value']:>8}  {record['unit']}")


def cmd_fetch(args: argparse.Namespace) -> int:
    """Pokreće sve kolektore za zadani grad; vraća 1 ako barem jedan nije uspio."""
    city = CITIES[args.city]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ulazna točka CLI-ja."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
