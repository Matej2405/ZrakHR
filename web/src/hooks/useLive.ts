import { useEffect, useState } from 'react'

import { fetchLive, type LiveSnapshot } from '../api/live'

/** Snimka se objavljuje svaki sat; provjera svakih 10 minuta donosi je ubrzo nakon objave */
export const LIVE_REFRESH_MS = 10 * 60 * 1000

export type LiveState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: LiveSnapshot }

/** Učitava snimku mjerenja i osvježava je; ako osvježavanje ne uspije, ostaje zadnja dobra snimka. */
export function useLive(): LiveState {
  const [state, setState] = useState<LiveState>({ status: 'loading' })

  useEffect(() => {
    let controller = new AbortController()

    function load() {
      controller.abort()
      controller = new AbortController()
      const { signal } = controller
      fetchLive(signal).then(
        (data) => {
          setState({ status: 'ready', data })
        },
        (error: unknown) => {
          if (signal.aborted) return
          const message = error instanceof Error ? error.message : 'Nepoznata greška'
          setState((current) =>
            current.status === 'ready' ? current : { status: 'error', message },
          )
        },
      )
    }

    load()
    const timer = window.setInterval(load, LIVE_REFRESH_MS)
    return () => {
      window.clearInterval(timer)
      controller.abort()
    }
  }, [])

  return state
}
