import './map.css'

import { useId } from 'react'

import type { City, StationsExport, StationSource } from '../../api/stations'
import { CITY_RADIUS_M, SOURCE_LABELS, SOURCES } from './constants'
import { formatCount, formatDateTime } from './format'
import styles from './StationPanel.module.css'

const STATION_FORMS = { one: 'postaja', few: 'postaje', other: 'postaja' }

interface StationPanelProps {
  data: StationsExport
  visibleSources: ReadonlySet<StationSource>
  onToggleSource: (source: StationSource) => void
  onSelectCity: (city: City) => void
  onShowCroatia: () => void
}

/** Kontrole karte: koji se izvori prikazuju, skok na grad projekta i porijeklo podataka. */
export function StationPanel({
  data,
  visibleSources,
  onToggleSource,
  onSelectCity,
  onShowCroatia,
}: StationPanelProps) {
  const citiesHeadingId = useId()

  return (
    <div className={styles.panel}>
      <header className={styles.intro}>
        <h1 className={styles.title}>Karta postaja</h1>
        <p className={styles.lede}>
          Mjerne postaje DHMZ-a i AZO-a te gradovi u kojima projekt prati kvalitetu zraka.
        </p>
      </header>

      <fieldset className={styles.section}>
        <legend className={styles.heading}>Postaje na karti</legend>
        {SOURCES.map((source) => (
          <label key={source} className={styles.source}>
            <input
              type="checkbox"
              checked={visibleSources.has(source)}
              onChange={() => {
                onToggleSource(source)
              }}
            />
            {/* Ista oznaka kao na karti, pa ploča služi i kao legenda */}
            <span
              className={[styles.symbol, 'zr-marker', `zr-marker-${source}`].join(' ')}
              aria-hidden="true"
            />
            {/* Razmaci odvajaju riječi u nazivu checkboxa; u gridu ne utječu na raspored */}
            <span className={styles.sourceText}>
              <span className={styles.sourceName}>{SOURCE_LABELS[source].name}</span>{' '}
              <span className={styles.secondary}>{SOURCE_LABELS[source].measures}</span>
            </span>{' '}
            <span className={styles.count}>
              {formatCount(
                data.stations.filter((station) => station.source === source).length,
                STATION_FORMS,
              )}
            </span>
          </label>
        ))}
      </fieldset>

      <section className={styles.section} aria-labelledby={citiesHeadingId}>
        <h2 id={citiesHeadingId} className={styles.heading}>
          Gradovi projekta
        </h2>
        <div className={styles.cities}>
          {data.cities.map((city) => (
            <button
              key={city.name}
              type="button"
              className={styles.city}
              onClick={() => {
                onSelectCity(city)
              }}
            >
              {city.name}
            </button>
          ))}
          <button type="button" className={styles.city} onClick={onShowCroatia}>
            Cijela Hrvatska
          </button>
        </div>
        <p className={styles.secondary}>
          Isprekidani krug oko grada ima polumjer {CITY_RADIUS_M / 1000} km.
        </p>
      </section>

      <p className={styles.secondary}>
        Popis postaja izvezen je {formatDateTime(data.generated_at)} iz podataka{' '}
        <a href={data.sources.dhmz}>DHMZ-a</a> i <a href={data.sources.azo}>AZO-a</a>.
      </p>
    </div>
  )
}
