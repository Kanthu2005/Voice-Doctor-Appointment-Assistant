import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

export interface ToastMessage {
  id: string;
  type: "success" | "error" | "info";
  title: string;
  description?: string;
}

interface ToastContainerProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

const STYLES: Record<
  ToastMessage["type"],
  { border: string; iconBg: string; iconColor: string }
> = {
  success: {
    border: "border-emerald-200 bg-white",
    iconBg: "bg-emerald-50 text-emerald-600",
    iconColor: "text-emerald-600",
  },
  error: {
    border: "border-rose-200 bg-white",
    iconBg: "bg-rose-50 text-rose-600",
    iconColor: "text-rose-600",
  },
  info: {
    border: "border-blue-200 bg-white",
    iconBg: "bg-blue-50 text-blue-600",
    iconColor: "text-blue-600",
  },
};

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2 px-4 sm:px-0"
    >
      <AnimatePresence>
        {toasts.map((toast) => {
          const style = STYLES[toast.type];
          const Icon =
            toast.type === "success"
              ? CheckCircle2
              : toast.type === "error"
                ? AlertCircle
                : Info;

          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.98 }}
              transition={{ duration: 0.16 }}
              className={`pointer-events-auto flex items-start gap-3 rounded-xl border p-3.5 shadow-elevated ${style.border}`}
            >
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${style.iconBg}`}
              >
                <Icon className={`h-4 w-4 ${style.iconColor}`} />
              </div>

              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-slate-900">
                  {toast.title}
                </p>
                {toast.description ? (
                  <p className="mt-0.5 text-xs leading-relaxed text-slate-500">
                    {toast.description}
                  </p>
                ) : null}
              </div>

              <button
                type="button"
                onClick={() => onDismiss(toast.id)}
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                aria-label="Dismiss notification"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
