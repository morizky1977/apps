import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { House, ListChecks, ChartBar, SignOut } from "@phosphor-icons/react";

const NAV = [
  { to: "/dasbor", label: "Dasbor", icon: House, testid: "nav-dasbor" },
  { to: "/tugas", label: "Daftar Tugas", icon: ListChecks, testid: "nav-tugas" },
  { to: "/evaluasi", label: "Evaluasi Mingguan", icon: ChartBar, testid: "nav-evaluasi" },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex bg-[#F9F9F8]">
      {/* Sidebar */}
      <aside className="hidden md:flex w-[260px] shrink-0 flex-col border-r border-zinc-200 bg-white">
        <div className="px-6 py-8 border-b border-zinc-200">
          <div className="overline mb-2">Kerja Rutin</div>
          <h1 className="font-display text-2xl font-black tracking-tighter leading-none">
            RITME<span className="text-[#002FA7]">.</span>
          </h1>
          <p className="mt-2 text-xs text-zinc-500">Pencatat & Evaluasi Kerja Mingguan</p>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              data-testid={item.testid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 text-sm font-medium border-l-2 transition-colors duration-150 ${
                  isActive
                    ? "border-[#002FA7] bg-zinc-50 text-zinc-900"
                    : "border-transparent text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
                }`
              }
            >
              <item.icon size={18} weight="duotone" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-zinc-200">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-10 h-10 rounded-full bg-[#0A0A0A] text-white grid place-items-center font-display font-bold">
              {user?.name?.[0]?.toUpperCase() || "?"}
            </div>
            <div className="min-w-0">
              <div className="text-sm font-semibold truncate" data-testid="sidebar-user-name">{user?.name}</div>
              <div className="text-xs text-zinc-500 truncate">{user?.email}</div>
            </div>
          </div>
          <button
            data-testid="logout-btn"
            onClick={() => { logout(); navigate("/masuk"); }}
            className="mt-3 w-full inline-flex items-center gap-2 justify-center px-3 py-2 text-xs font-semibold uppercase tracking-[0.15em] border border-zinc-900 text-zinc-900 hover:bg-zinc-900 hover:text-white transition-colors"
          >
            <SignOut size={14} weight="bold" /> Keluar
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 inset-x-0 z-40 bg-white border-b border-zinc-200 px-4 py-3 flex items-center justify-between">
        <h1 className="font-display text-lg font-black tracking-tighter">RITME<span className="text-[#002FA7]">.</span></h1>
        <button data-testid="logout-btn-mobile" onClick={() => { logout(); navigate("/masuk"); }} className="text-xs font-semibold">Keluar</button>
      </div>

      <main className="flex-1 min-w-0 pt-14 md:pt-0">
        <Outlet />
        {/* Mobile bottom nav */}
        <nav className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-zinc-200 grid grid-cols-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              data-testid={`${item.testid}-mobile`}
              className={({ isActive }) => `flex flex-col items-center gap-1 py-2 text-[11px] ${isActive ? "text-[#002FA7]" : "text-zinc-500"}`}
            >
              <item.icon size={20} weight="duotone" />
              {item.label.split(" ")[0]}
            </NavLink>
          ))}
        </nav>
      </main>
    </div>
  );
}
