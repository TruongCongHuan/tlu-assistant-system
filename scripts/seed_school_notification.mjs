/**
 * Seed một document school_notifications (cần Application Default Credentials).
 *
 *   cd scripts && npm install
 *   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccount.json
 *   node seed_school_notification.mjs
 */
import { initializeApp, applicationDefault } from 'firebase-admin/app';
import { getFirestore, FieldValue } from 'firebase-admin/firestore';

initializeApp({ credential: applicationDefault() });
const db = getFirestore();

const ref = await db.collection('school_notifications').add({
  title: 'Thông báo mẫu (seed)',
  body: 'Tạo bởi scripts/seed_school_notification.mjs — xóa hoặc sửa trên Firebase Console.',
  createdAt: FieldValue.serverTimestamp(),
  link: null,
});

console.log('Created school_notifications/', ref.id);
