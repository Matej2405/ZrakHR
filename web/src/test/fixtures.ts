import type { AzoStation, DhmzStation, StationsExport } from '../api/stations'

const STATE_NETWORK = 'Državna mreža za trajno praćenje kvalitete zraka'

export const OSIJEK_2: AzoStation = {
  source: 'azo',
  external_id: '157',
  name: 'OSIJEK-2',
  lat: 45.557722,
  lon: 18.730861,
  network: STATE_NETWORK,
}

/** Postaja na istim koordinatama kao OSIJEK-2, kao u stvarnom AZO-ovu popisu */
export const OSIJEK_2_PM25: AzoStation = {
  ...OSIJEK_2,
  external_id: '318',
  name: 'OSIJEK-2 PPI PM2,5',
}

export const ZAGREB_1: AzoStation = {
  source: 'azo',
  external_id: '160',
  name: 'ZAGREB-1',
  lat: 45.800556,
  lon: 15.977778,
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
