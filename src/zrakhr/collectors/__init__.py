"""Kolektori podataka iz vanjskih izvora."""

from zrakhr.collectors.base import BaseCollector, HttpSource, Record
from zrakhr.collectors.dhmz import DhmzCollector, DhmzSnapshot, RejectedValue
from zrakhr.collectors.open_meteo import OpenMeteoAirQualityCollector, OpenMeteoWeatherCollector

__all__ = [
    "BaseCollector",
    "DhmzCollector",
    "DhmzSnapshot",
    "HttpSource",
    "OpenMeteoAirQualityCollector",
    "OpenMeteoWeatherCollector",
    "Record",
    "RejectedValue",
]
