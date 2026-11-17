import type { ReactNode } from 'react'

import styles from './Page.module.css'

interface PageProps {
  title: string
  lede: string
  children?: ReactNode
}

/** Zajednički okvir stranice: naslov u kartici preglednika, naslov stranice i uvodna rečenica. */
export function Page({ title, lede, children }: PageProps) {
  return (
    <div className={styles.page}>
      <title>{`${title} – ZrakHR`}</title>
      <h1 className={styles.title}>{title}</h1>
      <p className={styles.lede}>{lede}</p>
      {children}
    </div>
  )
}

/** Najava sadržaja koji još nije izrađen: što će biti prikazano i o čemu ovisi. */
export function Planned({ children }: { children: ReactNode }) {
  return <p className={styles.planned}>{children}</p>
}
