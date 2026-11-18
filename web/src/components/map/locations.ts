import type { Station, StationSource } from '../../api/stations'

/**
 * Postaje istog izvora na istim koordinatama. Na karti su jedna oznaka, jer bi se zasebne
 * oznake potpuno preklopile (npr. OSIJEK-2 i OSIJEK-2 PPI PM2,5 dijele lokaciju).
 */
export interface StationLocation {
  key: string
  source: StationSource
  lat: number
  lon: number
  stations: Station[]
}

export function groupByLocation(stations: readonly Station[]): StationLocation[] {
  const locations = new Map<string, StationLocation>()
  for (const station of stations) {
    const key = `${station.source}:${String(station.lat)}:${String(station.lon)}`
    const location = locations.get(key)
    if (location) {
      location.stations.push(station)
    } else {
      locations.set(key, {
        key,
        source: station.source,
        lat: station.lat,
        lon: station.lon,
        stations: [station],
      })
    }
  }
  return [...locations.values()]
}
