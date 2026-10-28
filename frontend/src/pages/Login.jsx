import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GraduationCap } from "lucide-react";
import { useAuth } from "../lib/auth.jsx";
import { Btn, inputCls } from "../components/ui.jsx";

const DEMO_ACCOUNTS = [
  { role: "Admin", user: "admin", pass: "admin123" },
  { role: "Receptionist", user: "reception", pass: "reception123" },
  { role: "Counsellor", user: "priya", pass: "staff123" },
];

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = await login(username, password);
      nav(user.role === "ADMIN" ? "/admin" : user.role === "RECEPTIONIST" ? "/reception" : "/staff");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-indigo-600 via-indigo-700 to-slate-900 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-xl bg-indigo-600 p-2.5 text-white">
            <GraduationCap size={26} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Nandha Engineering College</h1>
            <p className="text-xs text-slate-500">
              Admission Assistance & Visitor Queue System
            </p>
          </div>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">
              Username
            </label>
            <input
              className={inputCls}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. reception"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">
              Password
            </label>
            <input
              type="password"
              className={inputCls}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          {error && (
            <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">
              {error}
            </p>
          )}
          <Btn className="w-full" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Btn>
        </form>

        <div className="mt-6">
          <p className="mb-2 text-center text-xs font-medium uppercase tracking-wide text-slate-400">
            Demo accounts
          </p>
          <div className="grid grid-cols-3 gap-2">
            {DEMO_ACCOUNTS.map((a) => (
              <button
                key={a.role}
                onClick={() => {
                  setUsername(a.user);
                  setPassword(a.pass);
                }}
                className="rounded-lg border border-slate-200 p-2 text-left hover:border-indigo-400 hover:bg-indigo-50"
              >
                <p className="text-xs font-semibold text-slate-700">{a.role}</p>
                <p className="text-[10px] text-slate-400">
                  {a.user} / {a.pass}
                </p>
              </button>
            ))}
          </div>
        </div>

        <a
          href="/chat"
          className="mt-4 block text-center text-sm font-medium text-indigo-600 hover:underline"
        >
          Continue as Parent / Student →
        </a>
      </div>
    </div>
  );
}