export function CardGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="h-32 animate-pulse rounded-xl border border-slate-200 bg-white p-5"
        >
          <div className="h-3 w-24 rounded bg-slate-200" />
          <div className="mt-4 h-7 w-16 rounded bg-slate-200" />
          <div className="mt-4 h-3 w-32 rounded bg-slate-100" />
        </div>
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="border-b border-slate-200 bg-slate-50 px-5 py-3">
        <div className="h-3 w-48 animate-pulse rounded bg-slate-200" />
      </div>
      <div className="divide-y divide-slate-100">
        {Array.from({ length: rows }).map((_, index) => (
          <div key={index} className="flex items-center justify-between px-5 py-4">
            <div className="h-4 w-32 animate-pulse rounded bg-slate-200" />
            <div className="h-4 w-24 animate-pulse rounded bg-slate-100" />
            <div className="h-4 w-20 animate-pulse rounded bg-slate-100" />
          </div>
        ))}
      </div>
    </div>
  );
}
