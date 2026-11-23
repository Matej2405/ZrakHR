"""Snimka zadnjih mjerenja za dashboard (live/latest.json).

Dok REST API (#13) ne postoji, workflow Collect nakon svakog prikupljanja zapisuje ovu snimku u
granu data, a dashboard je čita izravno s raw.githubusercontent.com, bez ikakvog poslužitelja.
Postaje se prepoznaju po izvoru i vanjskoj oznaci, kao u izvozu postaja za kartu i tablici stations.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Any

from zrakhr.db import utc

# Vrijednost starija od ovoga nije trenutna, pa se ne prikazuje
MAX_AGE = timedelta(hours=24)

# Trend u oblačiću postaje: PM10 za zadnjih 48 sati
TREND_METRIC = "pm10"
TREND_AGE = timedelta(hours=48)


def build_snapshot(conn: sqlite3.Connection, now: datetime) -> dict[str, Any]:
    """Zadnja vrijednost po postaji i metrici (ne starija od MAX_AGE) i trend PM10 po postaji."""
    rows = conn.execute(
        """
        SELECT s.source, s.external_id, m.metric, m.observed_at, m.value, m.unit
        FROM measurements AS m
        JOIN stations AS s ON s.id = m.station_id
        JOIN (
            SELECT station_id, metric, MAX(observed_at) AS latest
            FROM measurements
            WHERE observed_at >= ?
            GROUP BY station_id, metric
        ) AS last
          ON last.station_id = m.station_id AND last.metric = m.metric
         AND last.latest = m.observed_at
        ORDER BY s.source, s.external_id, m.metric
        """,
        (utc(now - MAX_AGE),),
    ).fetchall()

    stations: dict[tuple[str, str], dict[str, Any]] = {}
    for source, external_id, metric, observed_at, value, unit in rows:
        station = stations.setdefault((source, external_id), {
            "source": source, "external_id": external_id, "values": {}, "trend": [],
        })
        station["values"][metric] = {"value": value, "unit": unit, "observed_at": observed_at}

    trend = conn.execute(
        """
        SELECT s.source, s.external_id, m.observed_at, m.value
        FROM measurements AS m
        JOIN stations AS s ON s.id = m.station_id
        WHERE m.metric = ? AND m.observed_at >= ?
        ORDER BY m.observed_at
        """,
        (TREND_METRIC, utc(now - TREND_AGE)),
    )
    for source, external_id, observed_at, value in trend:
        if (source, external_id) in stations:
            stations[(source, external_id)]["trend"].append([observed_at, value])

    return {"generated_at": utc(now), "trend_metric": TREND_METRIC, "stations": list(stations.values())}
