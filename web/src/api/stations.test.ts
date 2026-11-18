import { afterEach, describe, expect, it, vi } from 'vitest'

import { fetchStations, parseStationsExport, STATIONS_URL } from './stations'

const AZO = {
  source: 'azo',
  external_id: '160',
  name: 'ZAGREB-1',
  lat: 45.800556,
  lon: 15.977778,
  network: 'Državna mreža za trajno praćenje kvalitete zraka',
}

const DHMZ = {
  source: 'dhmz',
  external_id: 'Zagreb-Maksimir',
  name: 'Zagreb-Maksimir',
  lat: 45.822,
  lon: 16.034,
  automatic: false,
}

const EXPORT = {
  generated_at: '2026-11-17T21:57:50+00:00',
  sources: {
    dhmz: 'https://vrijeme.hr/hrvatska_n.xml',
    azo: 'https://iszz.azo.hr/iskzl/rs/postaja/koordinate',
  },
  cities: [{ name: 'Zagreb', lat: 45.815, lon: 15.9819 }],
  stations: [AZO, DHMZ],
}

describe('parseStationsExport', () => {
  it('prihvaća ispravan izvoz', () => {
    expect(parseStationsExport(EXPORT)).toEqual(EXPORT)
  })

  it('odbija nepoznat izvor i navodi gdje je greška', () => {
    const data = { ...EXPORT, stations: [{ ...AZO, source: 'hnb' }] }

    expect(() => parseStationsExport(data)).toThrow('stations[0].source')
  })

  it('odbija postaju bez koordinata', () => {
    const data = { ...EXPORT, stations: [AZO, { ...DHMZ, lat: null }] }

    expect(() => parseStationsExport(data)).toThrow('stations[1].lat')
  })

  it('odbija izvoz bez popisa postaja', () => {
    expect(() => parseStationsExport({ ...EXPORT, stations: undefined })).toThrow('stations')
  })
})

describe('fetchStations', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('dohvaća izvoz s putanje aplikacije', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(EXPORT)))
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchStations()).resolves.toEqual(EXPORT)
    expect(STATIONS_URL).toBe('/data/stations.json')
    expect(fetchMock).toHaveBeenCalledWith(STATIONS_URL, expect.anything())
  })

  it('javlja HTTP status kad izvoz ne postoji', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 404 })))

    await expect(fetchStations()).rejects.toThrow('HTTP 404')
  })
})
