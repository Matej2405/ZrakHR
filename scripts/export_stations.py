"""Izvoz mjernih postaja DHMZ-a i AZO-a u statički JSON za kartu na dashboardu.

Privremeno rješenje dok backend ne nudi popis postaja (naredba ``zrakhr stations`` iz #6 i
REST API iz #13). Karta čita web/public/data/stations.json, a ova skripta ga ponovno generira
iz izvora. Polja postaje (source, external_id, name, lat, lon) prate planiranu tablicu stations.

DHMZ-ov feed sadrži samo postaje koje su javile podatke u tekućem satu, pa ih je u različitim
satima različit broj (17.11.2026. u 21 h 73, a u 22 h 61). Zato skripta zadržava DHMZ postaje
iz prethodnog izvoza koje u tekućem satu nedostaju.

Pokretanje iz korijena repozitorija, s aktiviranim venvom:
    python scripts/export_stations.py
"""

import argparse
import json
import logging
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

import requests

from zrakhr.cities import CITIES

DHMZ_URL = "https://vrijeme.hr/hrvatska_n.xml"
AZO_URL = "https://iszz.azo.hr/iskzl/rs/postaja/koordinate"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "web" / "public" / "data" / "stations.json"
TIMEOUT = 30  # sekundi

# Granice Hrvatske s malom rezervom; postaja izvan njih ima pogrešne koordinate
LAT_RANGE = (42.3, 46.6)
LON_RANGE = (13.4, 19.5)

logger = logging.getLogger(__name__)


class _StationFields(TypedDict):
    source: str
    external_id: str
    name: str
    lat: float
    lon: float


class Station(_StationFields, total=False):
    """Postaja u izvozu; automatic postoji samo za DHMZ, a network samo za AZO."""

    automatic: bool
    network: str


def parse_number(text: str | None) -> float | None:
    """Pretvara vrijednost iz izvora ('17.200 ', '46,169056') u broj; '-', prazno i ostalo daju None."""
    if text is None:
        return None
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return None


def parse_dhmz(xml: bytes) -> list[Station]:
    """Postaje iz DHMZ-ova XML-a trenutnog vremena; postaje bez naziva ili koordinata se preskaču.

    Feed nema šifru postaje, pa naziv služi kao vanjski identifikator.
    """
    stations: list[Station] = []
    for element in ET.fromstring(xml).iter("Grad"):
        name = (element.findtext("GradIme") or "").strip()
        lat = parse_number(element.findtext("Lat"))
        lon = parse_number(element.findtext("Lon"))
        if not name or lat is None or lon is None:
            continue
        stations.append(Station(
            source="dhmz",
            external_id=name,
            name=name,
            lat=lat,
            lon=lon,
            automatic=element.get("autom") == "1",
        ))
    return stations


def parse_azo(response: dict[str, Any]) -> list[Station]:
    """Postaje iz AZO-ova popisa koordinata; stupci se traže po nazivu iz columnDesc.

    Širina je u stupcu degreesXDecimal, a dužina u degreesYDecimal (oznake X i Y slijede
    Gauss-Krügerovu projekciju), s decimalnim zarezom. Redak bez koordinata se preskače.
    """
    column = {desc["name"]: index for index, desc in enumerate(response["columnDesc"])}
    stations: list[Station] = []
    for station_id, row in zip(response["ids"], response["data"], strict=True):
        name = (row[column["postaja"]] or "").strip()
        lat = parse_number(row[column["degreesXDecimal"]])
        lon = parse_number(row[column["degreesYDecimal"]])
        if not name or lat is None or lon is None:
            continue
        stations.append(Station(
            source="azo",
            external_id=str(station_id),
            name=name,
            lat=lat,
            lon=lon,
            network=(row[column["mreza"]] or "").strip(),
        ))
    return stations


def merge_previous(stations: list[Station], previous: list[Station]) -> list[Station]:
    """Dodaje DHMZ postaje iz prethodnog izvoza koje u tekućem satu nisu javile podatke.

    AZO-ov popis koordinata je uvijek potpun, pa se iz prethodnog izvoza ne preuzima.
    """
    current = {station["external_id"] for station in stations if station["source"] == "dhmz"}
    carried = [station for station in previous
               if station["source"] == "dhmz" and station["external_id"] not in current]
    return stations + carried


def build_export(stations: list[Station], generated_at: datetime) -> dict[str, Any]:
    """Sastavlja izvoz: postaje unutar Hrvatske, poredane po izvoru i nazivu, i gradove projekta."""
    kept: list[Station] = []
    for station in stations:
        if LAT_RANGE[0] <= station["lat"] <= LAT_RANGE[1] and LON_RANGE[0] <= station["lon"] <= LON_RANGE[1]:
            kept.append(station)
        else:
            logger.warning("%s postaja %r ima koordinate izvan Hrvatske (%s, %s), preskačem",
                           station["source"], station["name"], station["lat"], station["lon"])
    kept.sort(key=lambda station: (station["source"], station["name"]))
    return {
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "sources": {"dhmz": DHMZ_URL, "azo": AZO_URL},
        "cities": [{"name": city.name, "lat": city.latitude, "lon": city.longitude}
                   for city in CITIES.values()],
        "stations": kept,
    }


def fetch(url: str) -> requests.Response:
    """HTTP GET koji grešku poslužitelja (4xx, 5xx) pretvara u iznimku."""
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return response


def main(argv: list[str] | None = None) -> int:
    """Dohvaća oba izvora i zapisuje izvoz; vraća 1 ako dohvat nije uspio."""
    parser = argparse.ArgumentParser(description="Izvoz postaja DHMZ-a i AZO-a u JSON za kartu.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="izlazna datoteka (zadano: web/public/data/stations.json)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        stations = parse_dhmz(fetch(DHMZ_URL).content) + parse_azo(fetch(AZO_URL).json())
    except requests.RequestException as exc:
        logger.error("dohvat nije uspio: %s", exc)
        return 1

    if args.output.exists():
        previous = json.loads(args.output.read_text(encoding="utf-8"))["stations"]
        merged = merge_previous(stations, previous)
        logger.info("DHMZ postaje iz prethodnog izvoza koje ovaj sat nisu javile podatke: %d",
                    len(merged) - len(stations))
        stations = merged

    export = build_export(stations, generated_at=datetime.now(timezone.utc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = {source: sum(s["source"] == source for s in export["stations"]) for source in ("dhmz", "azo")}
    logger.info("zapisane postaje (DHMZ: %d, AZO: %d) u %s", counts["dhmz"], counts["azo"], args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
