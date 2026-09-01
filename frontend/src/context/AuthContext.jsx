import { createContext, useContext, useState, useEffect } from "react";
import { getCustomerProfile } from "../services/api";

const AuthContext = createContext(null);

export const parseJwt = (token) => {
  try {
    if (!token) return null;
    const base64Url = token.split(".")[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
};

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [role, setRole] = useState(() => {
    const storedToken = localStorage.getItem("token");
    const parsed = parseJwt(storedToken);
    return parsed?.role || localStorage.getItem("role") || null;
  });
  const [phone, setPhone] = useState(() => localStorage.getItem("phone") || "");
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem("token");

      if (storedToken) {
        const parsed = parseJwt(storedToken);

        // Check if token is expired
        if (parsed?.exp && parsed.exp * 1000 < Date.now()) {
          logoutUser();
          setLoading(false);
          return;
        }

        const currentRole = parsed?.role || localStorage.getItem("role") || null;
        setToken(storedToken);
        setRole(currentRole);

        if (currentRole === "customer") {
          try {
            const profile = await getCustomerProfile();
            setUser(profile);
            if (profile.phone) {
              setPhone(profile.phone);
              localStorage.setItem("phone", profile.phone);
            }
          } catch (err) {
            console.warn("Could not fetch customer profile on init:", err);
            if (err.response?.status === 401 || err.response?.status === 403) {
              logoutUser();
            }
          }
        }
      } else {
        logoutUser();
      }

      setLoading(false);
    };

    initAuth();
  }, []);

  const loginUser = (tokenVal, roleVal, phoneVal = "") => {
    const parsed = parseJwt(tokenVal);
    const verifiedRole = parsed?.role || roleVal;

    localStorage.setItem("token", tokenVal);
    localStorage.setItem("role", verifiedRole);
    if (phoneVal) {
      localStorage.setItem("phone", phoneVal);
    }

    setToken(tokenVal);
    setRole(verifiedRole);
    setPhone(phoneVal);
  };

  const logoutUser = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("phone");
    setToken(null);
    setRole(null);
    setPhone("");
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        role,
        phone,
        user,
        loading,
        isAuthenticated: Boolean(token && role),
        isAdmin: role === "admin",
        isCustomer: role === "customer",
        isRider: role === "rider",
        login: loginUser,
        logout: logoutUser,
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
