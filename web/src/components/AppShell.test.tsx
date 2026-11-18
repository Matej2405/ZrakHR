import { render, screen, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { routes } from '../router'

// Test provjerava okvir i navigaciju, pa karta (Leaflet i dohvat postaja) nije potrebna
vi.mock('../pages/MapPage', () => ({ MapPage: () => <h1>Karta postaja</h1> }))

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(<RouterProvider router={router} />)
  return screen.getByRole('navigation', { name: 'Glavna navigacija' })
}

describe('AppShell', () => {
  it('prikazuje glavnu navigaciju sa sve četiri stranice', () => {
    const nav = renderAt('/')

    const labels = within(nav)
      .getAllByRole('link')
      .map((link) => link.textContent)
    expect(labels).toEqual(['Pregled', 'Karta', 'Analiza', 'Status'])
  })

  it('označava trenutnu stranicu u navigaciji', async () => {
    const nav = renderAt('/karta')

    expect(within(nav).getByRole('link', { name: 'Karta' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: 'Pregled' })).not.toHaveAttribute('aria-current')
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Karta postaja' }),
    ).toBeInTheDocument()
  })

  it('nepoznatu adresu prikazuje unutar okvira, uz dostupnu navigaciju', () => {
    const nav = renderAt('/ne-postoji')

    expect(
      screen.getByRole('heading', { level: 1, name: 'Stranica ne postoji' }),
    ).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'Pregled' })).toBeInTheDocument()
  })
})
