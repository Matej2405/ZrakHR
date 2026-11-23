/**
 * Snimka zadnjih mjerenja (live/latest.json u grani data), koju nakon svakog prikupljanja zapisuje
 * naredba `zrakhr live`. Dok REST API (#13) ne postoji, dashboard je čita izravno s GitHuba, pa se
 * osvježava bez poslužitelja i bez novog deploya.
 */

import type { StationSource } from './stations'
import { finiteNumber, invalid, isObject, text } from './validate'

export interface LiveValue {
  value: number
  unit: string
  /** Vrijeme mjerenja u UTC-u; kod AZO-a je to kraj satnog intervala */
  observed_at: string
}

export interface LiveStation {
  source: StationSource
  external_id: string
  /** Zadnja vrijednost po metrici, npr. pm10 ili temperature_2m */
  values: Record<string, LiveValue>
  /** Parovi [vrijeme, vrijednost] metrike trenda (PM10) za zadnjih 48 sati */
  trend: [string, number][]
}

export interface LiveSnapshot {
  generated_at: string
  trend_metric: string
  stations: LiveStation[]
}

export const LIVE_URL =
  import.meta.env.VITE_LIVE_URL ??
  'https://raw.githubusercontent.com/Matej2405/ZrakHR/data/live/latest.json'

export async function fetchLive(signal?: AbortSignal): Promise<LiveSnapshot> {
  const response = await fetch(LIVE_URL, { signal })
  if (!response.ok) {
    throw new Error(`Snimka mjerenja nije dohvaćena (HTTP ${String(response.status)}).`)
  }
  return parseLiveSnapshot(await response.json())
}

/** Ključ postaje, isti za izvoz postaja i snimku mjerenja */
export function liveKey(source: StationSource, externalId: string): string {
  return `${source}:${externalId}`
}

export function liveIndex(snapshot: LiveSnapshot): Map<string, LiveStation> {
  return new Map(
    snapshot.stations.map((station) => [liveKey(station.source, station.external_id), station]),
  )
}

const SUBJECT = 'Neispravna snimka mjerenja'

function parseValue(value: unknown, path: string): LiveValue {
  if (!isObject(value)) invalid(SUBJECT, path, 'objekt')
  return {
    value: finiteNumber(SUBJECT, value, 'value', path),
    unit: text(SUBJECT, value, 'unit', path),
    observed_at: text(SUBJECT, value, 'observed_at', path),
  }
}

function parseTrendPoint(point: unknown, path: string): [string, number] {
  if (!Array.isArray(point) || point.length !== 2)
    invalid(SUBJECT, path, 'par [vrijeme, vrijednost]')
  const time: unknown = point[0]
  const value: unknown = point[1]
  if (typeof time !== 'string' || typeof value !== 'number' || !Number.isFinite(value)) {
    invalid(SUBJECT, path, 'par [vrijeme, vrijednost]')
  }
  return [time, value]
}

function parseStation(value: unknown, path: string): LiveStation {
  if (!isObject(value)) invalid(SUBJECT, path, 'objekt')
  const { source, values, trend } = value
  if (source !== 'dhmz' && source !== 'azo') invalid(SUBJECT, `${path}.source`, '"dhmz" ili "azo"')
  if (!isObject(values)) invalid(SUBJECT, `${path}.values`, 'objekt')
  if (!Array.isArray(trend)) invalid(SUBJECT, `${path}.trend`, 'popis')
  return {
    source,
    external_id: text(SUBJECT, value, 'external_id', path),
    values: Object.fromEntries(
      Object.entries(values).map(([metric, item]) => [
        metric,
        parseValue(item, `${path}.values.${metric}`),
      ]),
    ),
    trend: trend.map((point: unknown, index) =>
      parseTrendPoint(point, `${path}.trend[${String(index)}]`),
    ),
  }
}

/** Provjerava oblik snimke, jer dolazi izvan aplikacije; greška navodi točno polje. */
export function parseLiveSnapshot(data: unknown): LiveSnapshot {
  if (!isObject(data)) invalid(SUBJECT, 'snimka', 'objekt')
  const { stations } = data
  if (!Array.isArray(stations)) invalid(SUBJECT, 'stations', 'popis')
  return {
    generated_at: text(SUBJECT, data, 'generated_at', 'snimka'),
    trend_metric: text(SUBJECT, data, 'trend_metric', 'snimka'),
    stations: stations.map((station: unknown, index) =>
      parseStation(station, `stations[${String(index)}]`),
    ),
  }
}
