import { describe, expect, it } from 'vitest'

import { pm10Band } from './pm10'

describe('pm10Band', () => {
  it.each([
    [0, 1],
    [24.9, 1],
    [25, 2],
    [49.9, 2],
    [50, 3],
    [74.9, 3],
    [75, 4],
    [99.9, 4],
    [100, 5],
    [420, 5],
  ])('%f μg/m³ je u razredu %i', (value, band) => {
    expect(pm10Band(value).band).toBe(band)
  })

  it('razred 3 počinje na dnevnoj graničnoj vrijednosti EU', () => {
    expect(pm10Band(49.9).aboveEuLimit).toBe(false)
    expect(pm10Band(50).aboveEuLimit).toBe(true)
  })
})
