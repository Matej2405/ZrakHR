"""Kolektor AZO-ovih mjerenja kvalitete zraka (https://iszz.azo.hr/iskzl/).

Portal izvozi satne izvorne (nevalidirane) podatke jedne postaje i jedne tvari za raspon datuma
(rs/podatak/export/json, tipPodatka=0). Validirani satni podaci za zadnje tjedne još ne postoje,
pa se koriste izvorni, uz provjeru raspona kao kod DHMZ-a. Portal čuva povijest, pa se isti
dohvat koristi i za satno prikupljanje (zadnja dva dana) i za dohvat unatrag.

Ograničenja portala, utvrđena isprobavanjem 18.11.2026.:
- jedan odgovor ima najviše 1000 vrijednosti (oko 41 dan satnih podataka), pa se dulji raspon
  dohvaća u dijelovima;
- pri prečestim upitima portal vraća HTTP 200 s tekstom "Too many requests" umjesto JSON-a, pa se
  između upita čeka, a takav odgovor se ponavlja uz dulje čekanje;
- vrijeme vrijednosti (ms od 1970. u UTC-u) je kraj satnog intervala: vrijednost u 01:00 je
  prosjek od 00:00 do 01:00.
"""

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import requests

from zrakhr.collectors.base import HttpSource, Record
from zrakhr.collectors.dhmz import Metric, RejectedValue

TIMEZONE = ZoneInfo("Europe/Zagreb")

# Grčko μ kao kod Open-Meteo, da se mjerenja i prognoze uspoređuju bez pretvaranja jedinica
UNIT = "μg/m³"

# Šifre tvari na portalu i metrike u koje se pretvaraju (nazivi kao kod Open-Meteo)
POLLUTANTS = {
    5: Metric("pm10", UNIT, 0, 1000),
    28: Metric("pm2_5", UNIT, 0, 1000),
    1: Metric("nitrogen_dioxide", UNIT, 0, 1000),
    31: Metric("ozone", UNIT, 0, 1000),
}

# Najdulji raspon jednog upita; 40 dana satnih podataka je 960 vrijednosti, ispod granice od 1000
CHUNK_DAYS = 40


@dataclass(frozen=True)
class AzoStation:
    """Postaja državne mreže u gradu projekta i tvari koje mjeri satno."""

    id: int
    name: str
    city: str
    lat: float
    lon: float
    pollutants: tuple[int, ...]


# Postaje državne mreže u gradovima projekta koje satno mjere barem jednu od tvari iz POLLUTANTS;
# koordinate su iz rs/postaja/koordinate. Postaje "PPI PM2,5" i RIJEKA-1 nemaju satnih podataka
# tih tvari, pa nisu tu.
# shortcut: popis je utvrđen upitima 18.11.2026.; ako postaja počne mjeriti novu tvar, treba je dodati
ALL_POLLUTANTS = (5, 28, 1, 31)
STATIONS = (
    AzoStation(155, "ZAGREB-1", "Zagreb", 45.800492, 15.974278, (5, 28, 1)),
    AzoStation(156, "ZAGREB-2", "Zagreb", 45.823717, 16.035825, (5, 28, 1)),
    AzoStation(157, "ZAGREB-3", "Zagreb", 45.764947, 16.006469, ALL_POLLUTANTS),
    AzoStation(303, "ZAGREB-4", "Zagreb", 45.774444, 15.931111, ALL_POLLUTANTS),
    AzoStation(159, "RIJEKA-2", "Rijeka", 45.320794, 14.483511, ALL_POLLUTANTS),
    AzoStation(304, "SPLIT-2", "Split", 43.518333, 16.442222, ALL_POLLUTANTS),
    AzoStation(305, "SPLIT-3", "Split", 43.504167, 16.453333, ALL_POLLUTANTS),
    AzoStation(160, "OSIJEK-1", "Osijek", 45.558792, 18.698769, (5, 1, 31)),
    AzoStation(299, "OSIJEK-2", "Osijek", 45.557722, 18.730861, ALL_POLLUTANTS),
    AzoStation(165, "SLAVONSKI BROD-1", "Slavonski Brod", 45.159472, 17.9951, ALL_POLLUTANTS),
    AzoStation(275, "SLAVONSKI BROD-2", "Slavonski Brod", 45.149114, 18.02345, (5, 28)),
)


class TooManyRequests(requests.RequestException):
    """Portal je odbio upit zbog prečestih upita (vraća ga kao HTTP 200 s tekstom)."""


@dataclass
class AzoSnapshot:
    """Obrađeni nizovi: normalizirani zapisi i odbačene vrijednosti."""

    records: list[Record]
    rejected: list[RejectedValue]


def series_key(station: AzoStation, pollutant: int) -> str:
    """Oznaka niza u sirovom odgovoru, npr. '155/5' (postaja/tvar)."""
    return f"{station.id}/{pollutant}"


class AzoCollector(HttpSource):
    """Dohvaća satne nizove za postaje iz STATIONS i pretvara ih u zapise."""

    source = "azo"
    url = "https://iszz.azo.hr/iskzl/rs/podatak/export/json"

    def __init__(self, *, pause: float = 2.0, **settings: Any) -> None:
        """Uz postavke HttpSource-a (timeout, retries, backoff), pause je čekanje (s) između upita,
        zbog ograničenja portala."""
        super().__init__(**settings)
        self.pause = pause

    def fetch_series(self, station: AzoStation, pollutant: int, start: date, end: date) -> list[dict[str, Any]]:
        """Satne vrijednosti jedne postaje i tvari od start do end (oba dana uključena)."""
        values: list[dict[str, Any]] = []
        chunk_start = start
        while chunk_start <= end:
            chunk_end = min(chunk_start + timedelta(days=CHUNK_DAYS - 1), end)
            params = {
                "postaja": station.id,
                "polutant": pollutant,
                "tipPodatka": 0,
                "vrijemeOd": chunk_start.strftime("%d.%m.%Y"),
                "vrijemeDo": chunk_end.strftime("%d.%m.%Y"),
            }
            values.extend(self._get(self.url, params, _parse_json_list))
            time.sleep(self.pause)
            chunk_start = chunk_end + timedelta(days=1)
        return values

    def fetch(self, start: date, end: date) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
        """Sirovi nizovi svih postaja i tvari po oznaci niza te oznake nizova koji nisu dohvaćeni.

        Neuspjeh jednog niza ne prekida ostale, da se dohvati što više podataka.
        """
        series: dict[str, list[dict[str, Any]]] = {}
        failed: list[str] = []
        for station in STATIONS:
            for pollutant in station.pollutants:
                key = series_key(station, pollutant)
                try:
                    series[key] = self.fetch_series(station, pollutant, start, end)
                except requests.RequestException:
                    failed.append(key)  # greška je već zapisana u log
        return series, failed

    def parse(self, series: dict[str, list[dict[str, Any]]]) -> AzoSnapshot:
        """Pretvara sirove nizove u zapise; vrijednosti izvan raspona se odbacuju s razlogom."""
        stations = {str(s.id): s for s in STATIONS}
        records: list[Record] = []
        rejected: list[RejectedValue] = []
        for key, values in series.items():
            station_id, pollutant = key.split("/")
            metric = POLLUTANTS[int(pollutant)]
            name = stations[station_id].name
            for item in values:
                value = item.get("vrijednost")
                if value is None:
                    continue  # sat bez mjerenja
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    rejected.append(RejectedValue(location=name, metric=metric.name, raw=str(value),
                                                  reason="nije broj"))
                    continue
                if not metric.low <= value <= metric.high:
                    rejected.append(RejectedValue(
                        location=name, metric=metric.name, raw=str(value),
                        reason=f"izvan raspona od {metric.low:g} do {metric.high:g} {metric.unit}"))
                    continue
                moment = datetime.fromtimestamp(item["vrijeme"] / 1000, timezone.utc).astimezone(TIMEZONE)
                records.append(Record(source=self.source, location=station_id, metric=metric.name,
                                      timestamp=moment.isoformat(), value=float(value), unit=metric.unit))
        return AzoSnapshot(records=records, rejected=rejected)


def _parse_json_list(response: requests.Response) -> list[dict[str, Any]]:
    """JSON lista vrijednosti; tekst "Too many requests" podiže TooManyRequests, koji se ponavlja."""
    if response.text.lstrip().lower().startswith("too many requests"):
        raise TooManyRequests("portal je odbio upit: too many requests")
    data = response.json()
    if not isinstance(data, list):
        raise requests.RequestException(f"neočekivan odgovor: {response.text[:80]!r}")
    return data
