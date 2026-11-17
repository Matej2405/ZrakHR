import { Link, NavLink, Outlet } from 'react-router'

import styles from './AppShell.module.css'
import { ThemeToggle } from './ThemeToggle'

const NAV_ITEMS = [
  { to: '/', label: 'Pregled' },
  { to: '/karta', label: 'Karta' },
  { to: '/analiza', label: 'Analiza' },
  { to: '/status', label: 'Status' },
]

/** Okvir svih stranica: zaglavlje s glavnom navigacijom i sadržaj aktivne rute. */
export function AppShell() {
  return (
    <div className={styles.shell}>
      <a className={styles.skipLink} href="#sadrzaj">
        Preskoči na sadržaj
      </a>
      <header className={styles.header}>
        <Link className={styles.wordmark} to="/">
          ZrakHR
        </Link>
        <nav className={styles.nav} aria-label="Glavna navigacija">
          <ul className={styles.navList}>
            {NAV_ITEMS.map(({ to, label }) => (
              <li key={to}>
                <NavLink className={styles.navLink} to={to}>
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className={styles.actions}>
          <ThemeToggle />
        </div>
      </header>
      <main id="sadrzaj" className={styles.main} tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  )
}
