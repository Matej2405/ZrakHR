const COORDINATE = new Intl.NumberFormat('hr-HR', {
  minimumFractionDigits: 4,
  maximumFractionDigits: 4,
})

const DATE_TIME = new Intl.DateTimeFormat('hr-HR', {
  dateStyle: 'long',
  timeStyle: 'short',
  timeZone: 'Europe/Zagreb',
})

const PLURAL = new Intl.PluralRules('hr')

/** Oblici imenice za hrvatska pravila množine, npr. postaja, postaje, postaja. */
export interface NounForms {
  one: string
  few: string
  other: string
}

/** "45,8220° N, 16,0340° E" */
export function formatCoordinates(lat: number, lon: number): string {
  return `${COORDINATE.format(lat)}° N, ${COORDINATE.format(lon)}° E`
}

/** "17. studenoga 2026. u 22:57", po vremenu u Hrvatskoj bez obzira na zonu preglednika */
export function formatDateTime(iso: string): string {
  return DATE_TIME.format(new Date(iso))
}

/** Broj s imenicom u ispravnom obliku: 1 postaja, 2 postaje, 5 postaja, 21 postaja. */
export function formatCount(count: number, forms: NounForms): string {
  const category = PLURAL.select(count)
  const noun = category === 'one' || category === 'few' ? forms[category] : forms.other
  return `${String(count)} ${noun}`
}
