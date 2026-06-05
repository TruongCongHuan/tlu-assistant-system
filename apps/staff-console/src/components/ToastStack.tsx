import { useEffect, useRef } from "react";
import { X } from "lucide-react";

export type ToastItem = {
  id: string;
  title: string;
  body: string;
};

export function ToastStack({
  toasts,
  onDismiss,
}: {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}) {
  if (toasts.length === 0) return null;
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex max-w-sm flex-col gap-2">
      {toasts.map((t) => (
        <ToastCard key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function ToastCard({
  toast,
  onDismiss,
}: {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}) {
  const onDismissRef = useRef(onDismiss);
  onDismissRef.current = onDismiss;

  useEffect(() => {
    const timer = setTimeout(() => onDismissRef.current(toast.id), 6000);
    return () => clearTimeout(timer);
  }, [toast.id]);

  return (
    <div className="pointer-events-auto relative rounded-xl border border-brand-200 bg-white py-3 pl-4 pr-10 shadow-lg ring-1 ring-brand-100">
      <button
        type="button"
        aria-label="Đóng"
        onClick={() => onDismiss(toast.id)}
        className="absolute right-2 top-2 rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
      >
        <X className="h-4 w-4" />
      </button>
      <div className="text-sm font-semibold text-slate-900">{toast.title}</div>
      <div className="mt-1 line-clamp-3 text-sm text-slate-600">{toast.body}</div>
    </div>
  );
}
