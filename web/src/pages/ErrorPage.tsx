import { isRouteErrorResponse, useRouteError } from 'react-router'

import { Page } from '../components/Page'

function describe(error: unknown): string {
  if (isRouteErrorResponse(error)) {
    return `${String(error.status)} ${error.statusText}`
  }
  return error instanceof Error ? error.message : 'Nepoznata greška'
}

/** Prikazuje se umjesto stranice koja se srušila; zaglavlje i navigacija ostaju dostupni. */
export function ErrorPage() {
  const error = useRouteError()

  return (
    <Page
      title="Prikaz stranice nije uspio"
      lede="Ostale stranice rade normalno: otvorite neku iz navigacije ili osvježite ovu."
    >
      <p>Greška: {describe(error)}</p>
    </Page>
  )
}
