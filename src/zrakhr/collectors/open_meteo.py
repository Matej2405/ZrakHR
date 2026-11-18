"""Kolektori Open-Meteo prognoze vremena i CAMS prognoze kvalitete zraka.

Open-Meteo je model, a ne mjerenje, pa se njegovi zapisi spremaju isključivo kao prognoze
(tablica forecasts), uz vrijeme izdavanja, da se kasnije mogu usporediti s mjerenjima DHMZ-a i AZO-a.
Varijable i jedinice odabrane su tako da odgovaraju mjerenjima s kojima se uspoređuju.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from zrakhr.cities import City
from zrakhr.collectors.base import BaseCollector, Record

TIMEZONE = "Europe/Zagreb"


class _OpenMeteoCollector(BaseCollector):
    """Zajednička logika za Open-Meteo API-je, koji vraćaju isti oblik odgovora."""

    url: str
    hourly_variables: tuple[str, ...]
    extra_params: dict[str, str] = {}

    def fetch(self, city: City) -> dict[str, Any]:
        """Dohvaća satnu prognozu za koordinate grada."""
        params = {
            "latitude": city.latitude,
            "longitude": city.longitude,
            "hourly": ",".join(self.hourly_variables),
            "timezone": TIMEZONE,
            **self.extra_params,
        }
        return self._get_json(self.url, params)

    def normalize(self, raw: dict[str, Any], city: City) -> list[Record]:
        """Stvara po jedan zapis prognoze za svaku metriku i sat; vrijednosti koje nedostaju preskače.

        Open-Meteo vraća lokalno vrijeme bez zone i jedan pomak (utc_offset_seconds)
        za cijeli odgovor, pa se taj pomak dodaje svakoj vremenskoj oznaci.
        """
        tz = timezone(timedelta(seconds=raw["utc_offset_seconds"]))
        hourly = raw["hourly"]
        units = raw["hourly_units"]
        timestamps = [
            datetime.fromisoformat(t).replace(tzinfo=tz).isoformat() for t in hourly["time"]
        ]

        records: list[Record] = []
        for metric, values in hourly.items():
            if metric == "time":
                continue
            for timestamp, value in zip(timestamps, values, strict=True):
                if value is None:
                    continue
                records.append(Record(
                    source=self.source,
                    location=city.name,
                    metric=metric,
                    timestamp=timestamp,
                    value=float(value),
                    unit=units[metric],
                ))
        return records


class OpenMeteoWeatherCollector(_OpenMeteoCollector):
    """Satna prognoza vremena s istim veličinama koje mjeri DHMZ, uz oborine."""

    source = "open-meteo-weather"
    url = "https://api.open-meteo.com/v1/forecast"
    hourly_variables = (
        "temperature_2m",
        "relative_humidity_2m",
        "pressure_msl",
        "surface_pressure",
        "wind_speed_10m",
        "wind_direction_10m",
        "precipitation",
    )
    # Zadana jedinica brzine vjetra je km/h, a DHMZ mjeri u m/s
    extra_params = {"wind_speed_unit": "ms"}


class OpenMeteoAirQualityCollector(_OpenMeteoCollector):
    """Satna CAMS prognoza lebdećih čestica PM10 i PM2.5."""

    source = "open-meteo-air-quality"
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    hourly_variables = ("pm10", "pm2_5")
