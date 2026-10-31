"""Testovi normalizacije Open-Meteo odgovora na ručno napisanim primjerima, bez mreže."""

from zrakhr.cities import CITIES
from zrakhr.collectors import OpenMeteoAirQualityCollector, OpenMeteoWeatherCollector

ZAGREB = CITIES["Zagreb"]

WEATHER_RESPONSE = {
    "latitude": 45.82,
    "longitude": 15.98,
    "utc_offset_seconds": 3600,
    "timezone": "Europe/Zagreb",
    "timezone_abbreviation": "GMT+1",
    "hourly_units": {
        "time": "iso8601",
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "surface_pressure": "hPa",
        "wind_speed_10m": "km/h",
        "precipitation": "mm",
    },
    "hourly": {
        "time": ["2026-10-31T00:00", "2026-10-31T01:00"],
        "temperature_2m": [8.4, 7.9],
        "relative_humidity_2m": [91, 93],
        "surface_pressure": [1002.3, 1002.1],
        "wind_speed_10m": [5.1, 4.3],
        "precipitation": [0.0, 0.2],
    },
}

AIR_QUALITY_RESPONSE = {
    "latitude": 45.8,
    "longitude": 16.0,
    "utc_offset_seconds": 7200,
    "timezone": "Europe/Zagreb",
    "timezone_abbreviation": "GMT+2",
    "hourly_units": {
        "time": "iso8601",
        "pm10": "μg/m³",
        "pm2_5": "μg/m³",
        "nitrogen_dioxide": "μg/m³",
        "ozone": "μg/m³",
    },
    "hourly": {
        "time": ["2026-07-15T13:00", "2026-07-15T14:00"],
        "pm10": [16.2, None],
        "pm2_5": [13.3, 13.0],
        "nitrogen_dioxide": [5.7, 4.4],
        "ozone": [51.0, None],
    },
}


def test_weather_creates_one_record_per_metric_and_hour() -> None:
    """Pet metrika × dva sata daje deset zapisa u jedinstvenom obliku."""
    records = OpenMeteoWeatherCollector().normalize(WEATHER_RESPONSE, ZAGREB)

    assert len(records) == 10
    assert records[0] == {
        "source": "open-meteo-weather",
        "location": "Zagreb",
        "metric": "temperature_2m",
        "timestamp": "2026-10-31T00:00:00+01:00",
        "value": 8.4,
        "unit": "°C",
    }


def test_weather_integer_values_become_float() -> None:
    """Cjelobrojne vrijednosti iz JSON-a (npr. vlažnost) spremaju se kao float."""
    records = OpenMeteoWeatherCollector().normalize(WEATHER_RESPONSE, ZAGREB)
    humidity = [r for r in records if r["metric"] == "relative_humidity_2m"]

    assert [r["value"] for r in humidity] == [91.0, 93.0]
    assert all(isinstance(r["value"], float) for r in humidity)


def test_air_quality_skips_missing_values() -> None:
    """Vrijednosti null se preskaču, ostale ostaju."""
    records = OpenMeteoAirQualityCollector().normalize(AIR_QUALITY_RESPONSE, ZAGREB)
    present = {(r["metric"], r["timestamp"]) for r in records}

    assert len(records) == 6
    assert ("pm10", "2026-07-15T14:00:00+02:00") not in present
    assert ("ozone", "2026-07-15T14:00:00+02:00") not in present
    assert ("pm2_5", "2026-07-15T14:00:00+02:00") in present


def test_air_quality_uses_offset_and_units_from_response() -> None:
    """Pomak od UTC-a i jedinice preuzimaju se iz samog odgovora."""
    records = OpenMeteoAirQualityCollector().normalize(AIR_QUALITY_RESPONSE, ZAGREB)

    assert records[0]["source"] == "open-meteo-air-quality"
    assert records[0]["timestamp"] == "2026-07-15T13:00:00+02:00"
    assert {r["unit"] for r in records} == {"μg/m³"}
