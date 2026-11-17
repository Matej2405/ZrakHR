import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { StationLocation } from '../components/map/locations'
import { STATIONS_EXPORT } from '../test/fixtures'
import { MapPage } from './MapPage'

// Leaflet treba stvarne dimenzije elemenata, kojih u jsdomu nema; test provjerava što stranica
// šalje karti, a samu kartu provjerava pregled u pregledniku
vi.mock('../components/map/StationMap', () => ({
  StationMap: ({ locations }: { locations: StationLocation[] }) => (
    <output aria-label="Oznake na karti">{locations.length}</output>
  ),
}))

function serveExport(response: Response) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
}

describe('MapPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('nakon učitavanja prikazuje sve izvore i oznaku za svaku lokaciju', async () => {
    serveExport(new Response(JSON.stringify(STATIONS_EXPORT)))
    render(<MapPage />)

    expect(await screen.findByRole('checkbox', { name: /DHMZ/ })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: /AZO/ })).toBeChecked()
    expect(screen.getByRole('status', { name: 'Oznake na karti' })).toHaveTextContent(/^3$/)
  })

  it('isključen izvor uklanja svoje oznake s karte', async () => {
    serveExport(new Response(JSON.stringify(STATIONS_EXPORT)))
    const user = userEvent.setup()
    render(<MapPage />)

    await user.click(await screen.findByRole('checkbox', { name: /DHMZ/ }))

    expect(screen.getByRole('status', { name: 'Oznake na karti' })).toHaveTextContent(/^2$/)
  })

  it('kad izvoz nije dostupan, kaže kako ga ponovno stvoriti', async () => {
    serveExport(new Response('', { status: 404 }))
    render(<MapPage />)

    expect(await screen.findByText(/HTTP 404/)).toBeInTheDocument()
    expect(screen.getByText(/scripts\/export_stations\.py/)).toBeInTheDocument()
  })
})
