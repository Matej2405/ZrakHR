import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { liveIndex, type LiveStation } from '../../api/live'
import type { Station } from '../../api/stations'
import { LIVE_SNAPSHOT, MAKSIMIR, OSIJEK_2, OSIJEK_2_PM25, ZAGREB_1 } from '../../test/fixtures'
import { groupByLocation } from './locations'
import { StationPopup } from './StationPopup'

const LIVE = liveIndex(LIVE_SNAPSHOT)

function renderPopupFor(stations: Station[], live?: ReadonlyMap<string, LiveStation>) {
  const [location] = groupByLocation(stations)
  if (!location) throw new Error('Primjer mora imati barem jednu postaju')
  render(<StationPopup location={location} live={live} />)
}

describe('StationPopup', () => {
  it('za postaje na istoj lokaciji navodi svaku s mrežom, a koordinate jednom', () => {
    renderPopupFor([OSIJEK_2, OSIJEK_2_PM25])

    expect(screen.getByText('OSIJEK-2')).toBeInTheDocument()
    expect(screen.getByText('OSIJEK-2 PPI PM2,5')).toBeInTheDocument()
    expect(screen.getAllByText(OSIJEK_2.network)).toHaveLength(2)
    expect(screen.getByText('45,5577° N, 18,7309° E')).toBeInTheDocument()
  })

  it('za DHMZ postaju navodi izvor i vrstu postaje', () => {
    renderPopupFor([MAKSIMIR])

    expect(screen.getByText('DHMZ, vrijeme')).toBeInTheDocument()
    expect(screen.getByText('postaja s motriteljem')).toBeInTheDocument()
  })

  it('uz AZO postaju navodi zadnja mjerenja, granicu EU i raspon PM10 za 48 sati', () => {
    renderPopupFor([OSIJEK_2, OSIJEK_2_PM25], LIVE)

    expect(screen.getByText('Mjereno 24. 11. 08:00')).toBeInTheDocument()
    expect(screen.getByText('62,4 μg/m³ (iznad granice EU)')).toBeInTheDocument()
    expect(screen.getByText('41 μg/m³')).toBeInTheDocument()
    expect(
      screen.getByText('48 h: od 48,1 μg/m³ do 62,4 μg/m³ (crtkano: granica EU)'),
    ).toBeInTheDocument()
    // Mjerenja ima samo OSIJEK-2, pa se navode jednom
    expect(screen.getAllByText(/^Mjereno/)).toHaveLength(1)
  })

  it('uz DHMZ postaju navodi vrijeme, a smjer vjetra i sa stranom svijeta', () => {
    renderPopupFor([MAKSIMIR], LIVE)

    expect(screen.getByText('Mjereno 24. 11. 09:00')).toBeInTheDocument()
    expect(screen.getByText('4,2 °C')).toBeInTheDocument()
    expect(screen.getByText('87 %')).toBeInTheDocument()
    expect(screen.getByText('2,1 m/s')).toBeInTheDocument()
    expect(screen.getByText('225° (JZ)')).toBeInTheDocument()
    // Starije mjerenje nosi svoje vrijeme, da se ne čita kao da je iz istog sata
    expect(screen.getByText('0,8 hPa (24. 11. 07:00)')).toBeInTheDocument()
    // Graf je samo za PM10
    expect(screen.queryByRole('figure')).not.toBeInTheDocument()
  })

  it('postaja bez mjerenja u zadnja 24 sata nema dijela s mjerenjima', () => {
    renderPopupFor([ZAGREB_1], LIVE)

    expect(screen.getByText('ZAGREB-1')).toBeInTheDocument()
    expect(screen.queryByText(/^Mjereno/)).not.toBeInTheDocument()
  })
})
