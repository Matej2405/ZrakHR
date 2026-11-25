"""Zajednička osnova kolektora: HTTP dohvat s ponavljanjem i sučelje kolektora po gradu."""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypedDict, TypeVar

import requests

from zrakhr.cities import City

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Record(TypedDict):
    """Normalizirani zapis jednog mjerenja."""

    source: str
    location: str
    metric: str
    timestamp: str  # ISO 8601 s pomakom od UTC-a
    value: float
    unit: str


class HttpSource:
    """Izvor podataka dostupan preko HTTP-a: naziv izvora i dohvat koji ponavlja privremene greške."""

    source: str  # naziv izvora, upisuje se u zapise i u imena datoteka

    def __init__(self, timeout: float = 30.0, retries: int = 4, backoff: float = 15.0) -> None:
        """Postavlja timeout (s), broj pokušaja i početno čekanje (s) koje se udvostručuje.

        Izvori znaju nekoliko minuta ne odgovarati (Open-Meteo je 24. i 25.11.2026. GitHubovu
        runneru zastajao i do 3 minute), pa zadani pokušaji čekaju 15, 30 i 60 s i ukupno traju do
        oko 4 minute. S kraćim razmacima svi pokušaji padnu u isti zastoj.
        """
        if retries < 1:
            raise ValueError("retries mora biti barem 1")
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

    def _get(self, url: str, params: dict[str, Any] | None,
             parse: Callable[[requests.Response], T]) -> T:
        """HTTP GET čiji odgovor pretvara funkcija parse; privremene greške ponavlja uz eksponencijalni backoff."""
        attempt = 1
        while True:
            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                result = parse(response)
            except requests.RequestException as exc:
                if attempt >= self.retries or not _is_retryable(exc):
                    logger.error("%s: dohvat nije uspio (pokušaj %d/%d): %s",
                                 self.source, attempt, self.retries, exc)
                    raise
                delay = self.backoff * 2 ** (attempt - 1)
                logger.warning("%s: pokušaj %d/%d nije uspio (%s), ponavljam za %.0f s",
                               self.source, attempt, self.retries, exc, delay)
                time.sleep(delay)
                attempt += 1
            else:
                logger.info("%s: dohvaćeno (HTTP %d, pokušaj %d/%d)",
                            self.source, response.status_code, attempt, self.retries)
                return result

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """HTTP GET koji vraća JSON, uz ponavljanje kao u _get."""
        return self._get(url, params, lambda response: response.json())


class BaseCollector(HttpSource, ABC):
    """Kolektor koji podatke dohvaća za pojedini grad (Open-Meteo) i normalizira ih."""

    @abstractmethod
    def fetch(self, city: City) -> dict[str, Any]:
        """Dohvaća sirovi odgovor izvora za zadani grad."""

    @abstractmethod
    def normalize(self, raw: dict[str, Any], city: City) -> list[Record]:
        """Pretvara sirovi odgovor u listu normaliziranih zapisa."""


def _is_retryable(exc: requests.RequestException) -> bool:
    """Ponavljaju se mrežne greške, istek vremena, HTTP 429 i 5xx; ostale 4xx ne."""
    if exc.response is None:
        return True
    return exc.response.status_code == 429 or exc.response.status_code >= 500
