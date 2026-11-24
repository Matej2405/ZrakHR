import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { StationSource } from '../../api/stations'
import type { LiveState } from '../../hooks/useLive'
import { LIVE_SNAPSHOT, STATIONS_EXPORT } from '../../test/fixtures'
import { StationPanel } from './StationPanel'

interface PanelOptions {
  visibleSources?: ReadonlySet<StationSource>
  live?: LiveState
}

function renderPanel({
  visibleSources = new Set(['dhmz', 'azo']),
  live = { status: 'ready', data: LIVE_SNAPSHOT },
}: PanelOptions = {}) {
  const handlers = { onToggleSource: vi.fn(), onSelectCity: vi.fn(), onShowCroatia: vi.fn() }
  render(
    <StationPanel
      data={STATIONS_EXPORT}
      live={live}
      visibleSources={visibleSources}
      {...handlers}
    />,
  )
  return handlers
}

describe('StationPanel', () => {
  it('broji postaje po izvoru, s ispravnim oblikom imenice', () => {
    renderPanel()

    expect(screen.getByRole('checkbox', { name: /DHMZ/ })).toHaveAccessibleName(
      'DHMZ vrijeme 1 postaja',
    )
    expect(screen.getByRole('checkbox', { name: /AZO/ })).toHaveAccessibleName(
      'AZO kvaliteta zraka 3 postaje',
    )
  })

  it('prikazuje koji su izvori uključeni i javlja promjenu', async () => {
    const user = userEvent.setup()
    const { onToggleSource } = renderPanel({ visibleSources: new Set(['azo']) })
    expect(screen.getByRole('checkbox', { name: /DHMZ/ })).not.toBeChecked()

    await user.click(screen.getByRole('checkbox', { name: /AZO/ }))

    expect(onToggleSource).toHaveBeenCalledWith('azo')
  })

  it('gumbi vode na grad projekta ili na cijelu Hrvatsku', async () => {
    const user = userEvent.setup()
    const { onSelectCity, onShowCroatia } = renderPanel()

    await user.click(screen.getByRole('button', { name: 'Osijek' }))
    await user.click(screen.getByRole('button', { name: 'Cijela Hrvatska' }))

    expect(onSelectCity).toHaveBeenCalledWith(STATIONS_EXPORT.cities[1])
    expect(onShowCroatia).toHaveBeenCalledOnce()
  })

  it('navodi kada je popis postaja izvezen', () => {
    renderPanel()

    expect(screen.getByText(/17\. studenoga 2026\. u 22:57/)).toBeInTheDocument()
  })

  it('uz mjerenja navodi vrijeme snimke i legendu razreda PM10', () => {
    renderPanel()
    const live = screen.getByRole('region', { name: 'Mjerenja uživo' })

    expect(within(live).getByText(/Snimka od 24\. studenoga 2026\. u 09:05/)).toBeInTheDocument()
    expect(
      within(live)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(['do 25', '25–50', '50–75', '75–100', '100 i više', 'bez mjerenja'])
  })

  it('kad mjerenja nisu dostupna, kaže da karta prikazuje samo postaje', () => {
    renderPanel({
      live: { status: 'error', message: 'Snimka mjerenja nije dohvaćena (HTTP 404).' },
    })
    const live = screen.getByRole('region', { name: 'Mjerenja uživo' })

    expect(within(live).getByText(/karta prikazuje samo postaje/)).toBeInTheDocument()
    expect(within(live).queryByRole('list')).not.toBeInTheDocument()
  })
})
