export type StaffRole = "super_admin" | "staff" | "auditor";

export function normalizeRole(
  r: string | undefined | null,
  isSuper?: boolean,
): StaffRole {
  if (r === "super_admin" || r === "staff" || r === "auditor") return r;
  if (isSuper) return "super_admin";
  return "staff";
}

export function roleLabelVi(role: string | undefined | null, isSuper?: boolean): string {
  switch (normalizeRole(role, isSuper)) {
    case "super_admin":
      return "Quản trị hệ thống";
    case "auditor":
      return "Giám sát / kiểm toán";
    default:
      return "Cán bộ";
  }
}

/** Đường dẫn cấp 1 (ví dụ `/chat`, `/`) mà role được phép mở */
export function canAccessPath(
  role: string | undefined | null,
  pathname: string,
  isSuper?: boolean,
): boolean {
  const r = normalizeRole(role, isSuper);
  const seg = pathname.replace(/\/$/, "").split("/").filter(Boolean);
  const base = seg.length === 0 ? "/" : `/${seg[0]}`;
  if (r === "super_admin") return true;
  if (r === "auditor") {
    return ["/", "/students", "/notifications", "/audit", "/settings"].includes(base);
  }
  return ["/", "/students", "/chat", "/notifications", "/submissions", "/feedback", "/vectors", "/settings"].includes(
    base,
  );
}

export function canEditStudentProfiles(
  role: string | undefined | null,
  isSuper?: boolean,
): boolean {
  return normalizeRole(role, isSuper) === "super_admin";
}

export function canManageNotifications(
  role: string | undefined | null,
  isSuper?: boolean,
): boolean {
  return normalizeRole(role, isSuper) === "super_admin";
}

export function canManageStaffAccounts(
  role: string | undefined | null,
  isSuper?: boolean,
): boolean {
  return normalizeRole(role, isSuper) === "super_admin";
}
