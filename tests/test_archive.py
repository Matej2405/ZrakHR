"""Testovi učitavanja arhive sirovih odgovora (zrakhr import) i dnevne provjere (zrakhr check)."""

import json
import shutil
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest

from zrakhr import archive, db
from zrakhr.__main__ import main

FIXTURES = Path(__file__).parent / "fixtures"

# Najmanji Open-Meteo odgovor: sat prije izdavanja (22:00 UTC) se ne sprema, ostala dva da
FORECAST = {
    "utc_offset_seconds": 3600,
    "hourly": {"time": ["2026-11-17T22:00", "2026-11-17T23:00", "2026-11-18T00:00"],
               "pm10": [10.0, 11.0, None], "pm2_5": [5.0, 6.0, 7.0]},
    "hourly_units": {"pm10": "μg/m³", "pm2_5": "μg/m³"},
}


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    """Arhiva kao u grani data: po jedan odgovor svakog izvora i jedna pokvarena datoteka."""
    raw = tmp_path / "raw"
    for sub in ("dhmz/2026-11", "azo/2026-11", "open-meteo/2026-11"):
        (raw / sub).mkdir(parents=True)
    shutil.copy(FIXTURES / "hrvatska_n.xml", raw / "dhmz/2026-11/dhmz_20261117T220000Z.xml")
    (raw / "dhmz/2026-11/dhmz_20261117T230000Z.xml").write_text("<nije xml", encoding="utf-8")
    (raw / "dhmz/2026-11/dhmz_20261117T235900Z_neobradeno.xml").write_text("<nije xml", encoding="utf-8")
    shutil.copy(FIXTURES / "azo_series.json", raw / "azo/2026-11/azo_20261117T230000Z.json")
    (raw / "open-meteo/2026-11/open-meteo-air-quality_slavonski-brod_20261117T221512Z.json").write_text(
        json.dumps(FORECAST), encoding="utf-8")
    (raw.parent / "README.md").write_text("nije podatak", encoding="utf-8")
    return raw


def test_import_loads_every_source_once_and_counts_broken_files(
    raw_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Pokvarena datoteka se broji i ne prekida ostale; ponovno učitavanje ne dodaje ništa."""
    args = ["import", "--raw-dir", str(raw_dir), "--db", str(tmp_path / "zrakhr.db")]

    assert main(args) == 1
    first = capsys.readouterr().out
    assert main(args) == 1
    second = capsys.readouterr().out

    assert "dhmz: datoteke 2, novih u bazi 26, neučitane 1" in first
    assert "azo: datoteke 1, novih u bazi 7, neučitane 0" in first
    assert "open-meteo-air-quality: datoteke 1, novih u bazi 3, neučitane 0" in first
    assert "novih u bazi 0" in second and "novih u bazi 26" not in second


def test_imported_forecast_is_issued_at_the_full_hour_of_the_fetch(raw_dir: Path, tmp_path: Path) -> None:
    """Vrijeme izdavanja dolazi iz imena datoteke, kao pri dohvatu (zrakhr fetch)."""
    main(["import", "--raw-dir", str(raw_dir), "--db", str(tmp_path / "zrakhr.db")])

    with sqlite3.connect(tmp_path / "zrakhr.db") as conn:
        rows = conn.execute("SELECT DISTINCT issue_time, lead_hours FROM forecasts ORDER BY 2").fetchall()
        city = conn.execute("SELECT city FROM stations WHERE source = 'open-meteo-air-quality'").fetchone()

    assert rows == [("2026-11-17T22:00:00Z", 0), ("2026-11-17T22:00:00Z", 1)]
    assert city == ("Slavonski Brod",)


def test_check_lists_missing_hours_and_fails(
    raw_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """DHMZ ima samo 22 h, AZO 00-02 h, a prognoza je izdana jednom od četiri puta."""
    path = str(tmp_path / "zrakhr.db")
    main(["import", "--raw-dir", str(raw_dir), "--db", path])
    capsys.readouterr()

    assert main(["check", "--date", "2026-11-17", "--db", path]) == 1

    out = capsys.readouterr().out.splitlines()
    assert out[0] == "dhmz 2026-11-17: sati 1/24, zapisi 26, nedostaju sati (UTC) 00-21, 23"
    assert out[1] == "azo 2026-11-17: sati 3/24, zapisi 7, nedostaju sati (UTC) 03-23"
    assert out[3] == "open-meteo-air-quality 2026-11-17: pokretanja prognoze 1/4, zapisi 3"


def test_check_passes_source_with_every_hour(tmp_path: Path) -> None:
    with closing(db.connect(tmp_path / "zrakhr.db")) as conn:
        db.save_station(conn, "dhmz", "Zagreb-Maksimir")
        db.insert_measurements(conn, [
            {"source": "dhmz", "location": "Zagreb-Maksimir", "metric": "temperature_2m",
             "timestamp": f"2026-11-20T{hour:02d}:00:00+00:00", "value": 5.0, "unit": "°C"}
            for hour in range(24)
        ])
        lines = dict(archive.check_day(conn, date(2026, 11, 20)))

    assert lines["dhmz 2026-11-20: sati 24/24, zapisi 24"] is True
    assert lines["azo 2026-11-20: sati 0/24, zapisi 0, nedostaju sati (UTC) 00-23"] is False
