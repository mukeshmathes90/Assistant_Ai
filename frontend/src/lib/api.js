import axios from "axios";

// Same-origin by default so the Vite dev proxy (and any reverse proxy in
// production) forwards /api to the backend. This also makes the app work when
// opened from a phone via the PC's LAN IP (e.g. after scanning a reception QR).
// Set VITE_API_URL only to call a backend on a different host.
export const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
});

API.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

API.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      if (!window.location.pathname.startsWith("/chat")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);