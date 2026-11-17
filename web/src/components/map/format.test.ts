import { describe, expect, it } from 'vitest'

import { formatCoordinates, formatCount, formatDateTime } from './format'

const STATIONS = { one: 'postaja', few: 'postaje', other: 'postaja' }

describe('format', () => {
  it('koordinate piše s decimalnim zarezom i četiri decimale', () => {
    expect(formatCoordinates(45.822, 16.034)).toBe('45,8220° N, 16,0340° E')
  })

  it('vrijeme izvoza prikazuje po hrvatskom vremenu', () => {
    expect(formatDateTime('2026-11-17T21:57:50+00:00')).toBe('17. studenoga 2026. u 22:57')
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
