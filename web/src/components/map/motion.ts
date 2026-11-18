/** Korisnik je u sustavu zatražio manje animacija; karta tada skače bez preleta i prijelaza. */
export function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}
