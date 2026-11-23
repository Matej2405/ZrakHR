import type { LiveSnapshot } from '../api/live'
import type { AzoStation, DhmzStation, StationsExport } from '../api/stations'

const STATE_NETWORK = 'Državna mreža za trajno praćenje kvalitete zraka'
const UG = 'μg/m³'

// Oznake postaja su stvarne AZO-ove oznake, iste kao u izvozu postaja i u bazi
export const OSIJEK_2: AzoStation = {
  source: 'azo',
  external_id: '299',
  name: 'OSIJEK-2',
  lat: 45.557722,
  lon: 18.730861,
  network: STATE_NETWORK,
}

/** Postaja na istim koordinatama kao OSIJEK-2, kao u stvarnom AZO-ovu popisu */
export const OSIJEK_2_PM25: AzoStation = {
  ...OSIJEK_2,
  external_id: '300',
  name: 'OSIJEK-2 PPI PM2,5',
}

export const ZAGREB_1: AzoStation = {
  source: 'azo',
  external_id: '155',
  name: 'ZAGREB-1',
  lat: 45.800492,
  lon: 15.974278,
  network: STATE_NETWORK,
}

export const MAKSIMIR: DhmzStation = {
  source: 'dhmz',
  external_id: 'Zagreb-Maksimir',
  name: 'Zagreb-Maksimir',
  lat: 45.822,
  lon: 16.034,
  automatic: false,
}

/** Mali izvoz: 3 postaje AZO-a na 2 lokacije i 1 postaja DHMZ-a */
export const STATIONS_EXPORT: StationsExport = {
  generated_at: '2026-11-17T21:57:50+00:00',
  sources: {
    dhmz: 'https://vrijeme.hr/hrvatska_n.xml',
    azo: 'https://iszz.azo.hr/iskzl/rs/postaja/koordinate',
  },
  cities: [
    { name: 'Zagreb', lat: 45.815, lon: 15.9819 },
    { name: 'Osijek', lat: 45.555, lon: 18.6955 },
  ],
  stations: [OSIJEK_2, OSIJEK_2_PM25, ZAGREB_1, MAKSIMIR],
}

/**
 * Snimka mjerenja: OSIJEK-2 iznad granice EU; Maksimir s vremenom, a promjenom tlaka iz ranijeg
 * sata, kao kod stvarnih postaja koje je ne mjere svaki sat; ZAGREB-1 bez svježeg mjerenja
 */
export const LIVE_SNAPSHOT: LiveSnapshot = {
  generated_at: '2026-11-24T08:05:00Z',
  trend_metric: 'pm10',
  stations: [
    {
      source: 'azo',
      external_id: '299',
      values: {
        pm10: { value: 62.4, unit: UG, observed_at: '2026-11-24T07:00:00Z' },
        pm2_5: { value: 41, unit: UG, observed_at: '2026-11-24T07:00:00Z' },
      },
      trend: [
        ['2026-11-24T05:00:00Z', 48.1],
        ['2026-11-24T06:00:00Z', 55],
        ['2026-11-24T07:00:00Z', 62.4],
      ],
    },
    {
      source: 'dhmz',
      external_id: 'Zagreb-Maksimir',
      values: {
        temperature_2m: { value: 4.2, unit: '°C', observed_at: '2026-11-24T08:00:00Z' },
        relative_humidity_2m: { value: 87, unit: '%', observed_at: '2026-11-24T08:00:00Z' },
        wind_speed_10m: { value: 2.1, unit: 'm/s', observed_at: '2026-11-24T08:00:00Z' },
        wind_direction_10m: { value: 225, unit: '°', observed_at: '2026-11-24T08:00:00Z' },
        pressure_tendency: { value: 0.8, unit: 'hPa', observed_at: '2026-11-24T06:00:00Z' },
      },
      trend: [],
    },
  ],
}
