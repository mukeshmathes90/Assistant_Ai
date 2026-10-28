import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./lib/auth.jsx";
import Login from "./pages/Login.jsx";
import Receptionist from "./pages/Receptionist.jsx";
import Staff from "./pages/Staff.jsx";
import Admin from "./pages/Admin.jsx";
import Chat from "./pages/Chat.jsx";

function Require({ roles, children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10 text-center text-slate-500">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) {
    if (user.role === "ADMIN") return <Navigate to="/admin" replace />;
    return <Navigate to="/login" replace />;
  }
  return children;
}

function Home() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "ADMIN") return <Navigate to="/admin" replace />;
  if (user.role === "RECEPTIONIST") return <Navigate to="/reception" replace />;
  return <Navigate to="/staff" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/chat" element={<Chat />} />
      <Route path="/" element={<Home />} />
      <Route
        path="/reception"
        element={
          <Require roles={["RECEPTIONIST", "ADMIN", "STAFF"]}>
            <Receptionist />
          </Require>
        }
      />
      <Route
        path="/staff"
        element={
          <Require roles={["STAFF", "ADMIN", "RECEPTIONIST"]}>
            <Staff />
          </Require>
        }
      />
      <Route
        path="/admin"
        element={
          <Require roles={["ADMIN"]}>
            <Admin />
          </Require>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}