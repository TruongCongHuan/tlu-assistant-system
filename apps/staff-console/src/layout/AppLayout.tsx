import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Megaphone,
  FileText,
  MessageSquareText,
  MessageCircle,
  Database,
  ScrollText,
  Settings,
  Users,
} from "lucide-react";
import { useStaffAuth } from "@/context/StaffKeyContext";
import { canAccessPath, roleLabelVi } from "@/lib/staffRole";

const nav = [
  { to: "/", end: true, label: "Tổng quan", icon: LayoutDashboard },
  { to: "/students", label: "Sinh viên & hồ sơ", icon: Users },
  { to: "/chat", label: "Chat phòng ban", icon: MessageCircle },
  { to: "/notifications", label: "Thông báo trường", icon: Megaphone },
  { to: "/submissions", label: "Đơn từ sinh viên", icon: FileText },
  { to: "/feedback", label: "Góp ý / thư SV", icon: MessageSquareText },
  { to: "/vectors", label: "Vector & tài liệu RAG", icon: Database },
  { to: "/audit", label: "Nhật ký thao tác", icon: ScrollText },
  { to: "/settings", label: "Cài đặt", icon: Settings },
];

export function AppLayout() {
  const { staffProfile } = useStaffAuth();

  const visibleNav = nav.filter((item) =>
    canAccessPath(staffProfile?.role, item.to, staffProfile?.isSuper),
  );

  return (
    <div className="flex min-h-screen bg-white">
      <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-slate-50/80">
        <div className="border-b border-slate-200 px-5 py-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            Đại học Thăng Long
          </div>
          <h1 className="mt-1 text-lg font-bold text-slate-900">TLU — Cán bộ</h1>
          <p className="mt-0.5 text-xs text-slate-500">Một cổng quản trị (Firebase + RAG)</p>
        </div>
        <nav className="flex-1 space-y-0.5 p-3">
          {visibleNav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-white text-brand-700 shadow-sm ring-1 ring-slate-200/80"
                    : "text-slate-600 hover:bg-white/80 hover:text-slate-900",
                ].join(" ")
              }
            >
              <Icon className="h-4 w-4 shrink-0 opacity-80" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-200 p-4 text-xs text-slate-500">
          {staffProfile ? (
            <div className="space-y-1 text-slate-800">
              <div className="font-semibold text-slate-900">
                {staffProfile.fullName || staffProfile.email}
              </div>
              <div className="text-brand-700">{roleLabelVi(staffProfile.role, staffProfile.isSuper)}</div>
              <div className="text-slate-600">
                {staffProfile.departmentName || staffProfile.departmentId || "—"}
              </div>
            </div>
          ) : (
            <span>Đã đăng nhập</span>
          )}
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-auto">
        <div className="mx-auto max-w-6xl px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
