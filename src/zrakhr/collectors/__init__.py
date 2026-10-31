"""Kolektori podataka iz vanjskih izvora."""

from zrakhr.collectors.base import BaseCollector, Record
from zrakhr.collectors.open_meteo import OpenMeteoAirQualityCollector, OpenMeteoWeatherCollector

__all__ = [
    "BaseCollector",
    "OpenMeteoAirQualityCollector",
    "OpenMeteoWeatherCollector",
    "Record",
]
