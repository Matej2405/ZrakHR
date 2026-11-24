/**
 * Mjerne postaje iz statičkog izvoza (scripts/export_stations.py), dok REST API (#13) ne bude
 * dostupan. Polja prate planiranu tablicu stations u backendu, zato su u snake_caseu.
 */

import { finiteNumber, invalid, isObject, text } from './validate'

export type StationSource = 'dhmz' | 'azo'

interface StationFields {
  external_id: string
  name: string
  lat: number
  lon: number
}

export interface DhmzStation extends StationFields {
  source: 'dhmz'
  /** Automatska postaja, bez motritelja */
  automatic: boolean
}

export interface AzoStation extends StationFields {
  source: 'azo'
  /** Mjerna mreža kojoj postaja pripada, npr. državna ili lokalna mreža grada */
  network: string
}

export type Station = DhmzStation | AzoStation

export interface City {
  name: string
  lat: number
  lon: number
}

export interface StationsExport {
  generated_at: string
  sources: Record<StationSource, string>
  cities: City[]
  stations: Station[]
}

export const STATIONS_URL = `${import.meta.env.BASE_URL}data/stations.json`

export async function fetchStations(signal?: AbortSignal): Promise<StationsExport> {
  const response = await fetch(STATIONS_URL, { signal })
  if (!response.ok) {
    throw new Error(`Popis postaja nije dohvaćen (HTTP ${String(response.status)}).`)
  }
  return parseStationsExport(await response.json())
}

const SUBJECT = 'Neispravan izvoz postaja'

function parseCity(value: unknown, path: string): City {
  if (!isObject(value)) invalid(SUBJECT, path, 'objekt')
  return {
    name: text(SUBJECT, value, 'name', path),
    lat: finiteNumber(SUBJECT, value, 'lat', path),
    lon: finiteNumber(SUBJECT, value, 'lon', path),
  }
}

function parseStation(value: unknown, path: string): Station {
  if (!isObject(value)) invalid(SUBJECT, path, 'objekt')
  const fields: StationFields = {
    external_id: text(SUBJECT, value, 'external_id', path),
    name: text(SUBJECT, value, 'name', path),
    lat: finiteNumber(SUBJECT, value, 'lat', path),
    lon: finiteNumber(SUBJECT, value, 'lon', path),
  }
  switch (value.source) {
    case 'dhmz': {
      const automatic = value.automatic
      if (typeof automatic !== 'boolean') invalid(SUBJECT, `${path}.automatic`, 'true ili false')
      return { source: 'dhmz', ...fields, automatic }
    }
    case 'azo':
      return { source: 'azo', ...fields, network: text(SUBJECT, value, 'network', path) }
    default:
      return invalid(SUBJECT, `${path}.source`, '"dhmz" ili "azo"')
  }
}

/** Provjerava oblik izvoza, jer datoteka dolazi izvan aplikacije; greška navodi točno polje. */
export function parseStationsExport(data: unknown): StationsExport {
  if (!isObject(data)) invalid(SUBJECT, 'izvoz', 'objekt')
  const { sources, cities, stations } = data
  if (!isObject(sources)) invalid(SUBJECT, 'sources', 'objekt')
  if (!Array.isArray(cities)) invalid(SUBJECT, 'cities', 'popis')
  if (!Array.isArray(stations)) invalid(SUBJECT, 'stations', 'popis')

  return {
    generated_at: text(SUBJECT, data, 'generated_at', 'izvoz'),
    sources: {
      dhmz: text(SUBJECT, sources, 'dhmz', 'sources'),
      azo: text(SUBJECT, sources, 'azo', 'sources'),
    },
    cities: cities.map((city: unknown, index) => parseCity(city, `cities[${String(index)}]`)),
    stations: stations.map((station: unknown, index) =>
      parseStation(station, `stations[${String(index)}]`),
    ),
  }
}
