import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { getRouteByPredictionId, getRouteDetails } from "../services/api";

const pickupIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const deliveryIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function FitBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) {
      map.fitBounds(bounds, { padding: [40, 40] });
    }
  }, [map, bounds]);
  return null;
}

const formatRiskLevel = (risk) => String(risk ?? "UNKNOWN").toUpperCase();

const formatDuration = (minutes) => {
  if (minutes == null) return "—";
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const hrs = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  return mins > 0 ? `${hrs}h ${mins}m` : `${hrs}h`;
};

const RouteDetails = () => {
  const { prediction_id, phone_number } = useParams();
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchRoute = async () => {
      try {
        const data = prediction_id
          ? await getRouteByPredictionId(prediction_id)
          : await getRouteDetails(phone_number);
        setRoute(data);
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to load route details");
      } finally {
        setLoading(false);
      }
    };

    fetchRoute();
  }, [prediction_id, phone_number]);

  const polylinePositions = useMemo(() => {
    if (!route?.route_polyline?.length) return [];
    return route.route_polyline.map((pt) => [pt.lat, pt.lng]);
  }, [route]);

  const mapBounds = useMemo(() => {
    if (!route) return null;
    const pickup = route.pickup_coordinates;
    const delivery = route.delivery_coordinates;
    const allPoints = polylinePositions.length
      ? polylinePositions
      : [
          [pickup.lat, pickup.lng],
          [delivery.lat, delivery.lng],
        ];
    return L.latLngBounds(allPoints);
  }, [route, polylinePositions]);

  if (loading) {
    return <p style={styles.message}>Loading route details...</p>;
  }

  if (error) {
    return (
      <div>
        <p style={{ ...styles.message, color: "#ef4444" }}>{error}</p>
        <Link to="/history" style={styles.backLink}>← Back to History</Link>
      </div>
    );
  }

  const pickup = route.pickup_coordinates;
  const delivery = route.delivery_coordinates;
  const centerLat = (pickup.lat + delivery.lat) / 2;
  const centerLng = (pickup.lng + delivery.lng) / 2;
  const highRisk = String(route.risk).toLowerCase() === "high";
  const isDrivingRoute = route.route_source === "openrouteservice";

  return (
    <div>
      <Link to="/history" style={styles.backLink}>← Back to History</Link>
      <h1 style={styles.title}>Route Details</h1>

      <div style={styles.statsRow}>
        <div style={styles.statCard}>
          <span style={styles.statLabel}>Phone</span>
          <span style={styles.statValue}>{route.phone_number}</span>
        </div>
        <div style={styles.statCard}>
          <span style={styles.statLabel}>Risk</span>
          <span style={{ ...styles.statValue, color: highRisk ? "#ef4444" : "#16a34a" }}>
            {formatRiskLevel(route.risk)}
          </span>
        </div>
        <div style={styles.statCard}>
          <span style={styles.statLabel}>Distance</span>
          <span style={styles.statValue}>{route.estimated_distance_km} km</span>
        </div>
        <div style={styles.statCard}>
          <span style={styles.statLabel}>Duration</span>
          <span style={styles.statValue}>{formatDuration(route.estimated_duration_min)}</span>
        </div>
      </div>

      <div style={styles.addressRow}>
        <div style={{ ...styles.addressCard, borderLeft: "4px solid #16a34a" }}>
          <span style={styles.addressLabel}>Pickup</span>
          <p style={styles.addressText}>{route.pickup_address}</p>
          <span style={styles.districtTag}>{route.pickup_district}</span>
          {route.pickup_area && (
            <span style={styles.areaTag}>{route.pickup_area}</span>
          )}
        </div>
        <div style={{ ...styles.addressCard, borderLeft: "4px solid #ef4444" }}>
          <span style={styles.addressLabel}>Delivery</span>
          <p style={styles.addressText}>{route.delivery_address}</p>
          <span style={styles.districtTag}>{route.delivery_district}</span>
          {route.delivery_area && (
            <span style={styles.areaTag}>{route.delivery_area}</span>
          )}
        </div>
      </div>

      <div style={styles.mapWrapper}>
        <MapContainer
          center={[centerLat, centerLng]}
          zoom={13}
          style={{ height: "440px", width: "100%" }}
          scrollWheelZoom
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {mapBounds && <FitBounds bounds={mapBounds} />}
          <Marker position={[pickup.lat, pickup.lng]} icon={pickupIcon}>
            <Popup>
              <strong>Pickup</strong>
              <br />
              {route.pickup_address}
            </Popup>
          </Marker>
          <Marker position={[delivery.lat, delivery.lng]} icon={deliveryIcon}>
            <Popup>
              <strong>Delivery</strong>
              <br />
              {route.delivery_address}
            </Popup>
          </Marker>
          {polylinePositions.length > 1 && (
            <Polyline
              positions={polylinePositions}
              color="#3b82f6"
              weight={4}
              opacity={0.85}
            />
          )}
        </MapContainer>
      </div>

      <p style={styles.note}>
        {isDrivingRoute
          ? "Route calculated via OpenRouteService driving directions."
          : "Route data unavailable — check ORS_API_KEY configuration."}
      </p>
    </div>
  );
};

const styles = {
  title: {
    margin: "16px 0 20px",
    fontSize: "1.75rem",
    color: "#1e293b",
  },
  backLink: {
    color: "#3b82f6",
    textDecoration: "none",
    fontSize: "0.875rem",
    fontWeight: "600",
  },
  statsRow: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
    gap: "12px",
    marginBottom: "16px",
  },
  statCard: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    padding: "14px 16px",
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  },
  statLabel: {
    color: "#64748b",
    fontSize: "0.75rem",
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  statValue: {
    color: "#1e293b",
    fontWeight: "700",
    fontSize: "1.05rem",
  },
  addressRow: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
    gap: "12px",
    marginBottom: "16px",
  },
  addressCard: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    padding: "16px",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  addressLabel: {
    color: "#64748b",
    fontSize: "0.75rem",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  addressText: {
    margin: 0,
    color: "#334155",
    fontSize: "0.95rem",
    lineHeight: 1.4,
  },
  districtTag: {
    display: "inline-block",
    alignSelf: "flex-start",
    background: "#eff6ff",
    color: "#2563eb",
    fontSize: "0.75rem",
    fontWeight: "600",
    padding: "2px 8px",
    borderRadius: "4px",
    textTransform: "capitalize",
  },
  areaTag: {
    display: "inline-block",
    alignSelf: "flex-start",
    background: "#f0fdf4",
    color: "#16a34a",
    fontSize: "0.75rem",
    fontWeight: "600",
    padding: "2px 8px",
    borderRadius: "4px",
  },
  mapWrapper: {
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    overflow: "hidden",
  },
  note: {
    marginTop: "12px",
    fontSize: "0.8rem",
    color: "#94a3b8",
  },
  message: {
    color: "#64748b",
  },
};

export default RouteDetails;
