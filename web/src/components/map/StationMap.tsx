import 'leaflet/dist/leaflet.css'
import './map.css'

import { divIcon, type DivIcon, type Map as LeafletMap } from 'leaflet'
import type { Ref } from 'react'
import { Circle, MapContainer, Marker, Popup, TileLayer, Tooltip } from 'react-leaflet'

import type { City, StationSource } from '../../api/stations'
import { useColorScheme } from '../../hooks/useColorScheme'
import { CITY_RADIUS_M, CROATIA_BOUNDS } from './constants'
import type { StationLocation } from './locations'
import { prefersReducedMotion } from './motion'
import styles from './StationMap.module.css'
import { StationPopup } from './StationPopup'

// OpenStreetMap ne traži API ključ; map.css podlogu prigušuje ili za tamnu temu invertira,
// da se oznake postaja jasno ističu
const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
const TILE_CLASS = { light: 'zr-tiles', dark: 'zr-tiles zr-tiles-dark' }

// Oblik oznake razlikuje izvor neovisno o boji: krug za DHMZ, romb za AZO (vidi map.css).
// Element je 24 × 24 px, koliko WCAG traži za cilj dodira, a vidljivi oblik je manji.
const ICONS: Record<StationSource, DivIcon> = {
  dhmz: divIcon({ className: 'zr-marker zr-marker-dhmz', iconSize: [24, 24] }),
  azo: divIcon({ className: 'zr-marker zr-marker-azo', iconSize: [24, 24] }),
}

interface StationMapProps {
  locations: StationLocation[]
  cities: City[]
  ref?: Ref<LeafletMap>
}

export function StationMap({ locations, cities, ref }: StationMapProps) {
  const [scheme] = useColorScheme()
  // Leaflet ne prati postavku sustava za animacije, pa se prijelazi isključuju ovdje
  const animate = !prefersReducedMotion()

  return (
    <MapContainer
      ref={ref}
      className={styles.map}
      bounds={CROATIA_BOUNDS}
      fadeAnimation={animate}
      zoomAnimation={animate}
      markerZoomAnimation={animate}
    >
      {/* className se postavlja samo pri stvaranju sloja, pa promjena teme stvara novi sloj */}
      <TileLayer
        key={scheme}
        url={TILE_URL}
        attribution={ATTRIBUTION}
        className={TILE_CLASS[scheme]}
      />
      {cities.map((city) => (
        <Circle
          key={city.name}
          center={[city.lat, city.lon]}
          radius={CITY_RADIUS_M}
          // Leaflet klasu postavlja samo pri stvaranju; kroz pathOptions (setStyle) ne bi stigla
          className="zr-city-area"
          interactive={false}
        >
          <Tooltip permanent direction="top" offset={[0, -8]} className="zr-city-label">
            {city.name}
          </Tooltip>
        </Circle>
      ))}
      {locations.map((location) => (
        <Marker
          key={location.key}
          position={[location.lat, location.lon]}
          icon={ICONS[location.source]}
          title={location.stations.map((station) => station.name).join(', ')}
        >
          <Popup>
            <StationPopup location={location} />
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
