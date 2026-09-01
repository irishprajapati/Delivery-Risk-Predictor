import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Profile = () => {
  const { isAdmin, isCustomer, isRider } = useAuth();

  if (isAdmin) {
    return <Navigate to="/admin/profile" replace />;
  }

  if (isCustomer) {
    return <Navigate to="/customer/profile" replace />;
  }

  if (isRider) {
    return <Navigate to="/rider/profile" replace />;
  }

  return <Navigate to="/login" replace />;
};

export default Profile;
