import { useState } from "react";
import axios from "axios";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const response = await axios.post("http://127.0.0.1:8000/login", {
        username,
        password,
      });

      if (response.data.success) {
        localStorage.setItem("token", response.data.token);

        // better than alert
        window.location.href = "/dashboard";
      } else {
        setError(response.data.message || "Login failed");
      }

    } catch (err) {
      console.error(err);

      if (err.response) {
        const data = err.response.data;

        if (data.errors) {
          setError(data.errors.join(", "));
        } else {
          setError(data.message || "Login failed");
        }

      } else {
        setError("Server not responding");
      }
    }
  };

  return (
    <div className="d-flex justify-content-center align-items-center vh-100 bg-light">
      <div
        className="card border-0 shadow-lg p-4"
        style={{
          width: "380px",
          borderRadius: "12px",
        }}
      >
        <h3 className="text-center mb-4 fw-semibold">Login</h3>
  
        <form onSubmit={handleLogin}>
          <div className="mb-3">
            <input
              type="text"
              className="form-control form-control-lg"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
  
          <div className="mb-3">
            <input
              type="password"
              className="form-control form-control-lg"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
  
          <button
            className="btn btn-primary w-100 py-2 fw-semibold"
            type="submit"
          >
            Login
          </button>
  
          {error && (
            <div className="alert alert-danger mt-3 py-2 text-center">
              {error}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}