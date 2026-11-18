import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { StationSource } from '../../api/stations'
import { STATIONS_EXPORT } from '../../test/fixtures'
import { StationPanel } from './StationPanel'

function renderPanel(visibleSources: ReadonlySet<StationSource> = new Set(['dhmz', 'azo'])) {
  const handlers = { onToggleSource: vi.fn(), onSelectCity: vi.fn(), onShowCroatia: vi.fn() }
  render(<StationPanel data={STATIONS_EXPORT} visibleSources={visibleSources} {...handlers} />)
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
    const { onToggleSource } = renderPanel(new Set(['azo']))
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
})
