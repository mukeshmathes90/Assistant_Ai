import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // Listen on the LAN so phones can scan the reception QR and open the app.
    host: true,
    port: 5173,
    // Allow the random ngrok-free.dev hostnames (and LAN IPs) in dev.
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});