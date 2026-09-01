import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000",
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
    const status = err.response?.status;
    const url = err.config?.url || "";
    const isAuthEndpoint =
      url.includes("/login") || url.includes("/register") || url.includes("/verify-otp");

    // 401 Unauthorized: Session token is missing, invalid, or expired -> Log out and redirect to login
    if (status === 401 && !isAuthEndpoint) {
      localStorage.removeItem("token");
      localStorage.removeItem("role");
      localStorage.removeItem("phone");

      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }

    // 403 Forbidden: Permission error (e.g. access denied for current role) -> Return error to UI without logging out
    return Promise.reject(err);
  }
);

/* ============================================================
   AUTH
============================================================ */

export const login = async (role, identifier, password) => {
  let endpoint;
  let params;

  if (role === "admin") {
    endpoint = "/admin/login";
    params = {
      username: identifier,
      password: password,
    };
  } else if (role === "rider") {
    endpoint = "/rider/login";
    params = {
      phone: identifier,
      password: password,
    };
  } else {
    endpoint = "/customer/login";
    params = {
      phone: identifier,
      password: password,
    };
  }

  const res = await API.post(endpoint, null, {
    params,
  });

  return res.data;
};

export const register = async (phone, password) => {
  const res = await API.post("/register", {
    phone,
    password,
  });
  return res.data;
};

export const verifyOTP = async (phone, otp) => {
  const res = await API.post("/verify-otp", {
    phone,
    otp,
  });
  return res.data;
};

/* ============================================================
   CUSTOMER PORTAL
============================================================ */

export const getCustomerProfile = async () => {
  const res = await API.get("/customer/profile");
  return res.data;
};

export const updateCustomerProfile = async (profileData) => {
  const res = await API.put("/customer/profile", profileData);
  return res.data;
};

export const changeCustomerPassword = async (currentPassword, newPassword) => {
  const res = await API.post("/customer/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return res.data;
};

export const getCustomerOrders = async () => {
  const res = await API.get("/customer/orders");
  return res.data;
};

export const getCustomerOrder = async (orderId) => {
  const res = await API.get(`/customer/orders/${orderId}`);
  return res.data;
};

export const getItems = async () => {
  const res = await API.get("/items");
  return res.data;
};

export const getCategories = async () => {
  const res = await API.get("/categories");
  return res.data;
};

export const placeOrder = async (orderData) => {
  const res = await API.post("/place-order", orderData);
  return res.data;
};

/* ============================================================
   ADMIN OPERATIONS
============================================================ */

export const getAdminDashboard = async () => {
  const res = await API.get("/admin/dashboard");
  return res.data;
};

export const getAdminDeliveries = async (params = {}) => {
  const res = await API.get("/admin/deliveries", { params });
  return res.data;
};

export const getDeliverySummary = async (deliveryId) => {
  const res = await API.get(`/admin/deliveries/${deliveryId}`);
  return res.data;
};

export const getDeliveryRiderOptions = async (deliveryId, riskLevel = null) => {
  const params = riskLevel ? { risk_level: riskLevel } : {};
  const res = await API.get(`/admin/deliveries/${deliveryId}/rider-options`, { params });
  return res.data;
};

export const assignDeliveryRider = async (deliveryId, riderId = null, riskLevel = null) => {
  const params = {};
  if (riderId !== null && riderId !== undefined) params.rider_id = riderId;
  if (riskLevel) params.risk_level = riskLevel;

  const res = await API.post(`/admin/deliveries/${deliveryId}/assign`, null, { params });
  return res.data;
};

export const startDelivery = async (deliveryId) => {
  const res = await API.post(`/admin/deliveries/${deliveryId}/start`);
  return res.data;
};

export const markOutForDelivery = async (deliveryId) => {
  const res = await API.post(`/admin/deliveries/${deliveryId}/out-for-delivery`);
  return res.data;
};

export const completeDelivery = async (deliveryId, actualDuration = null) => {
  const params = actualDuration ? { actual_duration: actualDuration } : {};
  const res = await API.post(`/admin/deliveries/${deliveryId}/complete`, null, { params });
  return res.data;
};

export const failDelivery = async (deliveryId, failureReason, unreachable = false) => {
  const params = {
    failure_reason: failureReason,
    unreachable: unreachable,
  };
  const res = await API.post(`/admin/deliveries/${deliveryId}/fail`, null, { params });
  return res.data;
};

export const reassignDelivery = async (deliveryId) => {
  const res = await API.post(`/admin/deliveries/${deliveryId}/reassign`);
  return res.data;
};

export const cancelDelivery = async (deliveryId, reason = "Cancelled by operations") => {
  const params = { reason };
  const res = await API.post(`/admin/deliveries/${deliveryId}/cancel`, null, { params });
  return res.data;
};

export const getAdminProfile = async () => {
  const res = await API.get("/admin/profile");
  return res.data;
};

export const changeAdminPassword = async (currentPassword, newPassword) => {
  const res = await API.post("/admin/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return res.data;
};

/* ============================================================
   RIDERS & CUSTOMERS
============================================================ */

export const getRiders = async () => {
  const res = await API.get("/admin/riders");
  return res.data;
};

export const getRiderDetail = async (riderId) => {
  const res = await API.get(`/admin/riders/${riderId}`);
  return res.data;
};

export const getAdminCustomers = async (params = {}) => {
  const res = await API.get("/admin/customers", { params });
  return res.data;
};

export const getAdminCustomerDetail = async (customerId) => {
  const res = await API.get(`/admin/customers/${customerId}`);
  return res.data;
};

export const updateAdminCustomerStatus = async (customerId, isVerified) => {
  const res = await API.patch(`/admin/customers/${customerId}/status`, {
    is_verified: isVerified,
  });
  return res.data;
};

/* ============================================================
   RIDER OPERATIONS
============================================================ */

export const getRiderProfile = async () => {
  const res = await API.get("/rider/profile");
  return res.data;
};

export const getRiderDeliveries = async (params = {}) => {
  const res = await API.get("/rider/deliveries", { params });
  return res.data;
};

export const getRiderDelivery = async (deliveryId) => {
  const res = await API.get(`/rider/deliveries/${deliveryId}`);
  return res.data;
};

export const riderPickupDelivery = async (deliveryId) => {
  const res = await API.post(`/rider/deliveries/${deliveryId}/pickup`);
  return res.data;
};

export const riderStartDelivery = async (deliveryId) => {
  const res = await API.post(`/rider/deliveries/${deliveryId}/start`);
  return res.data;
};

export const riderCompleteDelivery = async (deliveryId, actualDuration = null) => {
  const params = actualDuration ? { actual_duration: actualDuration } : {};
  const res = await API.post(`/rider/deliveries/${deliveryId}/complete`, null, { params });
  return res.data;
};

export const riderFailDelivery = async (deliveryId, reasonCode, notes = null) => {
  const res = await API.post(`/rider/deliveries/${deliveryId}/fail`, {
    reason_code: reasonCode,
    notes: notes,
  });
  return res.data;
};

export const getFailureReasons = async () => {
  const res = await API.get("/rider/failure-reasons");
  return res.data;
};

/* ============================================================
   ML PREDICTION & EXPLANATIONS
============================================================ */

export const predict = async (data) => {
  const res = await API.post("/predict", data);
  return res.data;
};

export const predictExplain = async (data) => {
  const res = await API.post("/predict/explain", data);
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

export const getRouteDetails = async (phoneNumber) => {
  const res = await API.get(`/route/${encodeURIComponent(phoneNumber)}`);
  return res.data;
};

export const getErrorMessage = (err, fallback = "An error occurred") => {
  if (!err) return fallback;
  if (typeof err === "string") return err;

  const detail = err.response?.data?.detail;
  if (!detail) {
    return err.response?.data?.message || err.message || fallback;
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        if (typeof d === "string") return d;
        const msg = d.msg || d.message || JSON.stringify(d);
        return msg.replace(/^Value error,\s*/i, "");
      })
      .filter(Boolean)
      .join(". ");
  }

  if (typeof detail === "object") {
    return detail.msg || detail.message || JSON.stringify(detail);
  }

  return fallback;
};

export default API;
