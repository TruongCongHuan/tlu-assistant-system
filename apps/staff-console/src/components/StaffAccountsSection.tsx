import { useCallback, useEffect, useState } from "react";
import { useStaffFetch } from "@/lib/api";
import type { StaffRole } from "@/lib/staffRole";

type Dept = { id: string; name: string; code?: string };
type Account = {
  id: string;
  email: string;
  loginId?: string | null;
  fullName: string;
  staffCode: string;
  departmentId: string;
  departmentName: string;
  role: StaffRole;
  isSuper?: boolean;
  active: boolean;
};

const ALL_DEPT: Dept = { id: "all", name: "Toàn trường" };

function accountRole(a: Account): StaffRole {
  if (a.role === "super_admin" || a.role === "staff" || a.role === "auditor") return a.role;
  if (a.isSuper) return "super_admin";
  return "staff";
}

const emptyForm = {
  email: "",
  loginId: "",
  password: "",
  fullName: "",
  staffCode: "",
  departmentId: "",
  role: "staff" as StaffRole,
};

export function StaffAccountsSection() {
  const fetchApi = useStaffFetch();
  const [depts, setDepts] = useState<Dept[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [editing, setEditing] = useState<Account | null>(null);
  const [form, setForm] = useState(emptyForm);

  const deptOptions =
    form.role === "super_admin" ? [...depts, ALL_DEPT] : depts;

  const load = useCallback(async () => {
    setErr(null);
    try {
      const [rd, ra] = await Promise.all([
        fetchApi("/api/departments"),
        fetchApi("/api/staff/accounts"),
      ]);
      const jd = await rd.json();
      const ja = await ra.json();
      if (!rd.ok) throw new Error(jd.error || rd.statusText);
      if (!ra.ok) throw new Error(ja.error || ra.statusText);
      setDepts(jd.items || []);
      setAccounts(ja.items || []);
    } catch (e) {
      setErr(String(e));
    }
  }, [fetchApi]);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
  }

  function openEdit(a: Account) {
    setEditing(a);
    const r = accountRole(a);
    setForm({
      email: a.email,
      loginId: a.loginId || "",
      password: "",
      fullName: a.fullName,
      staffCode: a.staffCode,
      departmentId: a.departmentId,
      role: r,
    });
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      if (editing) {
        const body: Record<string, unknown> = {
          fullName: form.fullName,
          staffCode: form.staffCode,
          departmentId: form.departmentId,
          role: form.role,
        };
        if (form.password.trim()) body.password = form.password;
        if (form.loginId.trim()) body.loginId = form.loginId.trim();
        else body.loginId = null;
        const r = await fetchApi(`/api/staff/accounts/${encodeURIComponent(editing.id)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || r.statusText);
      } else {
        if (!form.email.trim() || !form.password) {
          setErr("Email và mật khẩu bắt buộc khi tạo mới.");
          return;
        }
        if (!form.departmentId) {
          setErr("Chọn phòng ban (hoặc Toàn trường nếu quản trị).");
          return;
        }
        const r = await fetchApi("/api/staff/accounts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: form.email.trim(),
            loginId: form.loginId.trim() || undefined,
            password: form.password,
            fullName: form.fullName,
            staffCode: form.staffCode,
            departmentId: form.departmentId,
            role: form.role,
          }),
        });
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || r.statusText);
      }
      setEditing(null);
      setForm(emptyForm);
      await load();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onDisable(id: string) {
    if (!confirm("Vô hiệu hoá tài khoản này?")) return;
    try {
      const r = await fetchApi(`/api/staff/accounts/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || r.statusText);
      await load();
    } catch (e) {
      setErr(String(e));
    }
  }

  function roleLabel(r: StaffRole) {
    if (r === "super_admin") return "Quản trị";
    if (r === "auditor") return "Giám sát";
    return "Cán bộ";
  }

  return (
    <div className="space-y-6">
      {err && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          {err}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={openCreate}
          className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          + Tài khoản mới
        </button>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
        >
          Làm mới
        </button>
      </div>

      <form
        onSubmit={onSubmit}
        className="grid gap-3 rounded-lg border border-slate-100 bg-slate-50/80 p-4 sm:grid-cols-2"
      >
        <h3 className="sm:col-span-2 text-sm font-semibold text-slate-800">
          {editing ? `Sửa tài khoản — ${editing.email}` : "Tạo tài khoản"}
        </h3>
        {!editing && (
          <>
            <label className="sm:col-span-2 block text-xs">
              <span className="text-slate-600">Email đăng nhập</span>
              <input
                className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                required={!editing}
                disabled={Boolean(editing)}
              />
            </label>
            <label className="sm:col-span-2 block text-xs">
              <span className="text-slate-600">
                Mã đăng nhập ngắn (tuỳ chọn, ví dụ <code>super_admin</code>)
              </span>
              <input
                className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                value={form.loginId}
                onChange={(e) => setForm((f) => ({ ...f, loginId: e.target.value }))}
                placeholder="Để trống nếu chỉ dùng email"
              />
            </label>
            <label className="sm:col-span-2 block text-xs">
              <span className="text-slate-600">Mật khẩu {editing && "(để trống nếu giữ nguyên)"}</span>
              <input
                className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
                type="password"
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                required={!editing}
              />
            </label>
          </>
        )}
        <label className="block text-xs sm:col-span-2">
          <span className="text-slate-600">Họ tên</span>
          <input
            className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
            value={form.fullName}
            onChange={(e) => setForm((f) => ({ ...f, fullName: e.target.value }))}
          />
        </label>
        <label className="block text-xs">
          <span className="text-slate-600">Mã cán bộ</span>
          <input
            className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
            value={form.staffCode}
            onChange={(e) => setForm((f) => ({ ...f, staffCode: e.target.value }))}
          />
        </label>
        <label className="block text-xs">
          <span className="text-slate-600">Vai trò</span>
          <select
            className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
            value={form.role}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                role: e.target.value as StaffRole,
                departmentId:
                  e.target.value === "super_admin" && f.departmentId && f.departmentId !== "all"
                    ? f.departmentId
                    : e.target.value === "super_admin" && !f.departmentId
                      ? "all"
                      : e.target.value !== "super_admin" && f.departmentId === "all"
                        ? ""
                        : f.departmentId,
              }))
            }
          >
            <option value="staff">Cán bộ (theo phòng)</option>
            <option value="auditor">Giám sát (xem nhật ký, hạn chế)</option>
            <option value="super_admin">Quản trị hệ thống</option>
          </select>
        </label>
        <label className="block text-xs sm:col-span-2">
          <span className="text-slate-600">Phòng ban</span>
          <select
            className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
            value={form.departmentId}
            onChange={(e) => setForm((f) => ({ ...f, departmentId: e.target.value }))}
            required
          >
            <option value="">— Chọn —</option>
            {deptOptions.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        {editing && (
          <label className="block text-xs sm:col-span-2">
            <span className="text-slate-600">Mã đăng nhập ngắn</span>
            <input
              className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
              value={form.loginId}
              onChange={(e) => setForm((f) => ({ ...f, loginId: e.target.value }))}
              placeholder="Để trống để xóa mã ngắn"
            />
          </label>
        )}
        {editing && (
          <label className="block text-xs sm:col-span-2">
            <span className="text-slate-600">Mật khẩu mới (tuỳ chọn)</span>
            <input
              className="mt-1 w-full rounded border border-slate-200 px-2 py-1.5 text-sm"
              type="password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            />
          </label>
        )}
        <div className="flex gap-2 sm:col-span-2">
          <button
            type="submit"
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white"
          >
            {editing ? "Cập nhật" : "Tạo"}
          </button>
          {editing && (
            <button
              type="button"
              onClick={() => {
                setEditing(null);
                setForm(emptyForm);
              }}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              Hủy sửa
            </button>
          )}
        </div>
      </form>

      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b bg-slate-50 text-xs uppercase text-slate-600">
            <tr>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Mã đăng nhập</th>
              <th className="px-3 py-2">Họ tên</th>
              <th className="px-3 py-2">Mã</th>
              <th className="px-3 py-2">Phòng</th>
              <th className="px-3 py-2">Vai trò</th>
              <th className="px-3 py-2">Active</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id} className="border-b border-slate-100 hover:bg-slate-50/80">
                <td className="px-3 py-2">{a.email}</td>
                <td className="px-3 py-2 font-mono text-xs">{a.loginId || "—"}</td>
                <td className="px-3 py-2">{a.fullName}</td>
                <td className="px-3 py-2">{a.staffCode}</td>
                <td className="px-3 py-2 text-xs">{a.departmentName || a.departmentId}</td>
                <td className="px-3 py-2">{roleLabel(accountRole(a))}</td>
                <td className="px-3 py-2">{a.active ? "Có" : "Không"}</td>
                <td className="space-x-1 px-3 py-2 text-right">
                  <button
                    type="button"
                    className="text-brand-700 hover:underline"
                    onClick={() => openEdit(a)}
                  >
                    Sửa
                  </button>
                  {a.active && (
                    <button
                      type="button"
                      className="text-rose-700 hover:underline"
                      onClick={() => void onDisable(a.id)}
                    >
                      Vô hiệu
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
