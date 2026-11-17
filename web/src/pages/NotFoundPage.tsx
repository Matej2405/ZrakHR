import { Link, useLocation } from 'react-router'

import { Page } from '../components/Page'

export function NotFoundPage() {
  const { pathname } = useLocation()

  return (
    <Page
      title="Stranica ne postoji"
      lede={`Adresa ${pathname} ne odgovara nijednoj stranici ZrakHR-a.`}
    >
      <p>
        <Link to="/">Otvori pregled</Link>
      </p>
    </Page>
  )
}
