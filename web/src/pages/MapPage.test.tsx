import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { LIVE_URL, type LiveStation } from '../api/live'
import { STATIONS_URL } from '../api/stations'
import type { StationLocation } from '../components/map/locations'
import { LIVE_SNAPSHOT, STATIONS_EXPORT } from '../test/fixtures'
import { MapPage } from './MapPage'

// Leaflet treba stvarne dimenzije elemenata, kojih u jsdomu nema; test provjerava što stranica
// šalje karti, a samu kartu provjerava pregled u pregledniku
vi.mock('../components/map/StationMap', () => ({
  StationMap: ({
    locations,
    live,
  }: {
    locations: StationLocation[]
    live: ReadonlyMap<string, LiveStation>
  }) => (
    <>
      <output aria-label="Oznake na karti">{locations.length}</output>
      <output aria-label="Postaje s mjerenjima">{live.size}</output>
    </>
  ),
}))

const json = (data: unknown) => () => new Response(JSON.stringify(data))
const missing = () => new Response('', { status: 404 })

/** Odgovara na dohvat izvoza postaja i snimke mjerenja; tijelo odgovora čita se samo jednom */
function serve({ stations = json(STATIONS_EXPORT), live = json(LIVE_SNAPSHOT) } = {}) {
  const routes = new Map([
    [STATIONS_URL, stations],
    [LIVE_URL, live],
  ])
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => Promise.resolve((routes.get(url) ?? missing)())),
  )
}

describe('MapPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('nakon učitavanja prikazuje sve izvore i oznaku za svaku lokaciju', async () => {
    serve()
    render(<MapPage />)

    expect(await screen.findByRole('checkbox', { name: /DHMZ/ })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: /AZO/ })).toBeChecked()
    expect(screen.getByRole('status', { name: 'Oznake na karti' })).toHaveTextContent(/^3$/)
  })

  it('isključen izvor uklanja svoje oznake s karte', async () => {
    serve()
    const user = userEvent.setup()
    render(<MapPage />)

    await user.click(await screen.findByRole('checkbox', { name: /DHMZ/ }))

    expect(screen.getByRole('status', { name: 'Oznake na karti' })).toHaveTextContent(/^2$/)
  })

  it('kad izvoz nije dostupan, kaže kako ga ponovno stvoriti', async () => {
    serve({ stations: missing })
    render(<MapPage />)

    expect(await screen.findByText(/HTTP 404/)).toBeInTheDocument()
    expect(screen.getByText(/scripts\/export_stations\.py/)).toBeInTheDocument()
  })

  it('mjerenja iz snimke šalje karti i navodi vrijeme snimke', async () => {
    serve()
    render(<MapPage />)

    expect(await screen.findByText(/Snimka od 24\. studenoga 2026\. u 09:05/)).toBeInTheDocument()
    expect(screen.getByRole('status', { name: 'Postaje s mjerenjima' })).toHaveTextContent(/^2$/)
  })

  it('bez snimke mjerenja karta i dalje prikazuje postaje', async () => {
    serve({ live: missing })
    render(<MapPage />)

    expect(await screen.findByText(/karta prikazuje samo postaje/)).toBeInTheDocument()
    expect(screen.getByRole('status', { name: 'Oznake na karti' })).toHaveTextContent(/^3$/)
    expect(screen.getByRole('status', { name: 'Postaje s mjerenjima' })).toHaveTextContent(/^0$/)
  })
})
