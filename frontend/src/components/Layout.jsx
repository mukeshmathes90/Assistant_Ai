import React from "react";
import { GraduationCap, LogOut, MessageCircle, Users, LayoutDashboard } from "lucide-react";
import { useAuth } from "../lib/auth.jsx";

const NAV = {
  ADMIN: [
    { label: "Admin Dashboard", to: "/admin", icon: LayoutDashboard },
    { label: "Parent / Visitor Chat", to: "/chat", icon: MessageCircle },
  ],
  RECEPTIONIST: [
    { label: "Reception Desk", to: "/reception", icon: Users },
    { label: "Staff Queues", to: "/staff", icon: LayoutDashboard },
    { label: "Parent / Visitor Chat", to: "/chat", icon: MessageCircle },
  ],
  STAFF: [
    { label: "Staff Queues", to: "/staff", icon: LayoutDashboard },
    { label: "Reception Desk", to: "/reception", icon: Users },
    { label: "Parent / Visitor Chat", to: "/chat", icon: MessageCircle },
  ],
};

export default function Layout({ title, children }) {
  const { user, logout } = useAuth();
  const items = NAV[user?.role] || [];
  return (
    <div className="flex h-full min-h-screen">
      <aside className="hidden w-64 flex-col bg-slate-900 text-slate-200 md:flex">
        <div className="flex items-center gap-2 border-b border-slate-700 px-5 py-4">
          <GraduationCap className="text-indigo-400" size={24} />
          <div>
            <p className="text-sm font-bold text-white">Nandha Engineering College</p>
            <p className="text-[11px] text-slate-400">Admission Desk</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {items.map((i) => (
            <a
              key={i.to}
              href={i.to}
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium hover:bg-slate-800"
            >
              <i.icon size={17} />
              {i.label}
            </a>
          ))}
        </nav>
        <div className="border-t border-slate-700 p-4">
          <p className="text-sm font-medium text-white">{user?.full_name}</p>
          <p className="mb-2 text-xs text-slate-400">
            Role: {user?.role}
          </p>
          <button
            onClick={logout}
            className="flex items-center gap-2 rounded-lg bg-slate-800 px-3 py-1.5 text-sm hover:bg-slate-700"
          >
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-3">
          <div>
            <h1 className="text-lg font-bold text-slate-800">{title}</h1>
            <p className="text-xs text-slate-500">
              AI-Powered Admission Assistance & Visitor Queue Management
            </p>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="/chat"
              className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
            >
              <MessageCircle size={15} /> Visitor Chat
            </a>
            <button
              onClick={logout}
              className="md:hidden rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600"
            >
              Sign out
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-5">{children}</main>
      </div>
    </div>
  );
}