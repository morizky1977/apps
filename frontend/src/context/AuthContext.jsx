import { createContext, useContext, useEffect, useState } from "react";
import { apiClient } from "@/lib/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("kr_token");
    if (!token) { setLoading(false); return; }
    apiClient.get("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => { localStorage.removeItem("kr_token"); })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const res = await apiClient.post("/auth/login", { email, password });
    localStorage.setItem("kr_token", res.data.token);
    setUser(res.data.user);
    return res.data.user;
  };

  const register = async (name, email, password, security_answer) => {
    const body = { name, email, password };
    if (security_answer && security_answer.trim()) body.security_answer = security_answer;
    const res = await apiClient.post("/auth/register", body);
    localStorage.setItem("kr_token", res.data.token);
    setUser(res.data.user);
    return res.data.user;
  };

  const refreshUser = async () => {
    const res = await apiClient.get("/auth/me");
    setUser(res.data);
    return res.data;
  };

  const logout = () => {
    localStorage.removeItem("kr_token");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
