import { Routes, Route, Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Navbar from "./components/Navbar";

// Auth Pages
import Login from "./pages/Login";
import Register from "./pages/Register";
import VerifyOTP from "./pages/VerifyOTP";

// Customer Pages
import CustomerDashboard from "./pages/customer/CustomerDashboard";
import PlaceOrder from "./pages/customer/PlaceOrder";
import CustomerOrderDetail from "./pages/customer/CustomerOrderDetail";
import CustomerProfile from "./pages/customer/CustomerProfile";

// Rider Pages
import RiderDashboard from "./pages/rider/RiderDashboard";
import RiderDeliveryDetail from "./pages/rider/RiderDeliveryDetail";

// Admin Pages
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminDeliveries from "./pages/admin/AdminDeliveries";
import AdminPrediction from "./pages/admin/AdminPrediction";
import AdminDispatch from "./pages/admin/AdminDispatch";
import AdminDeliveryLifecycle from "./pages/admin/AdminDeliveryLifecycle";
import AdminRiders from "./pages/admin/AdminRiders";
import AdminRiderDetail from "./pages/admin/AdminRiderDetail";
import AdminCustomers from "./pages/admin/AdminCustomers";
import AdminCustomerDetail from "./pages/admin/AdminCustomerDetail";
import AdminProfile from "./pages/admin/AdminProfile";
import AdminPredictionsHistory from "./pages/admin/AdminPredictionsHistory";
import RouteDetails from "./pages/RouteDetails";
import Profile from "./pages/Profile";

function ProtectedRoute() {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <p style={{ color: "#64748b", fontSize: "0.95rem" }}>Loading session...</p>
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

function CustomerRoute() {
  const { isCustomer, loading } = useAuth();

  if (loading) return null;

  if (!isCustomer) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

function RiderRoute() {
  const { isRider, loading } = useAuth();

  if (loading) return null;

  if (!isRider) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

function AdminRoute() {
  const { isAdmin, loading } = useAuth();

  if (loading) return null;

  if (!isAdmin) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

function RoleRootRedirect() {
  const { isAdmin, isCustomer, isRider, token } = useAuth();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (isAdmin) {
    return <Navigate to="/admin/dashboard" replace />;
  }

  if (isRider) {
    return <Navigate to="/rider/dashboard" replace />;
  }

  if (isCustomer) {
    return <Navigate to="/customer/dashboard" replace />;
  }

  return <Navigate to="/login" replace />;
}

function AppLayout() {
  return (
    <>
      <Navbar />
      <main style={{ padding: "24px 20px", maxWidth: "1240px", margin: "0 auto", width: "100%" }}>
        <Outlet />
      </main>
    </>
  );
}

function App() {
  return (
    <Routes>
      {/* Public Auth Routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify-otp" element={<VerifyOTP />} />

      {/* Protected Routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<RoleRootRedirect />} />

          {/* Common Role Delegated Profile */}
          <Route path="/profile" element={<Profile />} />

          {/* Customer Only Portal */}
          <Route element={<CustomerRoute />}>
            <Route path="/customer/dashboard" element={<CustomerDashboard />} />
            <Route path="/customer/orders" element={<CustomerDashboard />} />
            <Route path="/customer/order" element={<PlaceOrder />} />
            <Route path="/customer/orders/:id" element={<CustomerOrderDetail />} />
            <Route path="/customer/profile" element={<CustomerProfile />} />
          </Route>

          {/* Rider Only Portal */}
          <Route element={<RiderRoute />}>
            <Route path="/rider/dashboard" element={<RiderDashboard />} />
            <Route path="/rider/deliveries" element={<RiderDashboard />} />
            <Route path="/rider/deliveries/:id" element={<RiderDeliveryDetail />} />
            <Route path="/rider/profile" element={<RiderDashboard />} />
          </Route>

          {/* Admin Only Portal */}
          <Route element={<AdminRoute />}>
            <Route path="/admin/dashboard" element={<AdminDashboard />} />
            <Route path="/admin/profile" element={<AdminProfile />} />
            <Route path="/admin/customers" element={<AdminCustomers />} />
            <Route path="/admin/customers/:id" element={<AdminCustomerDetail />} />
            <Route path="/admin/deliveries" element={<AdminDeliveries />} />
            <Route path="/admin/deliveries/:id" element={<AdminDeliveryLifecycle />} />
            <Route path="/admin/prediction" element={<AdminPrediction />} />
            <Route path="/admin/dispatch" element={<AdminDispatch />} />
            <Route path="/admin/riders" element={<AdminRiders />} />
            <Route path="/admin/riders/:id" element={<AdminRiderDetail />} />
            <Route path="/admin/predictions" element={<AdminPredictionsHistory />} />
            <Route path="/route/prediction/:prediction_id" element={<RouteDetails />} />
            <Route path="/route/:phone_number" element={<RouteDetails />} />

            {/* Legacy Aliases for admin */}
            <Route path="/history" element={<AdminPredictionsHistory />} />
            <Route path="/predict" element={<AdminPrediction />} />
          </Route>
        </Route>
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
