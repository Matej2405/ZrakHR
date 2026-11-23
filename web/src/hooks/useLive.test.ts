import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { LIVE_SNAPSHOT } from '../test/fixtures'
import { LIVE_REFRESH_MS, useLive } from './useLive'

const NEWER = { ...LIVE_SNAPSHOT, generated_at: '2026-11-24T09:05:00Z' }

const json = (data: unknown) => () => new Response(JSON.stringify(data))
const missing = () => new Response('', { status: 404 })

/** Svaki sljedeći dohvat dobiva sljedeći odgovor */
function serve(...responses: (() => Response)[]) {
  const fetch = vi.fn<typeof globalThis.fetch>()
  for (const response of responses) {
    fetch.mockImplementationOnce(() => Promise.resolve(response()))
  }
  vi.stubGlobal('fetch', fetch)
  return fetch
}

/** Pomiče lažni sat; usput se obrade i odgovori na dohvate koji čekaju */
async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms)
  })
}

describe('useLive', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('svakih 10 minuta zamjenjuje snimku novom', async () => {
    serve(json(LIVE_SNAPSHOT), json(NEWER))
    const { result } = renderHook(() => useLive())
    await advance(0)
    expect(result.current).toEqual({ status: 'ready', data: LIVE_SNAPSHOT })

    await advance(LIVE_REFRESH_MS)

    expect(result.current).toEqual({ status: 'ready', data: NEWER })
  })

  it('kad osvježavanje ne uspije, zadržava zadnju dobru snimku', async () => {
    const fetch = serve(json(LIVE_SNAPSHOT), missing)
    const { result } = renderHook(() => useLive())
    await advance(0)

    await advance(LIVE_REFRESH_MS)

    expect(fetch).toHaveBeenCalledTimes(2)
    expect(result.current).toEqual({ status: 'ready', data: LIVE_SNAPSHOT })
  })

  it('bez ijedne dobre snimke javlja grešku', async () => {
    serve(missing)
    const { result } = renderHook(() => useLive())

    await advance(0)

    expect(result.current).toEqual({
      status: 'error',
      message: 'Snimka mjerenja nije dohvaćena (HTTP 404).',
    })
  })

  it('nakon uklanjanja prekida dohvat i više ne osvježava', async () => {
    const fetch = serve(json(LIVE_SNAPSHOT))
    const { unmount } = renderHook(() => useLive())

    unmount()
    await advance(LIVE_REFRESH_MS)

    expect(fetch).toHaveBeenCalledOnce()
    expect(fetch.mock.calls[0]?.[1]?.signal?.aborted).toBe(true)
  })
})
