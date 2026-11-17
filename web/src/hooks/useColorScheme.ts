import { useSyncExternalStore } from 'react'

export type ColorScheme = 'light' | 'dark'

/** Ključ u localStorageu; mora odgovarati skripti u index.html koja temu primjenjuje prije iscrtavanja. */
const STORAGE_KEY = 'zrakhr-theme'
const DARK_QUERY = '(prefers-color-scheme: dark)'

function readScheme(): ColorScheme {
  const chosen = document.documentElement.dataset.theme
  if (chosen === 'light' || chosen === 'dark') {
    return chosen
  }
  return window.matchMedia(DARK_QUERY).matches ? 'dark' : 'light'
}

/** Prati promjenu teme sustava i atributa data-theme, pa sve komponente vide istu shemu boja. */
function subscribe(onChange: () => void): () => void {
  const media = window.matchMedia(DARK_QUERY)
  const observer = new MutationObserver(onChange)
  media.addEventListener('change', onChange)
  observer.observe(document.documentElement, { attributeFilter: ['data-theme'] })
  return () => {
    media.removeEventListener('change', onChange)
    observer.disconnect()
  }
}

/** Aktivna shema boja (izbor korisnika ili, ako ga nema, postavka sustava) i njezin prekidač. */
export function useColorScheme(): [ColorScheme, () => void] {
  const scheme = useSyncExternalStore(subscribe, readScheme)

  function toggleScheme() {
    const next: ColorScheme = scheme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Spremanje nije moguće (npr. blokirani kolačići); izbor vrijedi do osvježavanja stranice
    }
  }

  return [scheme, toggleScheme]
}
