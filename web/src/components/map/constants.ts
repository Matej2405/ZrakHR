import type { LatLngBoundsExpression } from 'leaflet'

import type { StationSource } from '../../api/stations'

/** Hrvatska s malom rezervom: početni prikaz karte i gumb „Cijela Hrvatska” */
export const CROATIA_BOUNDS: LatLngBoundsExpression = [
  [42.35, 13.45],
  [46.6, 19.45],
]

/** Polumjer kruga oko grada projekta, u metrima */
export const CITY_RADIUS_M = 10_000

/** Redoslijed izvora u legendi i nazivi koje vidi korisnik */
export const SOURCES: readonly StationSource[] = ['dhmz', 'azo']

export const SOURCE_LABELS: Record<StationSource, { name: string; measures: string }> = {
  dhmz: { name: 'DHMZ', measures: 'vrijeme' },
  azo: { name: 'AZO', measures: 'kvaliteta zraka' },
}
