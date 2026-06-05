import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useStaffAuth } from "@/context/StaffKeyContext";
import { staffFetch } from "@/lib/api";
import { LogOut, UserCog, Activity } from "lucide-react";
import { StaffAccountsSection } from "@/components/StaffAccountsSection";
import { canManageStaffAccounts } from "@/lib/staffRole";

export function SettingsPage() {
  const navigate = useNavigate();
  const { accessToken, clearStaffSession, staffProfile } = useStaffAuth();
  const [msg, setMsg] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  async function testConnection() {
    setTesting(true);
    setMsg(null);
    try {
      const r = await staffFetch(accessToken, "/api/health");
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || r.statusText);
      const storage = typeof j.storage === "string" ? j.storage : j.firebase ? "firebase" : "file";
      setMsg(
        `Kết nối OK. Storage: ${storage}. Firebase Admin: ${j.firebase ? "có" : "không"}. RAG: ${j.rag ? "OK" : "lỗi"}.`,
      );
    } catch (e) {
      setMsg(`Lỗi: ${String(e)}`);
    } finally {
      setTesting(false);
    }
  }

  const canStaffCrud = canManageStaffAccounts(staffProfile?.role, staffProfile?.isSuper);

  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Cài đặt</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">
          Phiên đăng nhập dùng JWT từ máy chủ. Quản lý tài khoản cán bộ chỉ dành cho{" "}
          <strong>quản trị hệ thống</strong>.
        </p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-800">
          <Activity className="h-4 w-4 text-brand-600" />
          Phiên hiện tại
        </div>
        {staffProfile ? (
          <div className="space-y-3 text-sm text-slate-700">
            <p>
              <strong>{staffProfile.fullName || staffProfile.email}</strong>
            </p>
            <p className="text-xs text-slate-500">
              Email: {staffProfile.email}
              {staffProfile.loginId ? (
                <>
                  {" "}
                  · Đăng nhập ngắn: <code className="rounded bg-slate-100 px-1">{staffProfile.loginId}</code>
                </>
              ) : null}
            </p>
            <button
              type="button"
              onClick={() => {
                clearStaffSession();
                navigate("/login", { replace: true });
              }}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <LogOut className="h-4 w-4" />
              Đăng xuất
            </button>
          </div>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
          <button
            type="button"
            onClick={() => void testConnection()}
            disabled={testing}
            className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
          >
            {testing ? "Đang kiểm tra…" : "Kiểm tra kết nối (Firebase + RAG)"}
          </button>
        </div>
      </section>

      {canStaffCrud && (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-800">
            <UserCog className="h-4 w-4 text-brand-600" />
            Quản lý tài khoản cán bộ
          </div>
          <p className="mb-4 text-xs text-slate-500">
            Tạo tài khoản theo phòng ban và vai trò: <strong>Cán bộ</strong> (thao tác theo phòng),{" "}
            <strong>Giám sát</strong> (xem nhật ký, hạn chế thao tác), <strong>Quản trị</strong> (toàn
            quyền).
          </p>
          <StaffAccountsSection />
        </section>
      )}

      {msg && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800">
          {msg}
        </div>
      )}

      <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-5 text-xs leading-relaxed text-slate-600">
        <p className="font-semibold text-slate-800">Triển khai</p>
        <ul className="mt-2 list-inside list-disc space-y-1">
          <li>
            Đặt <code>STAFF_JWT_SECRET</code> (khuyến nghị) — ký JWT; nếu không có sẽ fallback theo cấu
            hình server.
          </li>
          <li>
            Lần đầu chạy với Firestore trống, hệ thống tạo tài khoản{" "}
            <code className="rounded bg-slate-100 px-1">super_admin</code> /{" "}
            <code className="rounded bg-slate-100 px-1">123456</code> — đổi mật khẩu sau khi vào production.
          </li>
        </ul>
      </div>
    </div>
  );
}
