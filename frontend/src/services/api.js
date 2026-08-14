import axios from "axios";

const API = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

API.interceptors.request.use((req) => {
  const token = localStorage.getItem("token");
  if (token) {
    req.headers.Authorization = `Bearer ${token}`;
  }
  return req;
});

API.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

export const login = async (username, password) => {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);

  const res = await API.post("/login", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return res.data;
};

export const predict = async (data) => {
  const res = await API.post("/predict", data);
  return res.data;
};

export const getHistory = async () => {
  const res = await API.get("/history");
  return res.data;
};

export const getHistoryItem = async (predictionId) => {
  const res = await API.get(`/history/${predictionId}`);
  return res.data;
};

export const getRouteByPredictionId = async (predictionId) => {
  const res = await API.get(`/route/prediction/${predictionId}`);
  return res.data;
};

/** @deprecated Use getRouteByPredictionId for accurate per-prediction routes */
export const getRouteDetails = async (phoneNumber) => {
  const res = await API.get(`/route/${encodeURIComponent(phoneNumber)}`);
  return res.data;
};

export default API;
