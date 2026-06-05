import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useStaffAuth, type StaffProfile } from "@/context/StaffKeyContext";
import { LogIn } from "lucide-react";
import { apiUrl } from "@/lib/apiUrl";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { accessToken, persistStaffSession } = useStaffAuth();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const from = (location.state as { from?: string } | null)?.from || "/";

  useEffect(() => {
    if (accessToken.trim()) navigate(from, { replace: true });
  }, [accessToken, from, navigate]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErr(null);
    try {
      const r = await fetch(apiUrl("/api/auth/staff-login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          login: login.trim(),
          password,
        }),
      });
      let j: { error?: string; token?: string; staff?: StaffProfile } = {};
      try {
        j = (await r.json()) as { error?: string; token?: string; staff?: StaffProfile };
      } catch {
        /* body không phải JSON */
      }
      if (!r.ok) {
        throw new Error(j.error || r.statusText || `HTTP ${r.status}`);
      }
      if (!j.token || !j.staff) throw new Error("Phản hồi đăng nhập không hợp lệ");
      persistStaffSession(j.token, j.staff);
      setPassword("");
      navigate(from, { replace: true });
    } catch (e) {
      const msg = String(e);
      if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
        setErr(
          "Không kết nối được API. Mở đúng địa chỉ máy chủ (vd: http://localhost:3000 với Docker), hoặc chạy `npm run dev` trong apps/staff-console.",
        );
      } else {
        setErr(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6 text-center">
          <div className="text-xs font-semibold uppercase tracking-wide text-brand-600">
            Đại học Thăng Long
          </div>
          <p className="mt-3 text-sm font-medium text-slate-700">Dashboard</p>
        </div>

        <form onSubmit={(e) => void onSubmit(e)} className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-600">
              Tài khoản (email hoặc mã đăng nhập)
            </span>
            <input
              type="text"
              autoComplete="username"
              className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none ring-brand-600 focus:ring-2"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              required
              placeholder="vd: super_admin hoặc email@tlu.edu.vn"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-600">Mật khẩu</span>
            <input
              type="password"
              autoComplete="current-password"
              className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none ring-brand-600 focus:ring-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {err && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">{err}</div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-medium text-white shadow hover:bg-brand-700 disabled:opacity-50"
          >
            <LogIn className="h-4 w-4" />
            {loading ? "Đang đăng nhập…" : "Đăng nhập"}
          </button>
        </form>
      </div>
    </div>
  );
}
