import type { Map as LeafletMap } from 'leaflet'
import { useMemo, useState } from 'react'

import { liveIndex, type LiveStation } from '../api/live'
import type { City, StationSource } from '../api/stations'
import { CROATIA_BOUNDS, SOURCES } from '../components/map/constants'
import { groupByLocation } from '../components/map/locations'
import { prefersReducedMotion } from '../components/map/motion'
import { StationMap } from '../components/map/StationMap'
import { StationPanel } from '../components/map/StationPanel'
import { Page } from '../components/Page'
import { useLive } from '../hooks/useLive'
import { useStations } from '../hooks/useStations'
import styles from './MapPage.module.css'

/** Zoom na kojem se vide sve postaje unutar kruga oko grada */
const CITY_ZOOM = 11

const NO_LIVE: ReadonlyMap<string, LiveStation> = new Map()

export function MapPage() {
  const stations = useStations()
  // Mjerenja su dodatak: bez njih karta i dalje prikazuje postaje
  const live = useLive()
  const liveStations = useMemo(
    () => (live.status === 'ready' ? liveIndex(live.data) : NO_LIVE),
    [live],
  )
  const [map, setMap] = useState<LeafletMap | null>(null)
  const [visibleSources, setVisibleSources] = useState<ReadonlySet<StationSource>>(
    () => new Set(SOURCES),
  )

  if (stations.status === 'loading') {
    return <Page title="Karta postaja" lede="Učitavam popis postaja…" />
  }

  if (stations.status === 'error') {
    return (
      <Page title="Karta postaja" lede={stations.message}>
        <p>
          Izvoz ponovno stvara naredba <code>python scripts/export_stations.py</code> iz korijena
          repozitorija; nakon nje osvježite stranicu.
        </p>
      </Page>
    )
  }

  const { data } = stations
  const locations = groupByLocation(
    data.stations.filter((station) => visibleSources.has(station.source)),
  )

  function toggleSource(source: StationSource) {
    setVisibleSources((current) => {
      const next = new Set(current)
      if (next.has(source)) {
        next.delete(source)
      } else {
        next.add(source)
      }
      return next
    })
  }

  function showCity(city: City) {
    map?.flyTo([city.lat, city.lon], CITY_ZOOM, { animate: !prefersReducedMotion() })
  }

  function showCroatia() {
    map?.flyToBounds(CROATIA_BOUNDS, { animate: !prefersReducedMotion() })
  }

  return (
    <div className={styles.layout}>
      <title>Karta postaja – ZrakHR</title>
      <div className={styles.panel}>
        <StationPanel
          data={data}
          live={live}
          visibleSources={visibleSources}
          onToggleSource={toggleSource}
          onSelectCity={showCity}
          onShowCroatia={showCroatia}
        />
      </div>
      <div className={styles.map}>
        <StationMap ref={setMap} locations={locations} cities={data.cities} live={liveStations} />
      </div>
    </div>
  )
}
