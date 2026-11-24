/**
 * Razredi PM10 za bojenje AZO postaja na karti: jednaki razredi od 25 μg/m³, tako da je dnevna
 * granična vrijednost EU (50 μg/m³) granica razreda. Prikazuje se satna vrijednost, pa je
 * usporedba s dnevnom granicom orijentacijska; službeni indeks kvalitete zraka (EAQI) dolazi s #33.
 */

export const EU_DAILY_LIMIT = 50

const BAND_WIDTH = 25

export const PM10_BANDS = [
  { band: 1, label: 'do 25' },
  { band: 2, label: '25–50' },
  { band: 3, label: '50–75' },
  { band: 4, label: '75–100' },
  { band: 5, label: '100 i više' },
] as const

export type Pm10BandNumber = (typeof PM10_BANDS)[number]['band']

export interface Pm10Band {
  band: Pm10BandNumber
  aboveEuLimit: boolean
}

export function pm10Band(value: number): Pm10Band {
  const index = Math.min(PM10_BANDS.length - 1, Math.floor(Math.max(0, value) / BAND_WIDTH))
  const band = PM10_BANDS[index]?.band ?? 1
  return { band, aboveEuLimit: value >= EU_DAILY_LIMIT }
}
