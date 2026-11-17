import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MAKSIMIR, OSIJEK_2, OSIJEK_2_PM25 } from '../../test/fixtures'
import { groupByLocation } from './locations'
import { StationPopup } from './StationPopup'

function renderPopupFor(...stations: Parameters<typeof groupByLocation>[0]) {
  const [location] = groupByLocation(stations)
  if (!location) throw new Error('Primjer mora imati barem jednu postaju')
  render(<StationPopup location={location} />)
}

describe('StationPopup', () => {
  it('za postaje na istoj lokaciji navodi svaku s mrežom, a koordinate jednom', () => {
    renderPopupFor(OSIJEK_2, OSIJEK_2_PM25)

    expect(screen.getByText('OSIJEK-2')).toBeInTheDocument()
    expect(screen.getByText('OSIJEK-2 PPI PM2,5')).toBeInTheDocument()
    expect(screen.getAllByText(OSIJEK_2.network)).toHaveLength(2)
    expect(screen.getByText('45,5577° N, 18,7309° E')).toBeInTheDocument()
  })

  it('za DHMZ postaju navodi izvor i vrstu postaje', () => {
    renderPopupFor(MAKSIMIR)

    expect(screen.getByText('DHMZ, vrijeme')).toBeInTheDocument()
    expect(screen.getByText('postaja s motriteljem')).toBeInTheDocument()
  })
})
