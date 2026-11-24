import { describe, expect, it } from 'vitest'

import {
  formatCoordinates,
  formatCount,
  formatDateTime,
  formatShortTime,
  formatValue,
} from './format'

const STATIONS = { one: 'postaja', few: 'postaje', other: 'postaja' }

describe('format', () => {
  it('koordinate piše s decimalnim zarezom i četiri decimale', () => {
    expect(formatCoordinates(45.822, 16.034)).toBe('45,8220° N, 16,0340° E')
  })

  it('vrijeme izvoza prikazuje po hrvatskom vremenu', () => {
    expect(formatDateTime('2026-11-17T21:57:50+00:00')).toBe('17. studenoga 2026. u 22:57')
  })

  it('vrijeme mjerenja piše kratko, po hrvatskom vremenu', () => {
    expect(formatShortTime('2026-11-24T07:00:00Z')).toBe('24. 11. 08:00')
  })

  it.each([
    [62.4, 'μg/m³', '62,4 μg/m³'],
    [87, '%', '87 %'],
    [1013.25, 'hPa', '1.013,3 hPa'],
    [225, '°', '225° (JZ)'],
    [350, '°', '350° (S)'],
  ])('vrijednost %s uz jedinicu %s piše kao %s', (value, unit, expected) => {
    expect(formatValue(value, unit)).toBe(expected)
  })

  it.each([
    [1, '1 postaja'],
    [2, '2 postaje'],
    [5, '5 postaja'],
    [12, '12 postaja'],
    [21, '21 postaja'],
    [74, '74 postaje'],
    [106, '106 postaja'],
  ])('broj %i slaže s imenicom: %s', (count, expected) => {
    expect(formatCount(count, STATIONS)).toBe(expected)
  })
})
