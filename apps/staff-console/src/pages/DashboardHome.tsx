import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useStaffFetch } from "@/lib/api";
import { useStaffAuth } from "@/context/StaffKeyContext";
import { canAccessPath, roleLabelVi } from "@/lib/staffRole";
import {
  Megaphone,
  FileText,
  MessageSquareText,
  MessageCircle,
  Database,
  Activity,
  Users,
} from "lucide-react";

export function DashboardHome() {
  const { staffProfile } = useStaffAuth();
  const fetchApi = useStaffFetch();
  const [health, setHealth] = useState<{
    firebase: boolean;
    rag: boolean;
  } | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const r = await fetchApi("/api/health");
        const j = await r.json();
        if (r.ok) setHealth({ firebase: j.firebase, rag: j.rag });
      } catch {
        setHealth({ firebase: false, rag: false });
      }
    })();
  }, [fetchApi]);

  const allCards = [
    {
      to: "/students",
      title: "Sinh viên & hồ sơ",
      desc: "Danh sách users, MSSV, lớp — đồng bộ từ app khi đăng nhập.",
      icon: Users,
    },
    {
      to: "/chat",
      title: "Chat phòng ban",
      desc: "Tin sinh viên gửi tới phòng của bạn — trả lời từ đây.",
      icon: MessageCircle,
    },
    {
      to: "/notifications",
      title: "Thông báo trường",
      desc: "Đăng tin lên Firestore — sinh viên đọc trên app.",
      icon: Megaphone,
    },
    {
      to: "/submissions",
      title: "Đơn từ",
      desc: "Theo dõi đơn đã gửi kèm file đính kèm.",
      icon: FileText,
    },
    {
      to: "/feedback",
      title: "Góp ý",
      desc: "Thư góp ý / ẩn danh từ sinh viên.",
      icon: MessageSquareText,
    },
    {
      to: "/vectors",
      title: "Vector RAG",
      desc: "Upload, index và xóa tài liệu phục vụ chatbot.",
      icon: Database,
    },
  ];

  const cards = allCards.filter((c) =>
    canAccessPath(staffProfile?.role, c.to, staffProfile?.isSuper),
  );

  return (
    <div className="space-y-8">
      <header>
        <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
          Tổng quan
        </h2>
        {staffProfile ? (
          <p className="mt-1 text-sm text-slate-700">
            <span className="font-medium text-slate-900">
              {staffProfile.fullName || staffProfile.email}
            </span>
            <span className="text-slate-500"> · </span>
            <span className="text-brand-700">{roleLabelVi(staffProfile.role, staffProfile.isSuper)}</span>
          </p>
        ) : null}
        <p className="mt-1 text-sm text-slate-600">
          Bảng điều khiển nội bộ: Firebase (thông báo, đơn, góp ý) và API RAG vector. Các mục hiển thị theo
          quyền của tài khoản.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
        <Activity className="h-4 w-4 text-brand-600" />
        <span className="font-medium text-slate-700">Trạng thái dịch vụ</span>
        {health ? (
          <>
            <StatusPill ok={health.firebase} label="Firebase Admin" />
            <StatusPill ok={health.rag} label="RAG API" />
          </>
        ) : (
          <span className="text-slate-500">Đang kiểm tra…</span>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {cards.map(({ to, title, desc, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className="group rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-200 hover:shadow-md"
          >
            <div className="flex items-start gap-4">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
                <Icon className="h-5 w-5" />
              </span>
              <div>
                <h3 className="font-semibold text-slate-900 group-hover:text-brand-700">
                  {title}
                </h3>
                <p className="mt-1 text-sm text-slate-600">{desc}</p>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={
        ok
          ? "rounded-full bg-emerald-50 px-2.5 py-0.5 text-emerald-800 ring-1 ring-emerald-200"
          : "rounded-full bg-rose-50 px-2.5 py-0.5 text-rose-800 ring-1 ring-rose-200"
      }
    >
      {label}: {ok ? "OK" : "Lỗi / chưa cấu hình"}
    </span>
  );
}
