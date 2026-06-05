/**
 * Local JSON file persistence for demo mode (STORAGE_BACKEND=file).
 */
import fs from "fs/promises";
import path from "path";
import { randomUUID } from "crypto";
import bcrypt from "bcryptjs";

const DEFAULT_DEPARTMENTS = [
  { id: "co_van", name: "Cố vấn học tập", code: "CVHT" },
  { id: "ct_sv", name: "Phòng Công tác Chính trị Sinh viên", code: "CTSV" },
  { id: "dao_tao", name: "Phòng Đào tạo", code: "DT" },
  { id: "tai_chinh", name: "Phòng Tài chính - Kế toán", code: "TC" },
  { id: "tam_ly", name: "Phòng Tham vấn tâm lý", code: "TVTL" },
];

function nowIso() {
  return new Date().toISOString();
}

function unreadForStaff(messages, staffReadAt) {
  const readMs = staffReadAt ? Date.parse(staffReadAt) : 0;
  return messages.filter(
    (m) =>
      m.senderRole === "student" &&
      Date.parse(m.createdAt || 0) > readMs,
  ).length;
}

function unreadForStudent(messages, studentReadAt) {
  const readMs = studentReadAt ? Date.parse(studentReadAt) : 0;
  return messages.filter(
    (m) =>
      m.senderRole === "staff" &&
      Date.parse(m.createdAt || 0) > readMs,
  ).length;
}

export function createFileStore(dataDir) {
  const root = path.resolve(dataDir);

  async function ensureDirs() {
    const dirs = [
      "chats",
      "chats_meta",
      "notifications",
      "submissions",
      "uploads",
      "feedback",
      "users",
      "audit",
      "departments",
    ];
    for (const d of dirs) {
      await fs.mkdir(path.join(root, d), { recursive: true });
    }
  }

  async function readJson(rel, fallback) {
    const p = path.join(root, rel);
    try {
      const raw = await fs.readFile(p, "utf8");
      return JSON.parse(raw);
    } catch (e) {
      if (e.code === "ENOENT") return fallback;
      throw e;
    }
  }

  async function writeJson(rel, data) {
    const p = path.join(root, rel);
    await fs.mkdir(path.dirname(p), { recursive: true });
    const tmp = `${p}.${randomUUID()}.tmp`;
    await fs.writeFile(tmp, JSON.stringify(data, null, 2), "utf8");
    await fs.rename(tmp, p);
  }

  async function ensureDepartmentsSeeded() {
    const items = await readJson("departments/items.json", null);
    if (items && items.length > 0) return items;
    const seeded = DEFAULT_DEPARTMENTS.map((d) => ({
      ...d,
      createdAt: nowIso(),
    }));
    await writeJson("departments/items.json", seeded);
    return seeded;
  }

  async function ensureDefaultSuperAdmin() {
    const accounts = await readJson("users/staff_accounts.json", []);
    if (accounts.some((a) => a.loginId === "super_admin" && a.active !== false)) {
      return;
    }
    const hash = await bcrypt.hash("123456", 10);
    const id = "staff_super_admin";
    accounts.push({
      id,
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
      createdAt: nowIso(),
      updatedAt: nowIso(),
    });
    await writeJson("users/staff_accounts.json", accounts);
    console.log("[file-store] Seeded super_admin / 123456");
  }

  async function findStaffAccountByLogin(loginRaw) {
    const trimmed = String(loginRaw || "").trim();
    if (!trimmed) return null;
    const accounts = await readJson("users/staff_accounts.json", []);
    const em = trimmed.toLowerCase();
    return (
      accounts.find((a) => a.loginId === trimmed) ||
      accounts.find((a) => (a.email || "").toLowerCase() === em) ||
      null
    );
  }

  async function listUsers(roleFilter = "student") {
    const students = await readJson("users/students.json", []);
    let items = students.map((s) => ({
      id: s.uid || s.id,
      email: s.email ?? null,
      displayName: s.displayName ?? s.fullName ?? null,
      photoUrl: null,
      role: s.role ?? "student",
      studentCode: s.studentCode ?? null,
      fullName: s.fullName ?? null,
      className: s.className ?? null,
      faculty: s.faculty ?? null,
      course: s.course ?? null,
      phone: s.phone ?? null,
      source: s.source ?? "demo",
      syncedAt: s.syncedAt ?? null,
      createdAt: s.createdAt ?? null,
      updatedAt: s.updatedAt ?? null,
    }));
    if (roleFilter !== "all") {
      items = items.filter((u) => (u.role || "student") === roleFilter);
    }
    items.sort((a, b) => (b.updatedAt || "").localeCompare(a.updatedAt || ""));
    return items;
  }

  async function patchUser(uid, patch) {
    const students = await readJson("users/students.json", []);
    const i = students.findIndex((s) => (s.uid || s.id) === uid);
    if (i < 0) {
      students.push({
        uid,
        id: uid,
        role: "student",
        ...patch,
        updatedAt: nowIso(),
        syncedAt: nowIso(),
      });
    } else {
      students[i] = { ...students[i], ...patch, updatedAt: nowIso(), syncedAt: nowIso() };
    }
    await writeJson("users/students.json", students);
  }

  async function listNotifications() {
    const items = await readJson("notifications/items.json", []);
    return [...items].sort((a, b) => (b.createdAt || "").localeCompare(a.createdAt || ""));
  }

  async function createNotification({ title, body, link }) {
    const items = await readJson("notifications/items.json", []);
    const id = randomUUID();
    items.push({
      id,
      title: String(title).trim(),
      body: body != null ? String(body) : "",
      link: link != null && link !== "" ? String(link) : null,
      createdAt: nowIso(),
    });
    await writeJson("notifications/items.json", items);
    return id;
  }

  async function deleteNotification(id) {
    const items = await readJson("notifications/items.json", []);
    const next = items.filter((n) => n.id !== id);
    await writeJson("notifications/items.json", next);
  }

  async function listSubmissions() {
    const dir = path.join(root, "submissions");
    let files = [];
    try {
      files = await fs.readdir(dir);
    } catch {
      return [];
    }
    const items = [];
    for (const f of files.filter((x) => x.endsWith(".json"))) {
      const doc = await readJson(`submissions/${f}`, null);
      if (doc) {
        const attachments = (doc.attachments || []).map((a) => ({
          name: a.name,
          size: a.size,
          storagePath: a.storagePath,
          fileKey: a.storagePath ? path.basename(a.storagePath) : null,
        }));
        items.push({
          id: doc.id,
          title: doc.title,
          details: doc.details,
          source: doc.source,
          studentUid: doc.studentUid ?? null,
          studentEmail: doc.studentEmail ?? null,
          uploadBatchId: doc.uploadBatchId,
          attachmentCount: attachments.length,
          createdAt: doc.createdAt,
          attachments,
        });
      }
    }
    items.sort((a, b) => (b.createdAt || "").localeCompare(a.createdAt || ""));
    return items;
  }

  async function getSubmission(id) {
    return readJson(`submissions/${id}.json`, null);
  }

  async function createSubmission(doc) {
    const id = doc.id || randomUUID();
    const full = { ...doc, id, createdAt: doc.createdAt || nowIso() };
    await writeJson(`submissions/${id}.json`, full);
    return id;
  }

  async function saveUploadFile(submissionId, index, filename, buffer) {
    const safe = filename.replace(/[^\w.\-]/g, "_").replace(/\.\./g, "_");
    const rel = `uploads/${submissionId}/${index}_${safe}`;
    const p = path.join(root, rel);
    await fs.mkdir(path.dirname(p), { recursive: true });
    await fs.writeFile(p, buffer);
    return rel;
  }

  function uploadAbsPath(relPath) {
    return path.join(root, relPath);
  }

  async function listFeedback() {
    const items = await readJson("feedback/items.json", []);
    return [...items].sort((a, b) => (b.createdAt || "").localeCompare(a.createdAt || ""));
  }

  async function createFeedback(entry) {
    const items = await readJson("feedback/items.json", []);
    const id = randomUUID();
    items.push({ id, ...entry, createdAt: nowIso() });
    await writeJson("feedback/items.json", items);
    return id;
  }

  async function appendAudit(entry) {
    const items = await readJson("audit/logs.json", []);
    items.unshift({ id: randomUUID(), at: nowIso(), ...entry });
    await writeJson("audit/logs.json", items.slice(0, 500));
  }

  async function listAuditLogs() {
    const items = await readJson("audit/logs.json", []);
    return items.slice(0, 100);
  }

  async function getThreadMeta(threadId) {
    return readJson(`chats_meta/${threadId}.json`, null);
  }

  async function setThreadMeta(threadId, meta) {
    await writeJson(`chats_meta/${threadId}.json`, meta);
  }

  async function listThreadMessages(threadId) {
    return readJson(`chats/${threadId}.json`, []);
  }

  async function appendThreadMessage(threadId, msg, metaUpdate) {
    const messages = await readJson(`chats/${threadId}.json`, []);
    messages.push(msg);
    await writeJson(`chats/${threadId}.json`, messages);
    if (metaUpdate) {
      const existing = (await getThreadMeta(threadId)) || {};
      await setThreadMeta(threadId, { ...existing, ...metaUpdate });
    }
  }

  async function listChatThreads({ departmentId, limit = 100 } = {}) {
    const metaDir = path.join(root, "chats_meta");
    let files = [];
    try {
      files = await fs.readdir(metaDir);
    } catch {
      return [];
    }
    const items = [];
    for (const f of files.filter((x) => x.endsWith(".json"))) {
      const threadId = f.replace(/\.json$/, "");
      const meta = await readJson(`chats_meta/${threadId}.json`, null);
      if (!meta) continue;
      if (departmentId && meta.departmentId !== departmentId) continue;
      const messages = await listThreadMessages(threadId);
      items.push({
        id: threadId,
        studentUid: meta.studentUid,
        studentEmail: meta.studentEmail ?? null,
        studentName: meta.studentName ?? null,
        departmentId: meta.departmentId,
        departmentTitle: meta.departmentTitle ?? "",
        status: meta.status ?? "open",
        preview: meta.preview ?? "",
        lastMessageAt: meta.lastMessageAt,
        createdAt: meta.createdAt,
        unreadForStaff: unreadForStaff(messages, meta.staffReadAt),
        unreadForStudent: unreadForStudent(messages, meta.studentReadAt),
      });
    }
    items.sort((a, b) => (b.lastMessageAt || "").localeCompare(a.lastMessageAt || ""));
    return items.slice(0, limit);
  }

  async function ensureStudentThread({
    studentUid,
    studentEmail,
    studentName,
    departmentId,
    departmentTitle,
  }) {
    const threadId = `${studentUid}_${departmentId}`;
    let meta = await getThreadMeta(threadId);
    if (!meta) {
      meta = {
        studentUid,
        studentEmail: studentEmail || "",
        departmentId,
        departmentTitle,
        status: "open",
        preview: "",
        createdAt: nowIso(),
        lastMessageAt: nowIso(),
      };
      await setThreadMeta(threadId, meta);
      await writeJson(`chats/${threadId}.json`, []);
    }
    return { threadId, meta };
  }

  async function sendStudentMessage({
    studentUid,
    studentEmail,
    studentName,
    departmentId,
    departmentTitle,
    text,
  }) {
    const { threadId } = await ensureStudentThread({
      studentUid,
      studentEmail,
      studentName,
      departmentId,
      departmentTitle,
    });
    const trimmed = String(text).trim();
    const msg = {
      id: randomUUID(),
      text: trimmed,
      senderUid: studentUid,
      senderRole: "student",
      senderName: studentName || "Sinh viên",
      createdAt: nowIso(),
    };
    await appendThreadMessage(threadId, msg, {
      preview: trimmed.length > 200 ? `${trimmed.slice(0, 200)}…` : trimmed,
      lastMessageAt: nowIso(),
      status: "open",
    });
    return { threadId, messageId: msg.id };
  }

  async function markStaffRead(threadId) {
    const meta = (await getThreadMeta(threadId)) || {};
    await setThreadMeta(threadId, { ...meta, staffReadAt: nowIso() });
  }

  async function markStudentRead(threadId) {
    const meta = (await getThreadMeta(threadId)) || {};
    await setThreadMeta(threadId, { ...meta, studentReadAt: nowIso() });
  }

  async function getThreadWithMessages(threadId) {
    const meta = await getThreadMeta(threadId);
    if (!meta) return null;
    const messages = await listThreadMessages(threadId);
    return {
      thread: {
        id: threadId,
        ...meta,
        unreadForStaff: unreadForStaff(messages, meta.staffReadAt),
        unreadForStudent: unreadForStudent(messages, meta.studentReadAt),
      },
      messages,
    };
  }

  async function sendStaffMessage(threadId, { text, senderUid, senderName }) {
    const meta = await getThreadMeta(threadId);
    if (!meta) return null;
    const trimmed = String(text).trim();
    const msg = {
      id: randomUUID(),
      text: trimmed,
      senderUid,
      senderRole: "staff",
      senderName: senderName || "Cán bộ",
      createdAt: nowIso(),
    };
    await appendThreadMessage(threadId, msg, {
      preview: trimmed.length > 200 ? `${trimmed.slice(0, 200)}…` : trimmed,
      lastMessageAt: nowIso(),
      status: "answered",
    });
    return msg.id;
  }

  async function listStaffAccounts() {
    const accounts = await readJson("users/staff_accounts.json", []);
    return accounts.map((x) => {
      const role =
        x.role === "super_admin" || x.role === "staff" || x.role === "auditor"
          ? x.role
          : x.isSuper
            ? "super_admin"
            : "staff";
      return {
        id: x.id,
        email: x.email,
        loginId: x.loginId ?? null,
        fullName: x.fullName ?? "",
        staffCode: x.staffCode ?? "",
        departmentId: x.departmentId,
        departmentName: x.departmentName ?? "",
        role,
        isSuper: role === "super_admin",
        active: x.active !== false,
        createdAt: x.createdAt ?? null,
        updatedAt: x.updatedAt ?? null,
      };
    });
  }

  async function listStudentUnreadByDepartment(studentUid) {
    const results = [];
    for (const d of DEFAULT_DEPARTMENTS) {
      const threadId = `${studentUid}_${d.id}`;
      const meta = await getThreadMeta(threadId);
      if (!meta) {
        results.push({ departmentId: d.id, departmentTitle: d.name, unread: 0 });
        continue;
      }
      const messages = await listThreadMessages(threadId);
      results.push({
        departmentId: d.id,
        departmentTitle: d.name,
        unread: unreadForStudent(messages, meta.studentReadAt),
      });
    }
    return results;
  }

  async function getStudentProfile(uid) {
    const students = await readJson("users/students.json", []);
    return students.find((s) => (s.uid || s.id) === uid) || null;
  }

  return {
    root,
    ensureDirs,
    ensureDepartmentsSeeded,
    ensureDefaultSuperAdmin,
    findStaffAccountByLogin,
    listUsers,
    patchUser,
    listNotifications,
    createNotification,
    deleteNotification,
    listSubmissions,
    getSubmission,
    createSubmission,
    saveUploadFile,
    uploadAbsPath,
    listFeedback,
    createFeedback,
    appendAudit,
    listAuditLogs,
    getThreadMeta,
    listThreadMessages,
    listChatThreads,
    ensureStudentThread,
    sendStudentMessage,
    sendStaffMessage,
    markStaffRead,
    markStudentRead,
    getThreadWithMessages,
    listStaffAccounts,
    listStudentUnreadByDepartment,
    getStudentProfile,
    readJson,
    writeJson,
  };
}
