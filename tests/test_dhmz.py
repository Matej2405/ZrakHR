"""Testovi DHMZ kolektora na spremljenom isječku feeda (tests/fixtures/hrvatska_n.xml), bez mreže."""

from pathlib import Path

import pytest

from zrakhr.__main__ import main
from zrakhr.collectors import DhmzCollector, DhmzSnapshot

FIXTURE = Path(__file__).parent / "fixtures" / "hrvatska_n.xml"


@pytest.fixture(scope="module")
def snapshot() -> DhmzSnapshot:
    return DhmzCollector().parse(FIXTURE.read_bytes())


def values_at(snapshot: DhmzSnapshot, location: str) -> dict[str, float]:
    """Vrijednosti jedne postaje po metrici."""
    return {r["metric"]: r["value"] for r in snapshot.records if r["location"] == location}


def rejected_at(snapshot: DhmzSnapshot, location: str) -> dict[str, str]:
    """Razlozi odbacivanja za jednu postaju po metrici."""
    return {r["metric"]: r["reason"] for r in snapshot.rejected if r["location"] == location}


def test_observation_time_is_local_hour_with_utc_offset(snapshot: DhmzSnapshot) -> None:
    """Datum i termin iz feeda su lokalno vrijeme; zimi je pomak +01:00."""
    assert snapshot.observed_at.isoformat() == "2026-11-17T23:00:00+01:00"
    assert {r["timestamp"] for r in snapshot.records} == {"2026-11-17T23:00:00+01:00"}


def test_summer_observation_uses_summer_time_offset() -> None:
    """Ljeti vrijedi srednjoeuropsko ljetno vrijeme (+02:00)."""
    xml = b"<Hrvatska><DatumTermin><Datum>15.07.2026</Datum><Termin>14</Termin></DatumTermin></Hrvatska>"

    assert DhmzCollector().parse(xml).observed_at.isoformat() == "2026-07-15T14:00:00+02:00"


def test_complete_station_gives_every_metric_with_unit(snapshot: DhmzSnapshot) -> None:
    """Postaja sa svim podacima daje šest zapisa; smjer vjetra je u stupnjevima."""
    assert values_at(snapshot, "Rijeka") == {
        "temperature_2m": 14.5,
        "relative_humidity_2m": 96.0,
        "pressure_msl": 1000.6,
        "pressure_tendency": -0.5,
        "wind_speed_10m": 1.8,
        "wind_direction_10m": 135.0,
    }
    units = {r["metric"]: r["unit"] for r in snapshot.records if r["location"] == "Rijeka"}
    assert units["wind_speed_10m"] == "m/s"
    assert units["wind_direction_10m"] == "°"


def test_dash_means_no_measurement_and_is_not_rejected(snapshot: DhmzSnapshot) -> None:
    """Crtica znači da postaja to ne mjeri; takva vrijednost se preskače bez odbacivanja."""
    assert values_at(snapshot, "Otočac") == {"temperature_2m": 11.7, "relative_humidity_2m": 100.0}
    assert rejected_at(snapshot, "Otočac") == {}


def test_station_level_pressure_is_kept_apart_from_sea_level_pressure(snapshot: DhmzSnapshot) -> None:
    """Zvjezdica označava tlak na visini planinske postaje, koji nije sveden na razinu mora."""
    zavizan = values_at(snapshot, "Zavižan")

    assert zavizan["surface_pressure"] == 836.8
    assert "pressure_msl" not in zavizan


def test_calm_wind_has_no_direction(snapshot: DhmzSnapshot) -> None:
    """C (tišina) daje brzinu vjetra 0 i nema smjera, a nije greška."""
    maksimir = values_at(snapshot, "Zagreb-Maksimir")

    assert maksimir["wind_speed_10m"] == 0.0
    assert "wind_direction_10m" not in maksimir
    assert rejected_at(snapshot, "Zagreb-Maksimir") == {}


def test_impossible_values_are_rejected_with_reason(snapshot: DhmzSnapshot) -> None:
    """Vlažnost 0 % automatske postaje je kvar senzora: vrijednost se odbacuje, ostalo ostaje."""
    assert rejected_at(snapshot, "Bosiljevo") == {
        "relative_humidity_2m": "izvan raspona od 1 do 100 %",
    }
    assert values_at(snapshot, "Bosiljevo")["temperature_2m"] == 14.6


def test_dirty_values_are_cleaned_or_rejected(snapshot: DhmzSnapshot) -> None:
    """Decimalni zarez i predznak + se čiste; tekst, nepoznat smjer i nemoguća brzina se odbacuju."""
    assert values_at(snapshot, "Izmišljena postaja") == {
        "temperature_2m": 12.5,
        "pressure_msl": 1013.2,
        "pressure_tendency": 0.3,
    }
    assert rejected_at(snapshot, "Izmišljena postaja") == {
        "relative_humidity_2m": "nije broj",
        "wind_direction_10m": "nepoznat smjer",
        "wind_speed_10m": "izvan raspona od 0 do 75 m/s",
    }


def test_snapshot_counts_stations_records_and_rejections(snapshot: DhmzSnapshot) -> None:
    """Šest postaja daje 26 zapisa i 4 odbačene vrijednosti."""
    assert snapshot.stations == 6
    assert len(snapshot.records) == 26
    assert len(snapshot.rejected) == 4


def test_feed_without_observation_time_is_an_error() -> None:
    """Feed bez datuma i termina znači da se format promijenio, pa obrada mora pasti."""
    with pytest.raises(ValueError, match="DatumTermin"):
        DhmzCollector().parse(b"<Hrvatska></Hrvatska>")


def test_collect_saves_raw_xml_named_by_observation_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Datoteka nosi vrijeme opažanja u UTC-u, pa ponovljeno prikupljanje istog sata ne stvara duplikat."""
    monkeypatch.setattr(DhmzCollector, "fetch", lambda self: FIXTURE.read_bytes())

    assert main(["collect", "--source", "dhmz", "--raw-dir", str(tmp_path)]) == 0
    assert main(["collect", "--source", "dhmz", "--raw-dir", str(tmp_path)]) == 0

    assert [p.name for p in tmp_path.iterdir()] == ["dhmz_20261117T220000Z.xml"]
    assert (tmp_path / "dhmz_20261117T220000Z.xml").read_bytes() == FIXTURE.read_bytes()
    summary = capsys.readouterr().out.splitlines()[0]
    assert summary == "dhmz 2026-11-17T23:00:00+01:00: postaje 6, zapisi 26, odbačene vrijednosti 4"


def test_collect_keeps_raw_xml_that_cannot_be_parsed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Neobradiv odgovor se ipak sprema, da podatak ne propadne, a naredba javlja grešku."""
    monkeypatch.setattr(DhmzCollector, "fetch", lambda self: b"<Hrvatska></Hrvatska>")

    assert main(["collect", "--source", "dhmz", "--raw-dir", str(tmp_path)]) == 1
    [saved] = tmp_path.iterdir()
    assert saved.name.startswith("dhmz_") and saved.name.endswith("_neobradeno.xml")
