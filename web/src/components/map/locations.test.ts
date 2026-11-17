import { describe, expect, it } from 'vitest'

import type { AzoStation, DhmzStation } from '../../api/stations'
import { groupByLocation } from './locations'

const OSIJEK_2: AzoStation = {
  source: 'azo',
  external_id: '160',
  name: 'OSIJEK-2',
  lat: 45.557722,
  lon: 18.730861,
  network: 'Državna mreža za trajno praćenje kvalitete zraka',
}
const OSIJEK_2_PM25: AzoStation = { ...OSIJEK_2, external_id: '318', name: 'OSIJEK-2 PPI PM2,5' }
const OSIJEK_DHMZ: DhmzStation = {
  source: 'dhmz',
  external_id: 'Osijek',
  name: 'Osijek',
  lat: 45.557722,
  lon: 18.730861,
  automatic: false,
}

describe('groupByLocation', () => {
  it('postaje istog izvora na istim koordinatama spaja u jednu lokaciju', () => {
    const [location, ...rest] = groupByLocation([OSIJEK_2, OSIJEK_2_PM25])

    expect(rest).toEqual([])
    expect(location?.stations.map((station) => station.name)).toEqual([
      'OSIJEK-2',
      'OSIJEK-2 PPI PM2,5',
    ])
  })

  it('postaje različitih izvora ostaju odvojene i na istim koordinatama', () => {
    const locations = groupByLocation([OSIJEK_2, OSIJEK_DHMZ])

    expect(locations.map((location) => location.source)).toEqual(['azo', 'dhmz'])
  })
})
