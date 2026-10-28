import React, { createContext, useContext, useEffect, useState } from "react";
import { API } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("user") || "null");
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(!!user);

  useEffect(() => {
    if (!user) return;
    API.get("/api/auth/me")
      .then((r) => {
        setUser(r.data);
        localStorage.setItem("user", JSON.stringify(r.data));
      })
      .finally(() => setLoading(false));
  }, []);

  async function login(username, password) {
    const r = await API.post("/api/auth/login", { username, password });
    localStorage.setItem("token", r.data.access_token);
    localStorage.setItem("user", JSON.stringify(r.data.user));
    setUser(r.data.user);
    return r.data.user;
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
    window.location.href = "/login";
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}