import { useEffect, useState, useRef, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  LOCATION_PRESETS,
  VALLEY_MAP_CENTER,
} from "../utils/locationPresets";

// Standard red pin marker
const defaultIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const greenIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function LocationMarker({ position, setPosition, onLocationChange, isPickup = false }) {
  const markerRef = useRef(null);

  useMapEvents({
    click(e) {
      const newPos = { lat: e.latlng.lat, lng: e.latlng.lng };
      setPosition(newPos);
      if (onLocationChange) {
        onLocationChange(newPos);
      }
    },
  });

  const eventHandlers = useMemo(
    () => ({
      dragend() {
        const marker = markerRef.current;
        if (marker != null) {
          const latlng = marker.getLatLng();
          const newPos = { lat: latlng.lat, lng: latlng.lng };
          setPosition(newPos);
          if (onLocationChange) {
            onLocationChange(newPos);
          }
        }
      },
    }),
    [onLocationChange, setPosition]
  );

  if (!position) return null;

  return (
    <Marker
      draggable={true}
      eventHandlers={eventHandlers}
      position={[position.lat, position.lng]}
      ref={markerRef}
      icon={isPickup ? greenIcon : defaultIcon}
    >
      <Popup minWidth={90}>
        <span>
          <strong>{isPickup ? "Pickup Location" : "Delivery Pin"}</strong>
          <br />
          Drag or click map to move
        </span>
      </Popup>
    </Marker>
  );
}

function RecenterMap({ position }) {
  const map = useMapEvents({});
  useEffect(() => {
    if (position?.lat && position?.lng) {
      map.flyTo([position.lat, position.lng], map.getZoom(), { animate: true });
    }
  }, [position, map]);
  return null;
}

const MapPinPicker = ({
  initialLat = VALLEY_MAP_CENTER.lat,
  initialLng = VALLEY_MAP_CENTER.lng,
  onLocationSelect,
  isPickup = false,
  label = "Delivery Location Pin",
  height = "260px",
}) => {
  const [position, setPosition] = useState({ lat: initialLat, lng: initialLng });
  const [isConfirmed, setIsConfirmed] = useState(false);

  useEffect(() => {
    setPosition({ lat: initialLat, lng: initialLng });
  }, [initialLat, initialLng]);

  const notifySelection = (pos, addressLabel = null) => {
    if (onLocationSelect) {
      onLocationSelect(pos, addressLabel ? { address: addressLabel } : undefined);
    }
  };

  const handlePositionChange = (pos, addressLabel = null) => {
    setPosition(pos);
    setIsConfirmed(false);
    notifySelection(pos, addressLabel);
  };

  const handlePresetClick = (preset) => {
    const newPos = { lat: preset.lat, lng: preset.lng };
    handlePositionChange(newPos, preset.name);
  };

  const handleConfirm = (e) => {
    if (e) e.preventDefault();
    setIsConfirmed(true);
    notifySelection(position);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "0.85rem", fontWeight: "600", color: "#334155" }}>
          {label}
        </span>
        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
          Click or drag pin on map
        </span>
      </div>

      <div
        style={{
          border: isConfirmed ? "2px solid #16a34a" : "1px solid #cbd5e1",
          borderRadius: "10px",
          overflow: "hidden",
          position: "relative",
          boxShadow: isConfirmed ? "0 0 0 3px rgba(22, 163, 74, 0.15)" : "none",
          transition: "all 0.2s ease",
        }}
      >
        <MapContainer
          center={[position.lat, position.lng]}
          zoom={13}
          style={{ height: height, width: "100%" }}
          scrollWheelZoom={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <LocationMarker
            position={position}
            setPosition={setPosition}
            onLocationChange={(pos) => handlePositionChange(pos)}
            isPickup={isPickup}
          />
          <RecenterMap position={position} />
        </MapContainer>
      </div>

      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "2px" }}>
        <span style={{ fontSize: "0.75rem", color: "#94a3b8", alignSelf: "center", marginRight: "4px" }}>
          Presets:
        </span>
        {LOCATION_PRESETS.map((preset) => (
          <button
            key={preset.name}
            type="button"
            onClick={() => handlePresetClick(preset)}
            style={{
              fontSize: "0.75rem",
              padding: "3px 8px",
              background: "#f1f5f9",
              border: "1px solid #e2e8f0",
              borderRadius: "4px",
              color: "#334155",
              cursor: "pointer",
            }}
          >
            {preset.name}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "4px" }}>
        <button
          type="button"
          onClick={handleConfirm}
          className={`btn-modern btn-modern-sm ${isConfirmed ? "btn-modern-success" : "btn-modern-secondary"}`}
          style={{ padding: "6px 14px" }}
        >
          {isConfirmed ? "Location Confirmed" : "Confirm Location"}
        </button>
      </div>
    </div>
  );
};

export default MapPinPicker;
