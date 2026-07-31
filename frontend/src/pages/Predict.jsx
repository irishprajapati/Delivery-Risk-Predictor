import { useState } from "react";
import { predict } from "../services/api";

const INITIAL_FORM = {
  phone_number: "",
  pickup_address: "",
  delivery_address: "",
  order_value: "",
  payment_method: "cod",
  weather_condition: "normal",
};

const Predict = () => {
  const [form, setForm] = useState(INITIAL_FORM);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    const payload = {
      ...form,
      order_value: Number(form.order_value),
    };

    try {
      const data = await predict(payload);
      setResult(data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg).join(", "));
      } else if (typeof detail === "string") {
        setError(detail);
      } else {
        setError("Failed to get prediction");
      }
    } finally {
      setLoading(false);
    }
  };

  const isHighRisk = result?.risk?.toUpperCase() === "HIGH";

  return (
    <div>
      <h1 style={styles.title}>Predict Delivery Risk</h1>

      <form onSubmit={handleSubmit} style={styles.form}>
        <div style={styles.grid}>
          <Field label="Phone Number">
            <input
              name="phone_number"
              value={form.phone_number}
              onChange={handleChange}
              placeholder="98XXXXXXXX"
              required
              style={styles.input}
            />
          </Field>

          <Field label="Order Value (NPR)">
            <input
              type="number"
              name="order_value"
              value={form.order_value}
              onChange={handleChange}
              placeholder="e.g. 1500"
              min={1}
              step="0.01"
              required
              style={styles.input}
            />
          </Field>

          <Field label="Pickup Address" full>
            <input
              name="pickup_address"
              value={form.pickup_address}
              onChange={handleChange}
              placeholder="Central Warehouse, Kathmandu"
              required
              style={styles.input}
            />
          </Field>

          <Field label="Delivery Address" full>
            <input
              name="delivery_address"
              value={form.delivery_address}
              onChange={handleChange}
              placeholder="Thamel, Kathmandu"
              required
              style={styles.input}
            />
          </Field>

          <Field label="Payment Method">
            <select
              name="payment_method"
              value={form.payment_method}
              onChange={handleChange}
              style={styles.input}
            >
              <option value="cod">COD</option>
              <option value="prepaid">Prepaid</option>
            </select>
          </Field>

          <Field label="Weather">
            <select
              name="weather_condition"
              value={form.weather_condition}
              onChange={handleChange}
              style={styles.input}
            >
              <option value="normal">Normal</option>
              <option value="rainy">Rainy</option>
              <option value="foggy">Foggy</option>
              <option value="clear">Clear</option>
            </select>
          </Field>
        </div>

        <button type="submit" disabled={loading} style={styles.button}>
          {loading ? "Predicting..." : "Run Prediction"}
        </button>
      </form>

      {error && <div style={styles.error}>{error}</div>}

      {result && (
        <div style={styles.resultCard}>
          <h2 style={styles.resultTitle}>Prediction Result</h2>
          <p style={styles.resultRow}>
            <strong>Phone:</strong> {result.phone_number}
          </p>
          <p style={styles.resultRow}>
            <strong>Prediction:</strong>{" "}
            {result.prediction === 1 ? "Delivery Failure Likely" : "Delivery Success Likely"}
          </p>
          <p style={styles.resultRow}>
            <strong>Risk Level:</strong>{" "}
            <span style={{ color: isHighRisk ? "#ef4444" : "#16a34a", fontWeight: "700" }}>
              {String(result.risk).toUpperCase()}
            </span>
          </p>
          {result.actions?.length > 0 && (
            <div style={{ marginTop: "12px" }}>
              <strong>Recommended Actions:</strong>
              <ul style={{ margin: "8px 0 0", paddingLeft: "20px" }}>
                {result.actions.map((action, i) => (
                  <li key={i}>{action}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

function Field({ label, children, full }) {
  return (
    <label style={{ ...styles.field, ...(full ? styles.fieldFull : {}) }}>
      <span style={styles.label}>{label}</span>
      {children}
    </label>
  );
}

const styles = {
  title: {
    margin: "0 0 24px",
    fontSize: "1.75rem",
    color: "#1e293b",
  },
  form: {
    background: "#f8fafc",
    padding: "24px",
    borderRadius: "8px",
    border: "1px solid #e2e8f0",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "16px",
  },
  field: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  fieldFull: {
    gridColumn: "1 / -1",
  },
  label: {
    fontSize: "0.875rem",
    fontWeight: "600",
    color: "#475569",
  },
  input: {
    padding: "10px 12px",
    borderRadius: "6px",
    border: "1px solid #cbd5e1",
    fontSize: "0.95rem",
  },
  button: {
    marginTop: "20px",
    background: "#2563eb",
    color: "white",
    border: "none",
    padding: "12px 24px",
    borderRadius: "6px",
    fontWeight: "600",
    cursor: "pointer",
    fontSize: "1rem",
  },
  error: {
    marginTop: "16px",
    padding: "12px 16px",
    background: "#fef2f2",
    color: "#ef4444",
    borderRadius: "6px",
    border: "1px solid #fecaca",
  },
  resultCard: {
    marginTop: "24px",
    padding: "20px 24px",
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    textAlign: "left",
  },
  resultTitle: {
    margin: "0 0 12px",
    fontSize: "1.125rem",
    color: "#1e293b",
  },
  resultRow: {
    margin: "8px 0",
    color: "#334155",
  },
};

export default Predict;
