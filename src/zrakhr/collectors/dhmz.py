"""Kolektor DHMZ-ovih mjerenja trenutnog vremena (https://vrijeme.hr/hrvatska_n.xml).

Feed sadrži samo tekući sat i samo postaje koje su u tom satu javile podatke (17.11.2026. u 21 h
73 postaje, a u 22 h 61), pa povijest nastaje isključivo redovitim prikupljanjem (scripts/collect.sh).
Vrijednosti se čiste: crtica i prazno znače da mjerenja nema, decimalni zarez postaje točka, a
fizikalno nemoguće vrijednosti (npr. vlažnost 0 %) se odbacuju i bilježe s razlogom.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict
from zoneinfo import ZoneInfo

from zrakhr.collectors.base import HttpSource, Record

TIMEZONE = ZoneInfo("Europe/Zagreb")


class RejectedValue(TypedDict):
    """Vrijednost koja nije prošla provjeru; čuva se za izvještaj o kvaliteti podataka."""

    location: str
    metric: str
    raw: str
    reason: str


@dataclass(frozen=True)
class Metric:
    """Mjerena veličina s nazivom kao kod Open-Meteo (radi usporedbe s prognozom) i rasponom mogućih vrijednosti."""

    name: str
    unit: str
    low: float
    high: float


# Elementi feeda i metrike u koje se pretvaraju
METRICS = {
    "Temp": Metric("temperature_2m", "°C", -40, 50),
    # 0 % u prirodi ne postoji; automatske postaje ga šalju kad senzor ne radi
    "Vlaga": Metric("relative_humidity_2m", "%", 1, 100),
    "Tlak": Metric("pressure_msl", "hPa", 900, 1080),
    # Sinoptička tendencija: promjena tlaka u posljednja 3 sata
    "TlakTend": Metric("pressure_tendency", "hPa", -20, 20),
    "VjetarBrzina": Metric("wind_speed_10m", "m/s", 0, 75),
}

# Planinske postaje (Zavižan, Puntijarka, Parg) zvjezdicom označavaju tlak na visini postaje,
# koji nije sveden na razinu mora, pa se čuva kao zasebna metrika
STATION_PRESSURE = Metric("surface_pressure", "hPa", 600, 1080)

# Smjer vjetra stiže kao jedna od 8 strana svijeta; C (tišina) nema smjer
WIND_DIRECTION = "wind_direction_10m"
WIND_DEGREES = {"N": 0, "NE": 45, "E": 90, "SE": 135, "S": 180, "SW": 225, "W": 270, "NW": 315}
CALM = "C"

MISSING = {"", "-"}


@dataclass
class DhmzSnapshot:
    """Jedan sat iz feeda: vrijeme opažanja, broj postaja, normalizirani zapisi i odbačene vrijednosti."""

    observed_at: datetime
    stations: int
    records: list[Record]
    rejected: list[RejectedValue]


class DhmzCollector(HttpSource):
    """Dohvaća feed i pretvara ga u zapise po postaji i metrici."""

    source = "dhmz"
    url = "https://vrijeme.hr/hrvatska_n.xml"

    def fetch(self) -> bytes:
        """Sirovi XML feeda, kakav se sprema u data/raw/."""
        return self._get(self.url, None, lambda response: response.content)

    def parse(self, xml: bytes) -> DhmzSnapshot:
        """Pretvara XML u zapise; feed bez datuma i termina opažanja podiže ValueError."""
        root = ET.fromstring(xml)
        observed_at = _observation_time(root)
        timestamp = observed_at.isoformat()
        stations = root.findall("Grad")
        records: list[Record] = []
        rejected: list[RejectedValue] = []

        def add(location: str, metric: Metric, text: str) -> None:
            checked = _check(metric, text)
            if isinstance(checked, str):
                rejected.append(RejectedValue(location=location, metric=metric.name, raw=text,
                                              reason=checked))
            else:
                records.append(Record(source=self.source, location=location, metric=metric.name,
                                      timestamp=timestamp, value=checked, unit=metric.unit))

        for station in stations:
            name = (station.findtext("GradIme") or "").strip()
            data = station.find("Podatci")
            if not name or data is None:
                continue
            for tag, metric in METRICS.items():
                text = (data.findtext(tag) or "").strip()
                if text in MISSING:
                    continue
                if tag == "Tlak" and text.endswith("*"):
                    add(name, STATION_PRESSURE, text[:-1])
                else:
                    add(name, metric, text)

            direction = (data.findtext("VjetarSmjer") or "").strip()
            if direction in WIND_DEGREES:
                records.append(Record(source=self.source, location=name, metric=WIND_DIRECTION,
                                      timestamp=timestamp, value=float(WIND_DEGREES[direction]),
                                      unit="°"))
            elif direction not in MISSING and direction != CALM:
                rejected.append(RejectedValue(location=name, metric=WIND_DIRECTION, raw=direction,
                                              reason="nepoznat smjer"))

        return DhmzSnapshot(observed_at=observed_at, stations=len(stations), records=records,
                            rejected=rejected)


def _observation_time(root: ET.Element) -> datetime:
    """Datum i termin opažanja su lokalno vrijeme u Hrvatskoj; vraća se vrijeme s pomakom od UTC-a."""
    date_text = root.findtext("DatumTermin/Datum")
    hour_text = root.findtext("DatumTermin/Termin")
    if not date_text or not hour_text:
        raise ValueError("feed nema datum i termin opažanja (DatumTermin)")
    day = datetime.strptime(date_text.strip(), "%d.%m.%Y")
    return day.replace(hour=int(hour_text), tzinfo=TIMEZONE)


def _check(metric: Metric, text: str) -> float | str:
    """Vrijednost kao broj ili, ako ne prođe provjeru, razlog odbacivanja."""
    try:
        value = float(text.replace(",", "."))
    except ValueError:
        return "nije broj"
    if not metric.low <= value <= metric.high:
        return f"izvan raspona od {metric.low:g} do {metric.high:g} {metric.unit}"
    return value
