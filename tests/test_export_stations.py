"""Testovi izvoza postaja za kartu (scripts/export_stations.py) na ručno napisanim primjerima, bez mreže."""

import logging
from datetime import datetime, timezone

import pytest

from export_stations import build_export, merge_previous, parse_azo, parse_dhmz, parse_number

# Isječak oblika https://vrijeme.hr/hrvatska_n.xml, s razmakom iza dužine kao u stvarnom feedu
DHMZ_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Hrvatska>
<DatumTermin><Datum>17.11.2026</Datum><Termin>21</Termin></DatumTermin>
<Grad autom="0">
<GradIme>Zagreb-Maksimir</GradIme>
<Lat>45.822</Lat>
<Lon>16.034 </Lon>
<Podatci><Temp> 12.6</Temp></Podatci>
</Grad>
<Grad autom="1">
<GradIme>Crni Lug - NP Risnjak</GradIme>
<Lat>45.421</Lat>
<Lon>14.692 </Lon>
<Podatci><Temp> 11.7</Temp></Podatci>
</Grad>
<Grad autom="0">
<GradIme>Bez koordinata</GradIme>
<Lat>-</Lat>
<Lon></Lon>
<Podatci><Temp>-</Temp></Podatci>
</Grad>
</Hrvatska>
""".encode()

# Oblik odgovora https://iszz.azo.hr/iskzl/rs/postaja/koordinate, sa stupcima u drugačijem
# redoslijedu nego u stvarnom odgovoru: parser ih mora tražiti po nazivu
AZO_RESPONSE = {
    "columnDesc": [
        {"name": "degreesYDecimal"},
        {"name": "postaja"},
        {"name": "mreza"},
        {"name": "degreesXDecimal"},
    ],
    "ids": ["160", "273", "999"],
    "data": [
        ["15,977778", "ZAGREB-1", "Državna mreža za trajno praćenje kvalitete zraka", "45,800556"],
        ["14,442222", " RIJEKA-2 ", "Državna mreža za trajno praćenje kvalitete zraka", "45,327778"],
        [None, "BEZ KOORDINATA", "Lokalna mreža", None],
    ],
}

GENERATED_AT = datetime(2026, 11, 17, 21, 30, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("17.200 ", 17.2),
        ("46,169056", 46.169056),
        ("-", None),
        ("", None),
        (None, None),
        ("n/a", None),
    ],
)
def test_parse_number_cleans_source_formats(text: str | None, expected: float | None) -> None:
    """Razmaci, decimalni zarez i oznake za vrijednost koja nedostaje, kako dolaze iz oba izvora."""
    assert parse_number(text) == expected


def test_dhmz_parses_stations_and_skips_missing_coordinates() -> None:
    """Postaja bez koordinata se preskače; naziv služi i kao vanjski identifikator."""
    assert parse_dhmz(DHMZ_XML) == [
        {
            "source": "dhmz",
            "external_id": "Zagreb-Maksimir",
            "name": "Zagreb-Maksimir",
            "lat": 45.822,
            "lon": 16.034,
            "automatic": False,
        },
        {
            "source": "dhmz",
            "external_id": "Crni Lug - NP Risnjak",
            "name": "Crni Lug - NP Risnjak",
            "lat": 45.421,
            "lon": 14.692,
            "automatic": True,
        },
    ]


def test_azo_reads_columns_by_name_and_skips_missing_coordinates() -> None:
    """Stupci se traže po nazivu iz columnDesc, decimalni zarez se pretvara u točku."""
    assert parse_azo(AZO_RESPONSE) == [
        {
            "source": "azo",
            "external_id": "160",
            "name": "ZAGREB-1",
            "lat": 45.800556,
            "lon": 15.977778,
            "network": "Državna mreža za trajno praćenje kvalitete zraka",
        },
        {
            "source": "azo",
            "external_id": "273",
            "name": "RIJEKA-2",
            "lat": 45.327778,
            "lon": 14.442222,
            "network": "Državna mreža za trajno praćenje kvalitete zraka",
        },
    ]


def test_merge_keeps_dhmz_stations_missing_from_current_hour() -> None:
    """DHMZ postaja koja ovaj sat nije javila podatke ostaje; AZO popis je uvijek potpun pa se ne nadopunjuje."""
    maksimir, risnjak = parse_dhmz(DHMZ_XML)
    zagreb, rijeka = parse_azo(AZO_RESPONSE)
    moved = maksimir | {"lat": 45.823}

    merged = merge_previous([moved, rijeka], previous=[maksimir, risnjak, zagreb])

    assert merged == [moved, rijeka, risnjak]


def test_export_sorts_stations_and_lists_project_cities() -> None:
    """Postaje su poredane po izvoru pa nazivu, a gradovi projekta dolaze iz zrakhr.cities."""
    export = build_export(parse_dhmz(DHMZ_XML) + parse_azo(AZO_RESPONSE), GENERATED_AT)

    assert export["generated_at"] == "2026-11-17T21:30:00+00:00"
    assert [(s["source"], s["name"]) for s in export["stations"]] == [
        ("azo", "RIJEKA-2"),
        ("azo", "ZAGREB-1"),
        ("dhmz", "Crni Lug - NP Risnjak"),
        ("dhmz", "Zagreb-Maksimir"),
    ]
    assert [c["name"] for c in export["cities"]] == [
        "Zagreb",
        "Rijeka",
        "Split",
        "Osijek",
        "Slavonski Brod",
    ]
    assert export["cities"][0] == {"name": "Zagreb", "lat": 45.815, "lon": 15.9819}


def test_export_drops_stations_outside_croatia(caplog: pytest.LogCaptureFixture) -> None:
    """Postaja izvan Hrvatske (npr. zamijenjena širina i dužina) izbacuje se uz upozorenje."""
    swapped = parse_azo(AZO_RESPONSE)[0] | {"lat": 15.977778, "lon": 45.800556}

    with caplog.at_level(logging.WARNING):
        export = build_export([swapped], GENERATED_AT)

    assert export["stations"] == []
    assert "ZAGREB-1" in caplog.text
