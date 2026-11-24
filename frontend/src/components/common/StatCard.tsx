import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  caption: string;
  icon: LucideIcon;
  accent?: "blue" | "teal" | "slate" | "rose";
}

const ACCENT_STYLES: Record<NonNullable<StatCardProps["accent"]>, string> = {
  blue: "bg-blue-50 text-blue-600 border-blue-100",
  teal: "bg-teal-50 text-teal-600 border-teal-100",
  slate: "bg-slate-100 text-slate-700 border-slate-200",
  rose: "bg-rose-50 text-rose-600 border-rose-100",
};

export function StatCard({
  label,
  value,
  caption,
  icon: Icon,
  accent = "blue",
}: StatCardProps) {
  return (
    <div className="rounded-xl border border-slate-200/90 bg-white p-5 shadow-card transition-colors hover:border-slate-300/90">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            {label}
          </p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-900 tabular-nums">
            {value}
          </p>
        </div>
        <div
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${ACCENT_STYLES[accent]}`}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="mt-3 text-xs text-slate-500">{caption}</p>
    </div>
  );
}
