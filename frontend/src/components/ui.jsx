import React from "react";
import { X } from "lucide-react";

export function Badge({ status }) {
  const map = {
    WAITING: "bg-amber-100 text-amber-700 border-amber-200",
    CALLED: "bg-sky-100 text-sky-700 border-sky-200",
    SERVING: "bg-emerald-100 text-emerald-700 border-emerald-200",
    COMPLETED: "bg-slate-200 text-slate-700 border-slate-300",
    HOLD: "bg-rose-100 text-rose-700 border-rose-200",
    SKIPPED: "bg-orange-100 text-orange-700 border-orange-200",
    CANCELLED: "bg-zinc-200 text-zinc-600 border-zinc-300",
    ACTIVE: "bg-indigo-100 text-indigo-700 border-indigo-200",
    PENDING: "bg-amber-100 text-amber-700 border-amber-200",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
        map[status] || "bg-slate-100 text-slate-600 border-slate-200"
      }`}
    >
      {status}
    </span>
  );
}

export function StatCard({ label, value, icon: Icon, accent }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {label}
          </p>
          <p className={`mt-1 text-2xl font-bold ${accent || "text-slate-800"}`}>
            {value}
          </p>
        </div>
        {Icon && (
          <div className="rounded-lg bg-slate-100 p-2 text-slate-500">
            <Icon size={20} />
          </div>
        )}
      </div>
    </div>
  );
}

export function Modal({ open, onClose, title, children, wide }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div
        className={`w-full ${wide ? "max-w-3xl" : "max-w-lg"} max-h-[90vh] overflow-auto rounded-xl bg-white shadow-2xl`}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h3 className="text-base font-semibold text-slate-800">{title}</h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X size={18} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export function Spinner({ label = "Loading…" }) {
  return (
    <div className="flex items-center justify-center gap-2 p-6 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600" />
      {label}
    </div>
  );
}

export function Label({ children }) {
  return (
    <label className="mb-1 block text-xs font-medium text-slate-600">
      {children}
    </label>
  );
}

export const inputCls =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100";

export function Btn({ variant = "primary", className = "", ...props }) {
  const styles = {
    primary:
      "bg-indigo-600 text-white hover:bg-indigo-700",
    secondary:
      "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50",
    danger:
      "bg-rose-600 text-white hover:bg-rose-700",
    success:
      "bg-emerald-600 text-white hover:bg-emerald-700",
    ghost:
      "text-slate-600 hover:bg-slate-100",
  };
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition ${styles[variant]} ${className}`}
      {...props}
    />
  );
}