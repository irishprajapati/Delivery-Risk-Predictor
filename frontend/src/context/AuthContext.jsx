import { createContext, useContext, useState, useEffect } from "react";
import { getCustomerProfile } from "../services/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [role, setRole] = useState(() => localStorage.getItem("role") || "customer");
  const [phone, setPhone] = useState(() => localStorage.getItem("phone") || "");
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem("token");
      const storedRole = localStorage.getItem("role");
      const storedPhone = localStorage.getItem("phone");

      if (storedToken) {
        setToken(storedToken);
        setRole(storedRole || "customer");
        setPhone(storedPhone || "");

        if (storedRole === "customer") {
          try {
            const profile = await getCustomerProfile();
            setUser(profile);
            if (profile.phone) {
              setPhone(profile.phone);
              localStorage.setItem("phone", profile.phone);
            }
          } catch (e) {
            console.warn("Could not fetch customer profile on init:", e);
          }
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const loginUser = (tokenVal, roleVal, phoneVal = "") => {
    localStorage.setItem("token", tokenVal);
    localStorage.setItem("role", roleVal);
    if (phoneVal) {
      localStorage.setItem("phone", phoneVal);
    }
    setToken(tokenVal);
    setRole(roleVal);
    setPhone(phoneVal);
  };

  const logoutUser = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("phone");
    setToken(null);
    setRole("customer");
    setPhone("");
    setUser(null);
  };

  const switchRole = (newRole) => {
    localStorage.setItem("role", newRole);
    setRole(newRole);
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        role,
        phone,
        user,
        loading,
        isAdmin: role === "admin",
        isCustomer: role === "customer",
        login: loginUser,
        logout: logoutUser,
        switchRole,
        setUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export default AuthContext;
