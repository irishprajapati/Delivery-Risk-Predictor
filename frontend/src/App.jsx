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

// Admin Pages
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminDeliveries from "./pages/admin/AdminDeliveries";
import AdminPrediction from "./pages/admin/AdminPrediction";
import AdminDispatch from "./pages/admin/AdminDispatch";
import AdminDeliveryLifecycle from "./pages/admin/AdminDeliveryLifecycle";
import AdminRiders from "./pages/admin/AdminRiders";
import AdminRiderDetail from "./pages/admin/AdminRiderDetail";
import AdminPredictionsHistory from "./pages/admin/AdminPredictionsHistory";
import RouteDetails from "./pages/RouteDetails";

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
    return <Navigate to="/admin/dashboard" replace />;
  }

  return <Outlet />;
}

function AdminRoute() {
  const { isAdmin, loading } = useAuth();

  if (loading) return null;

  if (!isAdmin) {
    return <Navigate to="/customer/dashboard" replace />;
  }

  return <Outlet />;
}

function RoleRootRedirect() {
  const { isAdmin, isCustomer, token } = useAuth();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={isAdmin ? "/admin/dashboard" : isCustomer ? "/customer/dashboard" : "/login"} replace />;
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

          {/* Customer Only Portal */}
          <Route element={<CustomerRoute />}>
            <Route path="/customer/dashboard" element={<CustomerDashboard />} />
            <Route path="/customer/orders" element={<CustomerDashboard />} />
            <Route path="/customer/order" element={<PlaceOrder />} />
            <Route path="/customer/orders/:id" element={<CustomerOrderDetail />} />
            <Route path="/customer/profile" element={<CustomerProfile />} />
          </Route>

          {/* Admin Only Portal */}
          <Route element={<AdminRoute />}>
            <Route path="/admin/dashboard" element={<AdminDashboard />} />
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
