import { lazy, Suspense } from 'react'

import { Page } from '../components/Page'

// Karta s Leafletom učitava se tek kad je korisnik otvori, pa ne usporava ostale stranice
const MapPage = lazy(() => import('./MapPage').then((module) => ({ default: module.MapPage })))

export function LazyMapPage() {
  return (
    <Suspense fallback={<Page title="Karta postaja" lede="Učitavam kartu…" />}>
      <MapPage />
    </Suspense>
  )
}
