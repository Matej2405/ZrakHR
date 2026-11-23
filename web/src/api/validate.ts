/**
 * Provjera oblika podataka koji dolaze izvan aplikacije (izvoz postaja, snimka mjerenja).
 * Greška navodi točno polje, npr. "Neispravan izvoz postaja: stations[3].lat mora biti broj."
 */

export type JsonObject = Record<string, unknown>

export function isObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function invalid(subject: string, path: string, expected: string): never {
  throw new Error(`${subject}: ${path} mora biti ${expected}.`)
}

export function text(subject: string, object: JsonObject, key: string, path: string): string {
  const value = object[key]
  return typeof value === 'string' ? value : invalid(subject, `${path}.${key}`, 'tekst')
}

export function finiteNumber(
  subject: string,
  object: JsonObject,
  key: string,
  path: string,
): number {
  const value = object[key]
  return typeof value === 'number' && Number.isFinite(value)
    ? value
    : invalid(subject, `${path}.${key}`, 'broj')
}
