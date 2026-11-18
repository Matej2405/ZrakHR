"""Testovi naredbi stations, db init i zajedničkih opcija CLI-ja, bez mreže."""

from contextlib import closing
from pathlib import Path

import pytest

from zrakhr import db
from zrakhr.__main__ import build_parser, main


def test_stations_on_new_database_says_how_to_fill_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Na svježem klonu baza je prazna; naredba to kaže umjesto prazne tablice."""
    assert main(["stations", "--db", str(tmp_path / "zrakhr.db")]) == 0

    assert "nema postaja" in capsys.readouterr().out


def test_stations_lists_saved_stations_filtered_by_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Ispis ima postaje iz baze, a --source ostavlja samo postaje jednog izvora."""
    path = tmp_path / "zrakhr.db"
    with closing(db.connect(path)) as conn:
        db.save_station(conn, "azo", "157", "ZAGREB-3", 45.764947, 16.006469, "Zagreb")
        db.save_station(conn, "dhmz", "Zagreb-Maksimir", "Zagreb-Maksimir")
        conn.commit()  # save_station ne sprema sam; pri prikupljanju to radi upis mjerenja

    assert main(["stations", "--db", str(path)]) == 0
    everything = capsys.readouterr().out
    assert main(["stations", "--source", "azo", "--db", str(path)]) == 0
    azo = capsys.readouterr().out

    assert "ZAGREB-3" in everything and "Zagreb-Maksimir" in everything
    assert everything.rstrip().endswith("postaje: 2")
    assert "45.7649" in azo and "Zagreb-Maksimir" not in azo
    assert azo.rstrip().endswith("postaje: 1")


def test_db_init_creates_all_tables(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["db", "init", "--db", str(tmp_path / "nova" / "zrakhr.db")]) == 0

    out = capsys.readouterr().out
    for table in ("collection_runs", "forecasts", "measurements", "sources", "stations"):
        assert table in out


def test_verbose_works_after_any_command() -> None:
    """-v je opcija svake naredbe, pa radi na kraju naredbe kao i --db."""
    parser = build_parser()

    assert parser.parse_args(["collect", "--source", "dhmz", "-v"]).verbose
    assert parser.parse_args(["db", "init", "--verbose"]).verbose
    assert not parser.parse_args(["stations"]).verbose


def test_wrong_usage_exits_with_2() -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["stations", "--source", "nepostojeci"])

    assert exit_info.value.code == 2
