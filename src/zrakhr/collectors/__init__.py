"""Kolektori podataka iz vanjskih izvora."""

from zrakhr.collectors.azo import STATIONS, AzoCollector, AzoSnapshot, AzoStation
from zrakhr.collectors.base import BaseCollector, HttpSource, Record
from zrakhr.collectors.dhmz import DhmzCollector, DhmzSnapshot, RejectedValue
from zrakhr.collectors.open_meteo import OpenMeteoAirQualityCollector, OpenMeteoWeatherCollector

__all__ = [
    "STATIONS",
    "AzoCollector",
    "AzoSnapshot",
    "AzoStation",
    "BaseCollector",
    "DhmzCollector",
    "DhmzSnapshot",
    "HttpSource",
    "OpenMeteoAirQualityCollector",
    "OpenMeteoWeatherCollector",
    "Record",
    "RejectedValue",
]
