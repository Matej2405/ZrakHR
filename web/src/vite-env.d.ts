// Varijable okoline koje aplikacija čita (Vite ih ugrađuje pri buildu)
interface ImportMetaEnv {
  /** Adresa snimke mjerenja; zadano je live/latest.json u grani data na GitHubu */
  readonly VITE_LIVE_URL?: string
}
