import { useColorScheme } from '../hooks/useColorScheme'
import styles from './ThemeToggle.module.css'

/** Prekidač tamne teme; dok ga korisnik ne promijeni, prati temu sustava. */
export function ThemeToggle() {
  const [scheme, toggleScheme] = useColorScheme()

  return (
    <button
      type="button"
      className={styles.toggle}
      aria-label="Tamna tema"
      aria-pressed={scheme === 'dark'}
      title="Tamna tema"
      onClick={toggleScheme}
    >
      <svg className={styles.icon} viewBox="0 0 20 20" aria-hidden="true">
        <circle cx="10" cy="10" r="7.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <path d="M10 2.75a7.25 7.25 0 0 0 0 14.5Z" fill="currentColor" />
      </svg>
    </button>
  )
}
