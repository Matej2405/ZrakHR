import { SOURCE_LABELS } from './constants'
import { formatCoordinates } from './format'
import type { StationLocation } from './locations'

/** Sadržaj oblačića oznake: svaka postaja na lokaciji s izvorom i mrežom ili vrstom postaje. */
export function StationPopup({ location }: { location: StationLocation }) {
  return (
    <div className="zr-popup">
      {location.stations.map((station) => (
        <div key={station.external_id} className="zr-popup-station">
          <strong className="zr-popup-name">{station.name}</strong>
          <dl>
            <dt>Izvor</dt>
            <dd>
              {SOURCE_LABELS[station.source].name}, {SOURCE_LABELS[station.source].measures}
            </dd>
            {station.source === 'azo' ? (
              <>
                <dt>Mreža</dt>
                <dd>{station.network}</dd>
              </>
            ) : (
              <>
                <dt>Vrsta</dt>
                <dd>{station.automatic ? 'automatska postaja' : 'postaja s motriteljem'}</dd>
              </>
            )}
          </dl>
        </div>
      ))}
      <p className="zr-popup-coordinates">{formatCoordinates(location.lat, location.lon)}</p>
    </div>
  )
}
