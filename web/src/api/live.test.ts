import { afterEach, describe, expect, it, vi } from 'vitest'

import { LIVE_SNAPSHOT } from '../test/fixtures'
import { fetchLive, LIVE_URL, liveIndex, parseLiveSnapshot } from './live'

describe('parseLiveSnapshot', () => {
  it('prihvaća ispravnu snimku', () => {
    expect(parseLiveSnapshot(LIVE_SNAPSHOT)).toEqual(LIVE_SNAPSHOT)
  })

  it('odbija vrijednost koja nije broj i navodi gdje je greška', () => {
    const [first] = LIVE_SNAPSHOT.stations
    const data = {
      ...LIVE_SNAPSHOT,
      stations: [
        { ...first, values: { pm10: { value: 'puno', unit: 'μg/m³', observed_at: 'x' } } },
      ],
    }

    expect(() => parseLiveSnapshot(data)).toThrow('stations[0].values.pm10.value')
  })

  it('odbija točku trenda bez vremena i vrijednosti', () => {
    const [first] = LIVE_SNAPSHOT.stations
    const data = { ...LIVE_SNAPSHOT, stations: [{ ...first, trend: [['2026-11-24T07:00:00Z']] }] }

    expect(() => parseLiveSnapshot(data)).toThrow('stations[0].trend[0]')
  })
})

describe('liveIndex', () => {
  it('postaje traži po izvoru i oznaci, kao u izvozu postaja', () => {
    const index = liveIndex(LIVE_SNAPSHOT)

    expect(index.get('azo:299')?.values.pm10?.value).toBe(62.4)
    expect(index.get('dhmz:Zagreb-Maksimir')?.values.temperature_2m?.value).toBe(4.2)
    expect(index.get('azo:155')).toBeUndefined()
  })
})

describe('fetchLive', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('čita snimku iz grane data na GitHubu', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(LIVE_SNAPSHOT)))
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchLive()).resolves.toEqual(LIVE_SNAPSHOT)
    expect(LIVE_URL).toBe(
      'https://raw.githubusercontent.com/Matej2405/ZrakHR/data/live/latest.json',
    )
    expect(fetchMock).toHaveBeenCalledWith(LIVE_URL, expect.anything())
  })
})
