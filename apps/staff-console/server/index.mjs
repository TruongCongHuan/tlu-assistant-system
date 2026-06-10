/**
 * Staff Console BFF: JWT (Bearer) cho cán bộ; X-Staff-Key tuỳ chọn cho vận hành; Firebase Admin + proxy RAG.
 * Dev: PORT=3001, prod/Docker: PORT=3000 + serve ../dist
 */
import express from "express";
import path from "path";
import { randomUUID } from "crypto";
import { fileURLToPath } from "url";
import multer from "multer";
import { File } from "node:buffer";
import { initializeApp, cert, applicationDefault } from "firebase-admin/app";
import { getFirestore, FieldValue } from "firebase-admin/firestore";
import { getMessaging } from "firebase-admin/messaging";
import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import { createFileStore } from "./file-store.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isProd = process.env.NODE_ENV === "production";
const PORT = Number(process.env.PORT || (isProd ? 3000 : 3001));
const STORAGE_BACKEND = (process.env.STORAGE_BACKEND || "firebase").trim();
const USE_FILE_STORAGE = STORAGE_BACKEND === "file";
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, "../../../data");
const STUDENT_KEY = (process.env.STUDENT_API_KEY || "").trim();
const STAFF_KEY = (process.env.STAFF_API_KEY || "").trim();
const RAG_URL = (process.env.RAG_API_URL || "http://127.0.0.1:8080").replace(
  /\/$/,
  "",
);
const RAG_ADMIN_KEY = (process.env.RAG_ADMIN_KEY || "").trim();
const JWT_SECRET = (process.env.STAFF_JWT_SECRET || STAFF_KEY || "dev-staff-jwt-change").trim();

const DEFAULT_DEPARTMENTS = [
  { id: "co_van", name: "Cố vấn học tập", code: "CVHT" },
  { id: "ct_sv", name: "Phòng Công tác Chính trị Sinh viên", code: "CTSV" },
  { id: "dao_tao", name: "Phòng Đào tạo", code: "DT" },
  { id: "tai_chinh", name: "Phòng Tài chính - Kế toán", code: "TC" },
  { id: "tam_ly", name: "Phòng Tham vấn tâm lý", code: "TVTL" },
];

let firebaseReady = false;
const hasServiceAccountJson = Boolean(process.env.FIREBASE_SERVICE_ACCOUNT_JSON?.trim());
const hasGoogleAppCreds = Boolean(process.env.GOOGLE_APPLICATION_CREDENTIALS?.trim());

/** @type {ReturnType<createFileStore> | null} */
let fileStore = null;
if (USE_FILE_STORAGE) {
  fileStore = createFileStore(DATA_DIR);
  console.log("[staff-console] STORAGE_BACKEND=file at", path.resolve(DATA_DIR));
}

// PRODUCTION_FIREBASE: skip init when demo file storage is active
try {
  if (USE_FILE_STORAGE) {
    firebaseReady = false;
  } else if (hasServiceAccountJson) {
    initializeApp({ credential: cert(JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT_JSON.trim())) });
    firebaseReady = true;
  } else if (hasGoogleAppCreds) {
    initializeApp({ credential: applicationDefault() });
    firebaseReady = true;
  } else if (!isProd) {
    initializeApp({ credential: applicationDefault() });
    firebaseReady = true;
  } else {
    console.warn(
      "[staff-console] Firebase tắt (production): cần FIREBASE_SERVICE_ACCOUNT_JSON hoặc GOOGLE_APPLICATION_CREDENTIALS.",
    );
  }
} catch (e) {
  console.warn("[staff-console] Firebase Admin not initialized:", e.message);
}

const db = firebaseReady ? getFirestore() : null;
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 40 * 1024 * 1024 } });

async function sendFcmSafely(run) {
  if (USE_FILE_STORAGE || !firebaseReady) return;
  try {
    const messaging = getMessaging();
    await run(messaging);
  } catch (e) {
    console.warn("[staff-console] FCM:", e?.message || e);
  }
}

function effectiveRoleFromDoc(data) {
  const r = String(data?.role || "").trim();
  if (r === "super_admin" || r === "staff" || r === "auditor") return r;
  if (data?.isSuper) return "super_admin";
  return "staff";
}

function effectiveRoleFromJwt(staff) {
  if (!staff) return "staff";
  const r = String(staff.role || "").trim();
  if (r === "super_admin" || r === "staff" || r === "auditor") return r;
  if (staff.isSuper) return "super_admin";
  return "staff";
}

function isMaster(req) {
  return Boolean(STAFF_KEY && (req.get("X-Staff-Key") || "").trim() === STAFF_KEY);
}

function isCrossDepartmentStaffPayload(staff) {
  if (!staff) return false;
  if (effectiveRoleFromJwt(staff) === "super_admin") return true;
  if (staff.departmentId === "all") return true;
  return false;
}

async function findStaffAccountByLogin(loginRaw) {
  if (fileStore) {
    const acc = await fileStore.findStaffAccountByLogin(loginRaw);
    if (!acc) return null;
    return { id: acc.id, data: () => acc };
  }
  if (!db) return null;
  const trimmed = String(loginRaw || "").trim();
  if (!trimmed) return null;
  let snap = await db.collection("staff_accounts").where("loginId", "==", trimmed).limit(1).get();
  if (!snap.empty) return snap.docs[0];
  const em = trimmed.toLowerCase();
  snap = await db.collection("staff_accounts").where("email", "==", em).limit(1).get();
  if (!snap.empty) return snap.docs[0];
  return null;
}

async function ensureDefaultSuperAdmin() {
  if (fileStore) {
    await fileStore.ensureDefaultSuperAdmin();
    return;
  }
  if (!db) return;
  try {
    const existing = await db
      .collection("staff_accounts")
      .where("loginId", "==", "super_admin")
      .limit(1)
      .get();
    if (!existing.empty) return;
    const hash = await bcrypt.hash("123456", 10);
    await db.collection("staff_accounts").add({
      loginId: "super_admin",
      email: "super_admin@tlu.console",
      fullName: "Super Admin",
      staffCode: "SUPER",
      departmentId: "all",
      departmentName: "Toàn trường",
      role: "super_admin",
      isSuper: true,
      passwordHash: hash,
      active: true,
      createdAt: FieldValue.serverTimestamp(),
      updatedAt: FieldValue.serverTimestamp(),
    });
    console.log("[staff-console] Seeded default super_admin (super_admin / 123456)");
  } catch (e) {
    console.warn("[staff-console] ensureDefaultSuperAdmin:", e?.message || e);
  }
}

const app = express();

const DEFAULT_CORS_ORIGINS = [
  "http://localhost:5173",
  "http://127.0.0.1:5173",
  "http://localhost:5174",
  "http://127.0.0.1:5174",
  "http://localhost:3000",
  "http://127.0.0.1:3000",
];
const CORS_ALLOWLIST = (process.env.STAFF_CORS_ORIGINS || DEFAULT_CORS_ORIGINS.join(","))
  .split(",")
  .map((s) => s.trim().replace(/\/$/, ""))
  .filter(Boolean);

function isAllowedStaffOrigin(origin) {
  if (!origin) return false;
  if (CORS_ALLOWLIST.includes(origin)) return true;
  try {
    const { hostname } = new URL(origin);
    if (hostname === "localhost" || hostname === "127.0.0.1") return true;
    if (/^192\.168\.\d{1,3}\.\d{1,3}$/.test(hostname)) return true;
    if (/^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(hostname)) return true;
  } catch {
    /* ignore */
  }
  return false;
}

app.use((req, res, next) => {
  const origin = req.get("Origin");
  if (origin && isAllowedStaffOrigin(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Vary", "Origin");
  }
  res.setHeader("Access-Control-Allow-Methods", "GET,HEAD,POST,PATCH,DELETE,OPTIONS");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization, X-Staff-Key, X-Student-Key, X-Actor-Email, X-Actor-Uid",
  );
  res.setHeader("Access-Control-Max-Age", "86400");
  if (req.method === "OPTIONS") {
    return res.sendStatus(204);
  }
  next();
});

app.use(express.json({ limit: "1mb" }));

app.get("/api/public/health", (_req, res) => {
  res.json({ ok: true });
});

function parseBearerToken(req) {
  const h = req.get("Authorization") || "";
  const m = h.match(/^Bearer\s+(.+)$/i);
  if (!m) return null;
  try {
    return jwt.verify(m[1].trim(), JWT_SECRET);
  } catch {
    return "invalid";
  }
}

function requireAuth(req, res, next) {
  if (isMaster(req)) {
    req.auth = { mode: "master" };
    return next();
  }
  const payload = parseBearerToken(req);
  if (payload === "invalid") {
    return res.status(401).json({ error: "Invalid or expired Bearer token" });
  }
  if (!payload) {
    return res.status(401).json({ error: "Cần đăng nhập (Authorization: Bearer <token>)" });
  }
  req.auth = { mode: "staff", staff: payload };
  next();
}

function requireSuperAdminRoute(req, res, next) {
  if (isMaster(req)) return next();
  if (req.auth?.mode === "staff" && effectiveRoleFromJwt(req.auth.staff) === "super_admin") {
    return next();
  }
  return res.status(403).json({ error: "Cần quyền quản trị hệ thống (super admin)." });
}

function requireNotificationAdmin(req, res, next) {
  if (isMaster(req)) return next();
  if (req.auth?.mode === "staff" && effectiveRoleFromJwt(req.auth.staff) === "super_admin") {
    return next();
  }
  return res.status(403).json({ error: "Chỉ quản trị hệ thống được tạo/xóa thông báo" });
}

function requireUserPatchAdmin(req, res, next) {
  if (isMaster(req)) return next();
  if (req.auth?.mode === "staff" && effectiveRoleFromJwt(req.auth.staff) === "super_admin") {
    return next();
  }
  return res.status(403).json({ error: "Chỉ quản trị được cập nhật hồ sơ sinh viên" });
}

function requireAuditReader(req, res, next) {
  if (isMaster(req)) return next();
  const r = req.auth?.mode === "staff" ? effectiveRoleFromJwt(req.auth.staff) : null;
  if (r === "super_admin" || r === "auditor") return next();
  return res.status(403).json({ error: "Không có quyền xem nhật ký" });
}

function requireRagOperator(req, res, next) {
  if (isMaster(req)) return next();
  const r = req.auth?.mode === "staff" ? effectiveRoleFromJwt(req.auth.staff) : null;
  if (r === "super_admin" || r === "staff") return next();
  return res.status(403).json({ error: "Không có quyền thao tác RAG" });
}

function requireChatParticipant(req, res, next) {
  if (isMaster(req)) return next();
  const r = req.auth?.mode === "staff" ? effectiveRoleFromJwt(req.auth.staff) : null;
  if (r === "super_admin" || r === "staff") return next();
  return res.status(403).json({ error: "Không có quyền truy cập chat phòng ban" });
}

function storageReady() {
  return Boolean(fileStore || db);
}

function requireStudentAuth(req, res, next) {
  const key = (req.get("X-Student-Key") || "").trim();
  if (!STUDENT_KEY || key !== STUDENT_KEY) {
    return res.status(401).json({ error: "Invalid or missing X-Student-Key" });
  }
  req.studentUid =
    (req.get("X-Student-Uid") || process.env.DEMO_STUDENT_UID || "demo_student_257480001").trim();
  next();
}

async function ensureDepartmentsSeeded() {
  if (fileStore) {
    await fileStore.ensureDepartmentsSeeded();
    return;
  }
  if (!db) return;
  const snap = await db.collection("departments").limit(1).get();
  if (!snap.empty) return;
  const batch = db.batch();
  for (const d of DEFAULT_DEPARTMENTS) {
    batch.set(db.collection("departments").doc(d.id), {
      ...d,
      createdAt: FieldValue.serverTimestamp(),
    });
  }
  await batch.commit();
}

/** --- Public auth --- */
app.post("/api/auth/staff-login", async (req, res) => {
  try {
    if (!storageReady()) {
      return res.status(503).json({
        error:
          "Chưa cấu hình storage. Với demo: STORAGE_BACKEND=file. Production: Firebase credentials.",
      });
    }
    await ensureDepartmentsSeeded();
    await ensureDefaultSuperAdmin();
    const body = req.body || {};
    const login = String(body.login ?? body.email ?? "").trim();
    const password = body.password;
    if (!login || !password) {
      return res.status(400).json({ error: "login (hoặc email) và password là bắt buộc" });
    }
    const doc = await findStaffAccountByLogin(login);
    if (!doc) {
      return res.status(401).json({ error: "Sai tài khoản hoặc mật khẩu" });
    }
    const data = doc.data();
    if (data.active === false) {
      return res.status(403).json({ error: "Tài khoản đã vô hiệu" });
    }
    const ok = await bcrypt.compare(String(password), data.passwordHash || "");
    if (!ok) return res.status(401).json({ error: "Sai tài khoản hoặc mật khẩu" });
    const role = effectiveRoleFromDoc(data);
    const token = jwt.sign(
      {
        sub: doc.id,
        email: data.email,
        loginId: data.loginId || null,
        fullName: data.fullName || "",
        staffCode: data.staffCode || "",
        departmentId: data.departmentId,
        departmentName: data.departmentName || "",
        role,
        isSuper: role === "super_admin",
      },
      JWT_SECRET,
      { expiresIn: "12h" },
    );
    res.json({
      token,
      staff: {
        id: doc.id,
        email: data.email,
        loginId: data.loginId || null,
        fullName: data.fullName,
        staffCode: data.staffCode,
        departmentId: data.departmentId,
        departmentName: data.departmentName,
        role,
        isSuper: role === "super_admin",
      },
    });
  } catch (e) {
    console.error(e);
    const msg = String(e?.message || e);
    const looksLikeFirebase =
      /Project Id|GOOGLE_APPLICATION|Firebase|firestore|Unable to detect/i.test(msg) ||
      e?.code === 5 ||
      e?.code === 7;
    res.status(looksLikeFirebase ? 503 : 500).json({
      error: looksLikeFirebase
        ? "Không kết nối được Firebase/Firestore. Kiểm tra credential trên máy chủ staff-console."
        : msg,
    });
  }
});

app.get("/api/auth/me", requireAuth, (req, res) => {
  if (req.auth.mode === "master") {
    return res.json({ mode: "master", role: "super_admin" });
  }
  res.json({ mode: "staff", ...req.auth.staff });
});

app.get("/api/health", requireAuth, async (_req, res) => {
  let ragOk = false;
  try {
    const r = await fetch(`${RAG_URL}/health`, { signal: AbortSignal.timeout(3000) });
    ragOk = r.ok;
  } catch {
    ragOk = false;
  }
  res.json({
    ok: true,
    storage: USE_FILE_STORAGE ? "file" : "firebase",
    firebase: Boolean(db),
    rag: ragOk,
    ragUrl: RAG_URL,
  });
});

function tsToIso(v) {
  if (!v) return null;
  if (typeof v.toDate === "function") return v.toDate().toISOString();
  if (v instanceof Date) return v.toISOString();
  return null;
}

function serializeUserDoc(x) {
  return {
    email: x.email ?? null,
    displayName: x.displayName ?? null,
    photoUrl: x.photoUrl ?? null,
    role: x.role ?? "student",
    studentCode: x.studentCode ?? null,
    fullName: x.fullName ?? null,
    className: x.className ?? null,
    faculty: x.faculty ?? null,
    course: x.course ?? null,
    phone: x.phone ?? null,
    source: x.source ?? null,
    syncedAt: tsToIso(x.syncedAt),
    createdAt: tsToIso(x.createdAt),
    updatedAt: tsToIso(x.updatedAt),
  };
}

async function writeAudit(req, action, resourceId, summary, resourceType = "staff_console") {
  let actorEmail = (req.get("X-Actor-Email") || "").trim() || null;
  let actorUid = (req.get("X-Actor-Uid") || "").trim() || null;
  let actorRole = "staff_console";
  if (req.auth?.mode === "master") {
    actorEmail = actorEmail || "master-api-key";
    actorRole = "master";
  } else if (req.auth?.mode === "staff" && req.auth.staff) {
    actorEmail = req.auth.staff.email || actorEmail;
    actorUid = req.auth.staff.sub || actorUid;
    actorRole = req.auth.staff.role || (req.auth.staff.isSuper ? "super_admin" : "staff");
  }
  if (fileStore) {
    await fileStore.appendAudit({
      actorUid,
      actorEmail,
      actorRole,
      action,
      resourceType,
      resourceId,
      payloadSummary: String(summary).slice(0, 500),
      result: "success",
    });
    return;
  }
  if (!db) return;
  await db.collection("audit_logs").add({
    at: FieldValue.serverTimestamp(),
    actorUid,
    actorEmail,
    actorRole,
    action,
    resourceType,
    resourceId,
    payloadSummary: String(summary).slice(0, 500),
    result: "success",
  });
}

/** --- users (Admin) — quản lý sinh viên --- */
app.get("/api/users", requireAuth, async (req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  const roleFilter = (req.query.role || "student").toString();
  try {
    if (fileStore) {
      const items = await fileStore.listUsers(roleFilter);
      return res.json({ items });
    }
    const snap = await db.collection("users").limit(500).get();
    let items = snap.docs.map((d) => ({
      id: d.id,
      ...serializeUserDoc(d.data()),
    }));
    if (roleFilter !== "all") {
      items = items.filter((u) => (u.role || "student") === roleFilter);
    }
    items.sort((a, b) => (b.updatedAt || "").localeCompare(a.updatedAt || ""));
    res.json({ items });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.patch("/api/users/:uid", requireAuth, requireUserPatchAdmin, async (req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  const { uid } = req.params;
  const body = req.body || {};
  const allowed = [
    "studentCode",
    "fullName",
    "className",
    "faculty",
    "course",
    "phone",
    "source",
  ];
  const patch = {};
  for (const k of allowed) {
    if (Object.prototype.hasOwnProperty.call(body, k)) {
      const v = body[k];
      patch[k] = v == null || v === "" ? null : String(v);
    }
  }
  if (Object.keys(patch).length === 0) {
    return res.status(400).json({ error: "No allowed fields to update" });
  }
  try {
    if (fileStore) {
      await fileStore.patchUser(uid, patch);
    } else {
      patch.updatedAt = FieldValue.serverTimestamp();
      patch.syncedAt = FieldValue.serverTimestamp();
      await db.collection("users").doc(uid).set(patch, { merge: true });
    }
    await writeAudit(req, "UPDATE_USER_PROFILE", uid, JSON.stringify(patch), "users");
    res.json({ ok: true });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

/** --- Notifications --- */
app.get("/api/notifications", requireAuth, async (_req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  try {
    if (fileStore) {
      const items = await fileStore.listNotifications();
      return res.json({ items });
    }
    const snap = await db
      .collection("school_notifications")
      .orderBy("createdAt", "desc")
      .limit(100)
      .get();
    const items = snap.docs.map((d) => {
      const x = d.data();
      return {
        id: d.id,
        title: x.title ?? "",
        body: x.body ?? "",
        link: x.link ?? null,
        createdAt: tsToIso(x.createdAt),
      };
    });
    res.json({ items });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.post("/api/notifications", requireAuth, requireNotificationAdmin, async (req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  const { title, body, link } = req.body || {};
  if (!title || typeof title !== "string") {
    return res.status(400).json({ error: "title is required" });
  }
  try {
    if (fileStore) {
      const id = await fileStore.createNotification({ title, body, link });
      await writeAudit(req, "CREATE_NOTIFICATION", id, title, "school_notification");
      return res.json({ id });
    }
    const ref = await db.collection("school_notifications").add({
      title: String(title).trim(),
      body: body != null ? String(body) : "",
      link: link != null && link !== "" ? String(link) : null,
      createdAt: FieldValue.serverTimestamp(),
    });
    await writeAudit(req, "CREATE_NOTIFICATION", ref.id, title, "school_notification");
    const titleTrim = String(title).trim();
    const bodyStr = body != null ? String(body) : "";
    void sendFcmSafely((m) =>
      m.send({
        topic: "school_broadcast",
        notification: {
          title: titleTrim,
          body: bodyStr.length > 200 ? `${bodyStr.slice(0, 200)}…` : bodyStr,
        },
        data: {
          type: "school_notification",
          id: ref.id,
        },
      }),
    );
    res.json({ id: ref.id });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.delete("/api/notifications/:id", requireAuth, requireNotificationAdmin, async (req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  const { id } = req.params;
  try {
    if (fileStore) {
      await fileStore.deleteNotification(id);
      await writeAudit(req, "DELETE_NOTIFICATION", id, id, "school_notification");
      return res.json({ deleted: true });
    }
    await db.collection("school_notifications").doc(id).delete();
    await writeAudit(req, "DELETE_NOTIFICATION", id, id, "school_notification");
    res.json({ deleted: true });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.get("/api/submissions", requireAuth, async (_req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  try {
    if (fileStore) {
      const items = await fileStore.listSubmissions();
      return res.json({ items });
    }
    const snap = await db
      .collection("application_submissions")
      .orderBy("createdAt", "desc")
      .limit(200)
      .get();
    const items = snap.docs.map((d) => {
      const x = d.data();
      return {
        id: d.id,
        title: x.title,
        details: x.details,
        source: x.source,
        studentUid: x.studentUid ?? null,
        studentEmail: x.studentEmail ?? null,
        uploadBatchId: x.uploadBatchId,
        attachmentCount: Array.isArray(x.attachments) ? x.attachments.length : 0,
        createdAt: tsToIso(x.createdAt),
      };
    });
    res.json({ items });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.get("/api/feedback", requireAuth, async (_req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  try {
    if (fileStore) {
      const items = await fileStore.listFeedback();
      return res.json({ items });
    }
    const snap = await db
      .collection("feedback_letters")
      .orderBy("createdAt", "desc")
      .limit(200)
      .get();
    const items = snap.docs.map((d) => {
      const x = d.data();
      return {
        id: d.id,
        subject: x.subject,
        body: x.body,
        anonymous: Boolean(x.anonymous),
        studentLabel: x.studentLabel ?? null,
        studentUid: x.studentUid ?? null,
        studentEmail: x.studentEmail ?? null,
        source: x.source,
        createdAt: tsToIso(x.createdAt),
      };
    });
    res.json({ items });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.get("/api/audit-logs", requireAuth, requireAuditReader, async (_req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  try {
    if (fileStore) {
      const items = await fileStore.listAuditLogs();
      return res.json({ items });
    }
    let snap;
    try {
      snap = await db.collection("audit_logs").orderBy("at", "desc").limit(100).get();
    } catch {
      snap = await db.collection("audit_logs").limit(50).get();
    }
    const items = snap.docs.map((d) => {
      const x = d.data();
      return {
        id: d.id,
        action: x.action,
        resourceType: x.resourceType,
        resourceId: x.resourceId,
        payloadSummary: x.payloadSummary,
        result: x.result,
        actorUid: x.actorUid ?? null,
        actorEmail: x.actorEmail ?? null,
        actorRole: x.actorRole ?? null,
        at: tsToIso(x.at),
      };
    });
    res.json({ items });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

/** --- Departments --- */
app.get("/api/departments", requireAuth, async (_req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  try {
    await ensureDepartmentsSeeded();
    if (fileStore) {
      const items = await fileStore.ensureDepartmentsSeeded();
      return res.json({ items });
    }
    const snap = await db.collection("departments").orderBy("name").get();
    const items = snap.docs.map((d) => ({ id: d.id, ...d.data() }));
    res.json({ items });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

/** --- Staff accounts (super admin) --- */
app.get("/api/staff/accounts", requireAuth, requireSuperAdminRoute, async (_req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  try {
    if (fileStore) {
      const items = await fileStore.listStaffAccounts();
      items.sort((a, b) => (a.email || "").localeCompare(b.email || ""));
      return res.json({ items });
    }
    const snap = await db.collection("staff_accounts").limit(200).get();
    const items = snap.docs.map((d) => {
      const x = d.data();
      const role = effectiveRoleFromDoc(x);
      return {
        id: d.id,
        email: x.email,
        loginId: x.loginId ?? null,
        fullName: x.fullName ?? "",
        staffCode: x.staffCode ?? "",
        departmentId: x.departmentId,
        departmentName: x.departmentName ?? "",
        role,
        isSuper: role === "super_admin",
        active: x.active !== false,
        createdAt: tsToIso(x.createdAt),
        updatedAt: tsToIso(x.updatedAt),
      };
    });
    items.sort((a, b) => (a.email || "").localeCompare(b.email || ""));
    res.json({ items });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.post("/api/staff/accounts", requireAuth, requireSuperAdminRoute, async (req, res) => {
  if (!db) return res.status(503).json({ error: "Firebase not configured" });
  const body = req.body || {};
  const { email, password, fullName, staffCode, departmentId, loginId, isSuper } = body;
  let { role: roleIn } = body;
  if (!email || !password || !departmentId) {
    return res.status(400).json({ error: "email, password, departmentId required" });
  }
  const role =
    roleIn === "super_admin" || roleIn === "staff" || roleIn === "auditor"
      ? roleIn
      : isSuper
        ? "super_admin"
        : "staff";
  const em = String(email).toLowerCase().trim();
  const lid = loginId != null && String(loginId).trim() !== "" ? String(loginId).trim() : "";
  try {
    const dup = await db.collection("staff_accounts").where("email", "==", em).limit(1).get();
    if (!dup.empty) return res.status(409).json({ error: "Email đã tồn tại" });
    if (lid) {
      const dupLid = await db.collection("staff_accounts").where("loginId", "==", lid).limit(1).get();
      if (!dupLid.empty) return res.status(409).json({ error: "Mã đăng nhập đã tồn tại" });
    }
    const did = String(departmentId);
    const deptRef = await db.collection("departments").doc(did).get();
    const departmentName =
      did === "all" ? "Toàn trường" : deptRef.exists ? deptRef.data().name : did;
    const hash = await bcrypt.hash(String(password), 10);
    const ref = await db.collection("staff_accounts").add({
      email: em,
      loginId: lid || null,
      passwordHash: hash,
      fullName: String(fullName || "").trim(),
      staffCode: String(staffCode || "").trim(),
      departmentId: did,
      departmentName,
      role,
      isSuper: role === "super_admin",
      active: true,
      createdAt: FieldValue.serverTimestamp(),
      updatedAt: FieldValue.serverTimestamp(),
    });
    await writeAudit(req, "CREATE_STAFF_ACCOUNT", ref.id, em, "staff_accounts");
    res.json({ id: ref.id });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.patch("/api/staff/accounts/:id", requireAuth, requireSuperAdminRoute, async (req, res) => {
  if (!db) return res.status(503).json({ error: "Firebase not configured" });
  const { id } = req.params;
  const body = req.body || {};
  const patch = {};
  if (body.fullName !== undefined) patch.fullName = String(body.fullName || "").trim();
  if (body.staffCode !== undefined) patch.staffCode = String(body.staffCode || "").trim();
  if (body.departmentId !== undefined) {
    patch.departmentId = String(body.departmentId);
    const dr = await db.collection("departments").doc(patch.departmentId).get();
    patch.departmentName =
      patch.departmentId === "all" ? "Toàn trường" : dr.exists ? dr.data().name : patch.departmentId;
  }
  if (body.password) {
    patch.passwordHash = await bcrypt.hash(String(body.password), 10);
  }
  if (body.active !== undefined) patch.active = Boolean(body.active);
  if (body.isSuper !== undefined) patch.isSuper = Boolean(body.isSuper);
  if (body.role === "super_admin" || body.role === "staff" || body.role === "auditor") {
    patch.role = body.role;
    patch.isSuper = body.role === "super_admin";
  }
  if (Object.prototype.hasOwnProperty.call(body, "loginId")) {
    const lid = body.loginId == null ? "" : String(body.loginId).trim();
    if (lid) {
      const dupLid = await db
        .collection("staff_accounts")
        .where("loginId", "==", lid)
        .limit(1)
        .get();
      if (!dupLid.empty && dupLid.docs[0].id !== id) {
        return res.status(409).json({ error: "Mã đăng nhập đã tồn tại" });
      }
      patch.loginId = lid;
    } else {
      patch.loginId = null;
    }
  }
  if (Object.keys(patch).length === 0) {
    return res.status(400).json({ error: "No fields to update" });
  }
  patch.updatedAt = FieldValue.serverTimestamp();
  try {
    await db.collection("staff_accounts").doc(id).set(patch, { merge: true });
    await writeAudit(req, "UPDATE_STAFF_ACCOUNT", id, JSON.stringify(Object.keys(patch)), "staff_accounts");
    res.json({ ok: true });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.delete("/api/staff/accounts/:id", requireAuth, requireSuperAdminRoute, async (req, res) => {
  if (!db) return res.status(503).json({ error: "Firebase not configured" });
  try {
    await db
      .collection("staff_accounts")
      .doc(req.params.id)
      .set({ active: false, updatedAt: FieldValue.serverTimestamp() }, { merge: true });
    await writeAudit(req, "DISABLE_STAFF_ACCOUNT", req.params.id, "", "staff_accounts");
    res.json({ ok: true });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

/** --- Chat phòng ban --- */
app.get("/api/chat/threads", requireAuth, requireChatParticipant, async (req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  try {
    if (fileStore) {
      let departmentId = "";
      if (req.auth.mode === "master" || isCrossDepartmentStaffPayload(req.auth.staff)) {
        departmentId = req.query.departmentId ? String(req.query.departmentId) : "";
      } else if (req.auth.mode === "staff") {
        departmentId = req.auth.staff.departmentId;
      }
      const items = await fileStore.listChatThreads({
        departmentId: departmentId || undefined,
      });
      return res.json({ items });
    }
    let snap;
    if (req.auth.mode === "master") {
      const dept = req.query.departmentId ? String(req.query.departmentId) : "";
      if (dept) {
        snap = await db
          .collection("department_threads")
          .where("departmentId", "==", dept)
          .orderBy("lastMessageAt", "desc")
          .limit(100)
          .get();
      } else {
        snap = await db
          .collection("department_threads")
          .orderBy("lastMessageAt", "desc")
          .limit(100)
          .get();
      }
    } else if (isCrossDepartmentStaffPayload(req.auth.staff)) {
      const dept = req.query.departmentId ? String(req.query.departmentId) : "";
      if (dept) {
        snap = await db
          .collection("department_threads")
          .where("departmentId", "==", dept)
          .orderBy("lastMessageAt", "desc")
          .limit(100)
          .get();
      } else {
        snap = await db
          .collection("department_threads")
          .orderBy("lastMessageAt", "desc")
          .limit(100)
          .get();
      }
    } else {
      snap = await db
        .collection("department_threads")
        .where("departmentId", "==", req.auth.staff.departmentId)
        .orderBy("lastMessageAt", "desc")
        .limit(100)
        .get();
    }
    const items = snap.docs.map((d) => {
      const x = d.data();
      return {
        id: d.id,
        studentUid: x.studentUid,
        studentEmail: x.studentEmail ?? null,
        departmentId: x.departmentId,
        departmentTitle: x.departmentTitle ?? "",
        status: x.status ?? "open",
        preview: x.preview ?? "",
        lastMessageAt: tsToIso(x.lastMessageAt),
        createdAt: tsToIso(x.createdAt),
        unreadForStaff: 0,
      };
    });
    res.json({ items });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.get("/api/chat/threads/:threadId/messages", requireAuth, requireChatParticipant, async (req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  const { threadId } = req.params;
  try {
    if (fileStore) {
      const t = await fileStore.getThreadMeta(threadId);
      if (!t) return res.status(404).json({ error: "not found" });
      if (req.auth.mode === "staff") {
        if (
          t.departmentId !== req.auth.staff.departmentId &&
          !isCrossDepartmentStaffPayload(req.auth.staff)
        ) {
          return res.status(403).json({ error: "Forbidden" });
        }
        await fileStore.markStaffRead(threadId);
      }
      const items = await fileStore.listThreadMessages(threadId);
      return res.json({ items, threadId });
    }
    const thread = await db.collection("department_threads").doc(threadId).get();
    if (!thread.exists) return res.status(404).json({ error: "not found" });
    const t = thread.data();
    if (req.auth.mode === "staff") {
      if (
        t.departmentId !== req.auth.staff.departmentId &&
        !isCrossDepartmentStaffPayload(req.auth.staff)
      ) {
        return res.status(403).json({ error: "Forbidden" });
      }
    }
    const snap = await thread.ref
      .collection("messages")
      .orderBy("createdAt", "asc")
      .limit(300)
      .get();
    const items = snap.docs.map((d) => {
      const x = d.data();
      return {
        id: d.id,
        text: x.text,
        senderUid: x.senderUid,
        senderRole: x.senderRole,
        senderName: x.senderName ?? null,
        createdAt: tsToIso(x.createdAt),
      };
    });
    res.json({ items });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.post("/api/chat/threads/:threadId/messages", requireAuth, requireChatParticipant, async (req, res) => {
  if (!storageReady()) return res.status(503).json({ error: "Storage not configured" });
  const { threadId } = req.params;
  const { text } = req.body || {};
  if (!text || typeof text !== "string") {
    return res.status(400).json({ error: "text required" });
  }
  try {
    if (fileStore) {
      const t = await fileStore.getThreadMeta(threadId);
      if (!t) return res.status(404).json({ error: "not found" });
      if (req.auth.mode === "staff") {
        if (
          t.departmentId !== req.auth.staff.departmentId &&
          !isCrossDepartmentStaffPayload(req.auth.staff)
        ) {
          return res.status(403).json({ error: "Forbidden" });
        }
      } else if (req.auth.mode !== "master") {
        return res.status(403).json({ error: "Chỉ cán bộ hoặc master mới trả lời thread" });
      }
      const name =
        req.auth.mode === "master"
          ? "Cán bộ (master)"
          : req.auth.staff.fullName || req.auth.staff.email || "Cán bộ";
      const uid = req.auth.mode === "master" ? "master" : req.auth.staff.sub;
      const trimmed = String(text).trim();
      const id = await fileStore.sendStaffMessage(threadId, {
        text: trimmed,
        senderUid: uid,
        senderName: name,
      });
      await writeAudit(req, "CHAT_STAFF_REPLY", threadId, trimmed.slice(0, 120), "department_thread");
      return res.json({ id });
    }
    const threadRef = db.collection("department_threads").doc(threadId);
    const thread = await threadRef.get();
    if (!thread.exists) return res.status(404).json({ error: "not found" });
    const t = thread.data();
    if (req.auth.mode === "staff") {
      if (
        t.departmentId !== req.auth.staff.departmentId &&
        !isCrossDepartmentStaffPayload(req.auth.staff)
      ) {
        return res.status(403).json({ error: "Forbidden" });
      }
    } else if (req.auth.mode !== "master") {
      return res.status(403).json({ error: "Chỉ cán bộ hoặc master mới trả lời thread" });
    }
    const name =
      req.auth.mode === "master"
        ? "Cán bộ (master)"
        : req.auth.staff.fullName || req.auth.staff.email || "Cán bộ";
    const uid = req.auth.mode === "master" ? "master" : req.auth.staff.sub;
    const trimmed = String(text).trim();
    const msgRef = threadRef.collection("messages").doc();
    const batch = db.batch();
    batch.set(msgRef, {
      text: trimmed,
      senderUid: uid,
      senderRole: "staff",
      senderName: name,
      createdAt: FieldValue.serverTimestamp(),
    });
    batch.set(
      threadRef,
      {
        preview: trimmed.length > 200 ? `${trimmed.slice(0, 200)}…` : trimmed,
        lastMessageAt: FieldValue.serverTimestamp(),
        status: "answered",
      },
      { merge: true },
    );
    await batch.commit();
    await writeAudit(req, "CHAT_STAFF_REPLY", threadId, trimmed.slice(0, 120), "department_thread");
    const studentUid = t.studentUid ? String(t.studentUid) : "";
    if (studentUid && studentUid !== "master") {
      void sendFcmSafely(async (m) => {
        const u = await db.collection("users").doc(studentUid).get();
        const token = u.exists ? String(u.data()?.fcmToken || "").trim() : "";
        if (!token) return;
        await m.send({
          token,
          notification: {
            title: "Tin từ phòng ban",
            body: trimmed.length > 120 ? `${trimmed.slice(0, 120)}…` : trimmed,
          },
          data: {
            type: "department_staff_message",
            threadId,
            departmentId: String(t.departmentId || ""),
          },
        });
      });
    }
    res.json({ id: msgRef.id });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message || e) });
  }
});

/** --- Student API (demo / local file storage) --- */
const DEPT_TITLES = {
  co_van: "Cố vấn học tập",
  ct_sv: "Phòng Công tác Chính trị Sinh viên",
  dao_tao: "Phòng Đào tạo",
  tai_chinh: "Phòng Tài chính - Kế toán",
  tam_ly: "Phòng Tham vấn tâm lý",
};

app.get("/api/student/chat/unread-summary", requireStudentAuth, async (req, res) => {
  if (!fileStore) return res.status(503).json({ error: "Student API requires STORAGE_BACKEND=file" });
  try {
    const items = await fileStore.listStudentUnreadByDepartment(req.studentUid);
    const totalUnread = items.reduce((s, x) => s + (x.unread || 0), 0);
    res.json({ items, totalUnread });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.get("/api/student/profile", requireStudentAuth, async (req, res) => {
  if (!fileStore) return res.status(503).json({ error: "Student API requires STORAGE_BACKEND=file" });
  try {
    const profile = await fileStore.getStudentProfile(req.studentUid);
    if (!profile) {
      return res.json({
        uid: req.studentUid,
        fullName: "Nguyễn Minh Anh",
        studentCode: "257480001",
        email: "minhanh.nguyen@thanglong.edu.vn",
        faculty: "Khoa học Máy tính",
        course: "năm nhất",
      });
    }
    res.json(profile);
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.get("/api/student/notifications", requireStudentAuth, async (_req, res) => {
  if (!fileStore) return res.status(503).json({ error: "Student API requires STORAGE_BACKEND=file" });
  try {
    const items = await fileStore.listNotifications();
    res.json({ items });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.get(
  "/api/student/chat/threads/:departmentId/messages",
  requireStudentAuth,
  async (req, res) => {
    if (!fileStore) return res.status(503).json({ error: "Student API requires STORAGE_BACKEND=file" });
    const departmentId = req.params.departmentId;
    const departmentTitle = DEPT_TITLES[departmentId] || departmentId;
    try {
      const profile = (await fileStore.getStudentProfile(req.studentUid)) || {};
      await fileStore.ensureStudentThread({
        studentUid: req.studentUid,
        studentEmail: profile.email || "",
        studentName: profile.fullName || profile.displayName || "Sinh viên",
        departmentId,
        departmentTitle,
      });
      const threadId = `${req.studentUid}_${departmentId}`;
      await fileStore.markStudentRead(threadId);
      const items = await fileStore.listThreadMessages(threadId);
      res.json({ threadId, items });
    } catch (e) {
      res.status(500).json({ error: String(e.message || e) });
    }
  },
);

app.post(
  "/api/student/chat/threads/:departmentId/messages",
  requireStudentAuth,
  async (req, res) => {
    if (!fileStore) return res.status(503).json({ error: "Student API requires STORAGE_BACKEND=file" });
    const { text } = req.body || {};
    if (!text || typeof text !== "string") {
      return res.status(400).json({ error: "text required" });
    }
    const departmentId = req.params.departmentId;
    const departmentTitle = DEPT_TITLES[departmentId] || departmentId;
    try {
      const profile = (await fileStore.getStudentProfile(req.studentUid)) || {};
      const result = await fileStore.sendStudentMessage({
        studentUid: req.studentUid,
        studentEmail: profile.email || "",
        studentName: profile.fullName || "Sinh viên",
        departmentId,
        departmentTitle,
        text,
      });
      res.json(result);
    } catch (e) {
      res.status(500).json({ error: String(e.message || e) });
    }
  },
);

app.post(
  "/api/student/submissions",
  requireStudentAuth,
  upload.fields([{ name: "files", maxCount: 5 }]),
  async (req, res) => {
    if (!fileStore) return res.status(503).json({ error: "Student API requires STORAGE_BACKEND=file" });
    const title = String(req.body?.title || "").trim();
    const details = String(req.body?.details || "").trim();
    if (!title || !details) {
      return res.status(400).json({ error: "title and details required" });
    }
    try {
      const profile = (await fileStore.getStudentProfile(req.studentUid)) || {};
      const submissionId = randomUUID();
      const attachments = [];
      const files = req.files?.files || [];
      for (let i = 0; i < files.length; i++) {
        const f = files[i];
        const rel = await fileStore.saveUploadFile(
          submissionId,
          i,
          f.originalname || "file.bin",
          f.buffer,
        );
        attachments.push({
          name: f.originalname,
          size: f.size,
          storagePath: rel,
          url: `/api/files/${submissionId}/${encodeURIComponent(path.basename(rel))}`,
        });
      }
      await fileStore.createSubmission({
        id: submissionId,
        title,
        details,
        source: "flutter_app",
        studentUid: req.studentUid,
        studentEmail: profile.email || null,
        uploadBatchId: submissionId,
        attachments,
      });
      res.json({ id: submissionId });
    } catch (e) {
      res.status(500).json({ error: String(e.message || e) });
  }
  },
);

app.post("/api/student/rag-feedback", requireStudentAuth, async (req, res) => {
  if (!fileStore) {
    return res.status(503).json({ error: "Student API requires STORAGE_BACKEND=file" });
  }
  const {
    messageId,
    question,
    answer,
    rating,
    retrievedContexts,
    retrievalMode,
    source,
  } = req.body || {};
  if (!messageId || !question || !answer || !rating) {
    return res.status(400).json({ error: "messageId, question, answer, rating required" });
  }
  if (rating !== "up" && rating !== "down") {
    return res.status(400).json({ error: "rating must be up or down" });
  }
  try {
    const profile = (await fileStore.getStudentProfile(req.studentUid)) || {};
    const id = await fileStore.appendRagFeedback({
      messageId: String(messageId),
      question: String(question).trim(),
      answer: String(answer).trim(),
      rating,
      retrievedContexts: Array.isArray(retrievedContexts) ? retrievedContexts : [],
      retrievalMode: retrievalMode ? String(retrievalMode) : null,
      studentUid: req.studentUid,
      studentEmail: profile.email || null,
      source: source || "flutter_app",
    });
    res.json({ id });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.post("/api/student/feedback", requireStudentAuth, async (req, res) => {
  if (!fileStore) return res.status(503).json({ error: "Student API requires STORAGE_BACKEND=file" });
  const { subject, body, anonymous, studentLabel } = req.body || {};
  if (!subject || !body) {
    return res.status(400).json({ error: "subject and body required" });
  }
  try {
    const profile = (await fileStore.getStudentProfile(req.studentUid)) || {};
    const id = await fileStore.createFeedback({
      subject: String(subject).trim(),
      body: String(body).trim(),
      anonymous: Boolean(anonymous),
      studentLabel: anonymous ? null : studentLabel || profile.fullName,
      studentUid: req.studentUid,
      studentEmail: profile.email || null,
      source: "flutter_app",
    });
    res.json({ id });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.get("/api/files/:submissionId/:filename", requireAuth, async (req, res) => {
  if (!fileStore) return res.status(503).json({ error: "File storage not configured" });
  try {
    const doc = await fileStore.getSubmission(req.params.submissionId);
    if (!doc) return res.status(404).json({ error: "not found" });
    const att = (doc.attachments || []).find((a) =>
      a.url?.includes(req.params.filename) || a.storagePath?.endsWith(req.params.filename),
    );
    if (!att?.storagePath) return res.status(404).json({ error: "file not found" });
    const abs = fileStore.uploadAbsPath(att.storagePath);
    res.sendFile(abs);
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

/** --- RAG proxy --- */
async function ragFetch(path, init) {
  if (!RAG_ADMIN_KEY) throw new Error("RAG_ADMIN_KEY not set on server");
  const headers = new Headers(init?.headers);
  headers.set("X-Admin-Key", RAG_ADMIN_KEY);
  return fetch(`${RAG_URL}${path}`, { ...init, headers });
}

app.get("/api/rag/documents", requireAuth, requireRagOperator, async (_req, res) => {
  try {
    const r = await ragFetch("/admin/documents", { method: "GET" });
    const text = await r.text();
    if (!r.ok) return res.status(r.status).type("text/plain").send(text);
    res.type("application/json").send(text);
  } catch (e) {
    res.status(502).json({ error: String(e.message || e) });
  }
});

app.get("/api/rag/ingest-jobs/:jobId", requireAuth, requireRagOperator, async (req, res) => {
  try {
    const r = await ragFetch(`/admin/ingest-jobs/${encodeURIComponent(req.params.jobId)}`, {
      method: "GET",
    });
    const text = await r.text();
    if (!r.ok) return res.status(r.status).type("text/plain").send(text);
    res.type("application/json").send(text);
  } catch (e) {
    res.status(502).json({ error: String(e.message || e) });
  }
});

app.post("/api/rag/documents", requireAuth, requireRagOperator, upload.single("file"), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: "Missing file" });
  try {
    const filename = req.file.originalname || "upload.bin";
    const mime = req.file.mimetype || "application/octet-stream";
    const fd = new globalThis.FormData();
    fd.append(
      "file",
      new File([req.file.buffer], filename, { type: mime }),
    );
    const r = await ragFetch("/admin/documents", {
      method: "POST",
      body: fd,
    });
    const text = await r.text();
    if (!r.ok) return res.status(r.status).type("text/plain").send(text);
    res.type("application/json").send(text);
  } catch (e) {
    res.status(502).json({ error: String(e.message || e) });
  }
});

app.delete("/api/rag/documents/:docId", requireAuth, requireRagOperator, async (req, res) => {
  try {
    const r = await ragFetch(`/admin/documents/${encodeURIComponent(req.params.docId)}`, {
      method: "DELETE",
    });
    const text = await r.text();
    if (!r.ok) return res.status(r.status).type("text/plain").send(text);
    res.type("application/json").send(text);
  } catch (e) {
    res.status(502).json({ error: String(e.message || e) });
  }
});

/** --- Static (production) --- */
if (isProd) {
  const dist = path.join(__dirname, "../dist");
  app.use(express.static(dist));
  app.get("*", (req, res, next) => {
    if (req.path.startsWith("/api")) return next();
    res.sendFile(path.join(dist, "index.html"));
  });
}

async function boot() {
  try {
    if (fileStore) {
      await fileStore.ensureDirs();
    }
    await ensureDepartmentsSeeded();
    await ensureDefaultSuperAdmin();
  } catch (e) {
    console.warn("[staff-console] bootstrap:", e?.message || e);
  }
  app.listen(PORT, () => {
    console.log(`[staff-console] listening on :${PORT} (prod=${isProd})`);
  });
}

void boot();
