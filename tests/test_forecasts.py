"""Testovi Open-Meteo prognoza: što se traži od API-ja i kako se pokretanja prognoze spremaju, bez mreže."""

import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import requests

from zrakhr import db
from zrakhr.__main__ import main
from zrakhr.cities import CITIES, City
from zrakhr.collectors import OpenMeteoAirQualityCollector, OpenMeteoWeatherCollector

ZAGREB = CITIES["Zagreb"]


def requested_params(monkeypatch: pytest.MonkeyPatch, collector: Any) -> dict[str, Any]:
    """Parametri koje kolektor šalje API-ju."""
    sent: dict[str, Any] = {}

    class Response:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            return {}

    def fake_get(url: str, params: dict[str, Any], **_: object) -> Response:
        sent.update(params)
        return Response()

    monkeypatch.setattr(requests, "get", fake_get)
    collector.fetch(ZAGREB)
    return sent


def test_air_quality_forecast_asks_only_for_particulate_matter(monkeypatch: pytest.MonkeyPatch) -> None:
    """CAMS se koristi samo kao prognoza PM10 i PM2.5."""
    params = requested_params(monkeypatch, OpenMeteoAirQualityCollector())

    assert params["hourly"] == "pm10,pm2_5"


def test_weather_forecast_matches_dhmz_metrics_and_units(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prognoza vremena traži veličine koje mjeri DHMZ, a vjetar u m/s kao DHMZ."""
    params = requested_params(monkeypatch, OpenMeteoWeatherCollector())

    assert {"temperature_2m", "relative_humidity_2m", "pressure_msl", "wind_speed_10m",
            "wind_direction_10m"} <= set(params["hourly"].split(","))
    assert params["wind_speed_unit"] == "ms"


def test_forecast_waits_out_a_stall_of_a_few_minutes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Open-Meteo zna nekoliko minuta ne odgovarati (24. i 25.11.2026. GitHubovu runneru do 3 minute),
    pa se pokušaji raspoređuju na minute: tri istekla pokušaja zaredom još ne znače neuspjeh."""
    waits: list[float] = []

    class Response:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            return {"hourly": {}}

    answers = iter([requests.ReadTimeout("Read timed out.")] * 3 + [Response()])

    def stalled_get(url: str, **_: object) -> Response:
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(requests, "get", stalled_get)
    monkeypatch.setattr(time, "sleep", waits.append)

    assert OpenMeteoWeatherCollector().fetch(ZAGREB) == {"hourly": {}}
    assert waits == [15, 30, 60]


def response(variables: dict[str, str], start: datetime, hours: int) -> dict[str, Any]:
    """Odgovor Open-Meteo oblika sa satima od start nadalje, u lokalnom vremenu (+01:00)."""
    local = start.astimezone(timezone(timedelta(hours=1)))
    return {
        "utc_offset_seconds": 3600,
        "hourly_units": {"time": "iso8601", **variables},
        "hourly": {
            "time": [(local + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(hours)],
            **{name: [float(h) for h in range(hours)] for name in variables},
        },
    }


@pytest.fixture
def fake_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """Oba API-ja vraćaju 24 sata: 6 prije trenutnog sata (prošlost) i 18 od njega nadalje."""
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=6)
    weather = response({"temperature_2m": "°C", "wind_speed_10m": "m/s"}, start, 24)
    air = response({"pm10": "μg/m³", "pm2_5": "μg/m³"}, start, 24)
    monkeypatch.setattr(OpenMeteoWeatherCollector, "fetch", lambda self, city: weather)
    monkeypatch.setattr(OpenMeteoAirQualityCollector, "fetch", lambda self, city: air)


@pytest.mark.usefixtures("fake_api")
def test_fetch_stores_forecast_snapshot_and_no_measurements(tmp_path: Path) -> None:
    """Dohvat sprema samo sate od izdavanja nadalje kao prognozu; ništa ne ide u mjerenja."""
    path = tmp_path / "zrakhr.db"

    assert main(["fetch", "--city", "Zagreb", "--raw-dir", str(tmp_path / "raw"), "--db", str(path)]) == 0
    # Isti sat: isto vrijeme izdavanja, pa nema duplikata
    assert main(["fetch", "--city", "Zagreb", "--raw-dir", str(tmp_path / "raw"), "--db", str(path)]) == 0

    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM measurements").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM forecasts").fetchone()[0] == 2 * 2 * 18
        leads = conn.execute("SELECT min(lead_hours), max(lead_hours), count(DISTINCT issue_time) "
                             "FROM forecasts").fetchone()
        assert leads == (0, 17, 1)
        stations = conn.execute("SELECT source, name, lat, lon, city FROM stations ORDER BY source").fetchall()
        assert stations == [
            ("open-meteo-air-quality", "Zagreb", ZAGREB.latitude, ZAGREB.longitude, "Zagreb"),
            ("open-meteo-weather", "Zagreb", ZAGREB.latitude, ZAGREB.longitude, "Zagreb"),
        ]
        runs = conn.execute("SELECT status, records FROM collection_runs ORDER BY id").fetchall()
        assert runs == [("ok", 36), ("ok", 36), ("ok", 0), ("ok", 0)]


def test_unparsable_forecast_is_recorded_as_failed_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Odgovor neočekivanog oblika ruši samo taj kolektor; sirovi odgovor ostaje spremljen."""
    def broken(self: object, city: City) -> dict[str, Any]:
        return {"error": True}

    monkeypatch.setattr(OpenMeteoWeatherCollector, "fetch", broken)
    monkeypatch.setattr(OpenMeteoAirQualityCollector, "fetch", broken)

    assert main(["fetch", "--city", "Zagreb", "--raw-dir", str(tmp_path / "raw"),
                 "--db", str(tmp_path / "zrakhr.db")]) == 1

    assert len(list((tmp_path / "raw").iterdir())) == 2
    with sqlite3.connect(tmp_path / "zrakhr.db") as conn:
        assert [r[0] for r in conn.execute("SELECT status FROM collection_runs")] == ["failed", "failed"]


def test_hours_before_issue_are_not_stored_as_forecast(tmp_path: Path) -> None:
    """Sat prije izdavanja nije prognoza, pa se ne sprema."""
    issued = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    records = [{"source": "open-meteo-air-quality", "location": "Zagreb", "metric": "pm10",
                "timestamp": (issued + timedelta(hours=h)).isoformat(), "value": 1.0, "unit": "μg/m³"}
               for h in (-1, 0, 1)]
    conn = db.connect(tmp_path / "zrakhr.db")

    assert db.insert_forecasts(conn, records, issued) == 2  # type: ignore[arg-type]
    conn.close()
