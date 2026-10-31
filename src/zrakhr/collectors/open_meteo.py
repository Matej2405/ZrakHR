"""Kolektori za Open-Meteo API-je vremenske prognoze i kvalitete zraka."""

from datetime import datetime, timedelta, timezone
from typing import Any

from zrakhr.cities import City
from zrakhr.collectors.base import BaseCollector, Record

TIMEZONE = "Europe/Zagreb"


class _OpenMeteoCollector(BaseCollector):
    """Zajednička logika za Open-Meteo API-je, koji vraćaju isti oblik odgovora."""

    url: str
    hourly_variables: tuple[str, ...]

    def fetch(self, city: City) -> dict[str, Any]:
        """Dohvaća satne vrijednosti za koordinate grada."""
        params = {
            "latitude": city.latitude,
            "longitude": city.longitude,
            "hourly": ",".join(self.hourly_variables),
            "timezone": TIMEZONE,
        }
        return self._get_json(self.url, params)

    def normalize(self, raw: dict[str, Any], city: City) -> list[Record]:
        """Stvara po jedan zapis za svaku metriku i sat; vrijednosti koje nedostaju preskače.

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
    """Satni vremenski podaci: temperatura, vlažnost, tlak, vjetar i oborine."""

    source = "open-meteo-weather"
    url = "https://api.open-meteo.com/v1/forecast"
    hourly_variables = (
        "temperature_2m",
        "relative_humidity_2m",
        "surface_pressure",
        "wind_speed_10m",
        "precipitation",
    )


class OpenMeteoAirQualityCollector(_OpenMeteoCollector):
    """Satni podaci o kvaliteti zraka: PM10, PM2.5, NO2 i O3."""

    source = "open-meteo-air-quality"
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    hourly_variables = ("pm10", "pm2_5", "nitrogen_dioxide", "ozone")
