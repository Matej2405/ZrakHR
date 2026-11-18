import { useEffect, useState } from 'react'

import { fetchStations, type StationsExport } from '../api/stations'

export type StationsState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: StationsExport }

/** Učitava popis postaja pri prvom prikazu; dohvat se prekida ako komponenta nestane prije kraja. */
export function useStations(): StationsState {
  const [state, setState] = useState<StationsState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    fetchStations(controller.signal).then(
      (data) => {
        setState({ status: 'ready', data })
      },
      (error: unknown) => {
        if (controller.signal.aborted) return
        setState({
          status: 'error',
          message: error instanceof Error ? error.message : 'Nepoznata greška',
        })
      },
    )
    return () => {
      controller.abort()
    }
  }, [])

  return state
}
