"""Testovi AZO kolektora, bez mreže.

Fixture tests/fixtures/azo_series.json ima stvarne odgovore portala od 17.11.2026. za ZAGREB-3
(PM10 i ozon); niz 155/28 (ZAGREB-1, PM2.5) je izmijenjen da sadrži sat bez mjerenja i
negativnu vrijednost.
"""

import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import requests

from zrakhr.__main__ import main
from zrakhr.collectors import STATIONS, AzoCollector, AzoSnapshot

FIXTURE = Path(__file__).parent / "fixtures" / "azo_series.json"
SERIES: dict[str, list[dict[str, Any]]] = json.loads(FIXTURE.read_text(encoding="utf-8"))["series"]


@pytest.fixture(scope="module")
def snapshot() -> AzoSnapshot:
    return AzoCollector().parse(SERIES)


def test_values_become_records_at_local_end_of_hour(snapshot: AzoSnapshot) -> None:
    """Vrijeme je kraj satnog intervala u UTC-u; zapisuje se u lokalnom vremenu s pomakom."""
    pm10 = [r for r in snapshot.records if r["location"] == "157" and r["metric"] == "pm10"]

    assert [(r["timestamp"], r["value"]) for r in pm10] == [
        ("2026-11-17T01:00:00+01:00", 30.9),
        ("2026-11-17T02:00:00+01:00", 27.5),
        ("2026-11-17T03:00:00+01:00", 25.8),
    ]


def test_metric_names_and_unit_match_open_meteo(snapshot: AzoSnapshot) -> None:
    """Nazivi i jedinica su kao kod Open-Meteo prognoze, da se mogu izravno usporediti."""
    assert {r["metric"] for r in snapshot.records} == {"pm10", "ozone", "pm2_5"}
    assert {r["unit"] for r in snapshot.records} == {"μg/m³"}
    assert {r["source"] for r in snapshot.records} == {"azo"}


def test_missing_hour_is_skipped_and_negative_value_rejected(snapshot: AzoSnapshot) -> None:
    """null znači da mjerenja nema; negativna koncentracija se odbacuje s razlogom."""
    pm25 = [r for r in snapshot.records if r["location"] == "155"]

    assert [r["value"] for r in pm25] == [18.4]
    assert snapshot.rejected == [{"location": "ZAGREB-1", "metric": "pm2_5", "raw": "-3.1",
                                  "reason": "izvan raspona od 0 do 1000 μg/m³"}]


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text
        self.status_code = 200

    def raise_for_status(self) -> None:
        pass

    def json(self) -> Any:
        return json.loads(self.text)


def test_long_range_is_fetched_in_chunks_below_the_portal_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Portal vraća najviše 1000 vrijednosti, pa se 85 dana dohvaća u tri dijela bez preklapanja."""
    asked: list[tuple[str, str]] = []

    def fake_get(url: str, params: dict[str, Any], **_: object) -> FakeResponse:
        asked.append((params["vrijemeOd"], params["vrijemeDo"]))
        return FakeResponse("[]")

    monkeypatch.setattr(requests, "get", fake_get)

    AzoCollector(pause=0).fetch_series(STATIONS[0], 5, date(2026, 10, 1), date(2026, 12, 24))

    assert asked == [("01.10.2026", "09.11.2026"), ("10.11.2026", "19.12.2026"),
                     ("20.12.2026", "24.12.2026")]


def test_too_many_requests_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """Portal odbija prečeste upite tekstom uz HTTP 200; takav odgovor se ponavlja."""
    answers = iter(["Too many requests", json.dumps(SERIES["157/5"])])
    monkeypatch.setattr(requests, "get", lambda url, **_: FakeResponse(next(answers)))

    values = AzoCollector(pause=0, backoff=0).fetch_series(STATIONS[0], 5, date(2026, 11, 17),
                                                           date(2026, 11, 17))

    assert len(values) == 3


def test_failed_series_does_not_stop_the_others(monkeypatch: pytest.MonkeyPatch) -> None:
    """Niz koji ni nakon ponavljanja ne uspije bilježi se, a ostali se dohvaćaju."""
    def fake_get(url: str, params: dict[str, Any], **_: object) -> FakeResponse:
        if params["postaja"] == STATIONS[0].id:
            raise requests.ConnectionError("mreža nije dostupna")
        return FakeResponse("[]")

    monkeypatch.setattr(requests, "get", fake_get)

    series, failed = AzoCollector(pause=0, backoff=0, retries=1).fetch(date(2026, 11, 17),
                                                                      date(2026, 11, 17))

    assert failed == [f"{STATIONS[0].id}/{p}" for p in STATIONS[0].pollutants]
    assert len(series) == sum(len(s.pollutants) for s in STATIONS) - len(failed)


def collect_args(tmp_path: Path, *extra: str) -> list[str]:
    return ["collect", "--source", "azo", "--raw-dir", str(tmp_path / "raw"),
            "--db", str(tmp_path / "zrakhr.db"), *extra]


def test_collect_stores_measurements_and_stations_with_city(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Prikupljanje sprema zapise i postaje s gradom; ponovljeni dohvat istog razdoblja ne dodaje ništa."""
    monkeypatch.setattr(AzoCollector, "fetch", lambda self, start, end: (SERIES, []))

    assert main(collect_args(tmp_path, "--since", "2026-11-17")) == 0
    assert main(collect_args(tmp_path, "--since", "2026-11-17")) == 0

    summaries = [line for line in capsys.readouterr().out.splitlines() if line.startswith("azo ")]
    assert summaries[0].startswith("azo 2026-11-17 do ")
    assert summaries[0].endswith("nizovi 3, zapisi 7, odbačene vrijednosti 1, novih u bazi 7")
    assert summaries[1].endswith("novih u bazi 0")
    assert len(list((tmp_path / "raw").iterdir())) >= 1
    with sqlite3.connect(tmp_path / "zrakhr.db") as conn:
        assert conn.execute("SELECT count(*) FROM measurements").fetchone()[0] == 7
        assert conn.execute("SELECT name, city FROM stations WHERE source = 'azo' AND external_id = '157'"
                            ).fetchone() == ("ZAGREB-3", "Zagreb")
        assert conn.execute("SELECT count(DISTINCT city) FROM stations WHERE source = 'azo'"
                            ).fetchone()[0] == 5


def test_partial_failure_keeps_data_but_fails_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dohvaćeni nizovi se spremaju, a pokretanje se bilježi kao neuspjelo s popisom nizova."""
    monkeypatch.setattr(AzoCollector, "fetch", lambda self, start, end: (SERIES, ["156/5"]))

    assert main(collect_args(tmp_path)) == 1

    with sqlite3.connect(tmp_path / "zrakhr.db") as conn:
        assert conn.execute("SELECT count(*) FROM measurements").fetchone()[0] == 7
        assert conn.execute("SELECT status, message FROM collection_runs").fetchone() == (
            "failed", "nedohvaćeni nizovi: 156/5")


def test_since_is_only_for_azo(tmp_path: Path) -> None:
    """DHMZ objavljuje samo tekući sat, pa --since za njega nema smisla."""
    assert main(["collect", "--source", "dhmz", "--since", "2026-10-01",
                 "--db", str(tmp_path / "zrakhr.db")]) == 2
