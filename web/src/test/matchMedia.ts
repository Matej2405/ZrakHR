/** Zamjena za window.matchMedia, koji jsdom ne implementira: zadaje temu sustava. */
export function mockSystemColorScheme(scheme: 'light' | 'dark'): void {
  window.matchMedia = (query: string) => {
    const list = {
      matches: query === '(prefers-color-scheme: dark)' && scheme === 'dark',
      media: query,
      onchange: null,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }
    // Zastarjele addListener/removeListener aplikacija ne koristi, pa ih zamjena izostavlja
    return list as unknown as MediaQueryList
  }
}
