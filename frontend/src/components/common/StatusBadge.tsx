interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

const STATUS_MAP: Record<string, { label: string; classes: string; dot: string }> = {
  booked: {
    label: "Booked",
    classes: "bg-emerald-50 text-emerald-700 border-emerald-200/80",
    dot: "bg-emerald-500",
  },
  available: {
    label: "Available",
    classes: "bg-teal-50 text-teal-700 border-teal-200/80",
    dot: "bg-teal-500",
  },
  cancelled: {
    label: "Cancelled",
    classes: "bg-rose-50 text-rose-700 border-rose-200/80",
    dot: "bg-rose-500",
  },
  idle: {
    label: "Idle",
    classes: "bg-slate-100 text-slate-700 border-slate-200",
    dot: "bg-slate-400",
  },
  connecting: {
    label: "Connecting",
    classes: "bg-amber-50 text-amber-700 border-amber-200",
    dot: "bg-amber-500",
  },
  connected: {
    label: "Connected",
    classes: "bg-teal-50 text-teal-700 border-teal-200",
    dot: "bg-teal-500",
  },
    muted: {
      label: "Muted",
      classes: "bg-amber-50 text-amber-800 border-amber-200",
      dot: "bg-amber-500",
    },
      ending: {
        label: "Ending",
        classes: "bg-slate-100 text-slate-700 border-slate-200",
        dot: "bg-slate-500",
      },
      ended: {
        label: "Ended",
        classes: "bg-slate-100 text-slate-600 border-slate-200",
        dot: "bg-slate-400",
      },
      error: {
        label: "Error",
        classes: "bg-rose-50 text-rose-700 border-rose-200",
        dot: "bg-rose-500",
      },
    };

    export function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
      const key = status.toLowerCase();
const config = STATUS_MAP[key] ?? {
  label: status,
  classes: "bg-slate-100 text-slate-700 border-slate-200",
  dot: "bg-slate-400",
};

const padding = size === "sm" ? "px-2.5 py-0.5 text-xs" : "px-3 py-1 text-xs";

return (
  <span
    className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${padding} ${config.classes}`}
  >
    <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
    {config.label}
  </span>
);
}
