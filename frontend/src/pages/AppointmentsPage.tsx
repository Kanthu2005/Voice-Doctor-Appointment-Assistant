import { useMemo, useState } from "react";
import { CalendarCheck, Search, XCircle } from "lucide-react";
import { EmptyState } from "../components/common/EmptyState";
import { TableSkeleton } from "../components/common/LoadingSkeleton";
import { StatusBadge } from "../components/common/StatusBadge";
import type { Appointment, AppointmentActionResponse } from "../types";
import { formatDateLabel, maskPhoneNumber } from "../utils/format";

interface AppointmentsPageProps {
  appointments: Appointment[];
  isLoading: boolean;
  globalSearch: string;
  onCancelAppointment: (
    appointmentId: number
  ) => Promise<AppointmentActionResponse>;
  onNotifySuccess: (title: string, description?: string) => void;
  onNotifyError: (title: string, description?: string) => void;
}

export function AppointmentsPage({
  appointments,
  isLoading,
  globalSearch,
  onCancelAppointment,
  onNotifySuccess,
  onNotifyError,
}: AppointmentsPageProps) {
  const [localSearch, setLocalSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "booked" | "cancelled">("all");
  const [dateFilter, setDateFilter] = useState("");
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  const effectiveQuery = (localSearch || globalSearch).trim().toLowerCase();

  const filteredAppointments = useMemo(() => {
    return appointments.filter((item) => {
      const matchesStatus =
        statusFilter === "all" || item.status === statusFilter;
      const matchesDate =
        !dateFilter || item.appointment_date === dateFilter;
      const matchesQuery =
        !effectiveQuery ||
        String(item.id).includes(effectiveQuery) ||
        item.doctor_name.toLowerCase().includes(effectiveQuery) ||
        item.speciality.toLowerCase().includes(effectiveQuery) ||
        item.patient_phone.toLowerCase().includes(effectiveQuery);
      return matchesStatus && matchesDate && matchesQuery;
    });
  }, [appointments, statusFilter, dateFilter, effectiveQuery]);

  const handleCancel = async (id: number) => {
    setCancellingId(id);
    try {
      const res = await onCancelAppointment(id);
      onNotifySuccess(
        "Appointment cancelled",
        `${res.appointment.doctor_name} slot (${formatDateLabel(res.appointment.appointment_date)} ${res.appointment.appointment_time}) released.`
      );
    } catch (err: unknown) {
        onNotifyError(
          "Cancellation failed",
          err instanceof Error ? err.message : "Unable to cancel appointment."
        );
    } finally {
      setCancellingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-slate-900">
            Appointments Ledger
          </h2>
          <p className="text-sm text-slate-500">
            Live SQLite appointment records with privacy-masked caller phone numbers.
          </p>
        </div>
        <span className="w-fit rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 tabular-nums">
          {filteredAppointments.length} records
        </span>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200/90 bg-white p-4 shadow-card lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-1 flex-col gap-3 sm:flex-row">
          <div className="relative flex-1 sm:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              placeholder="Search ID, doctor, or phone..."
              className="w-full rounded-lg border border-slate-200 bg-slate-50/70 py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/15"
            />
          </div>

          <input
            type="date"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            aria-label="Filter by appointment date"
            className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2 text-sm text-slate-700 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/15"
          />
        </div>

        <div className="flex items-center gap-1.5">
          {(["all", "booked", "cancelled"] as const).map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => setStatusFilter(status)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition ${statusFilter === status
                  ? "bg-slate-900 text-white"
                  : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <TableSkeleton rows={5} />
      ) : filteredAppointments.length === 0 ? (
        <EmptyState
          icon={CalendarCheck}
          title="No appointments match your filters"
          description="Book an appointment via Voice Assistant or the Doctors page, or adjust your active filters."
          actionLabel="Clear Filters"
          onAction={() => {
            setLocalSearch("");
            setStatusFilter("all");
            setDateFilter("");
          }}
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-card">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left">
              <thead className="bg-slate-50/90">
                <tr className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  <th className="px-5 py-3.5">Appointment ID</th>
                  <th className="px-5 py-3.5">Patient Phone</th>
                  <th className="px-5 py-3.5">Doctor</th>
                  <th className="px-5 py-3.5">Date</th>
                  <th className="px-5 py-3.5">Time</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {filteredAppointments.map((appt) => (
                  <tr
                    key={appt.id}
                    className="transition-colors hover:bg-slate-50/70"
                  >
                    <td className="whitespace-nowrap px-5 py-3.5 font-semibold text-slate-900 tabular-nums">
                      #{appt.id}
                    </td>
                    <td className="whitespace-nowrap px-5 py-3.5 font-mono text-xs text-slate-700">
                      {maskPhoneNumber(appt.patient_phone)}
                    </td>
                    <td className="px-5 py-3.5">
                      <p className="font-medium text-slate-900">
                        {appt.doctor_name}
                      </p>
                      <p className="text-xs text-slate-500">{appt.speciality}</p>
                    </td>
                    <td className="whitespace-nowrap px-5 py-3.5 text-slate-700 tabular-nums">
                      {formatDateLabel(appt.appointment_date)}
                    </td>
                    <td className="whitespace-nowrap px-5 py-3.5 text-slate-700 tabular-nums">
                      {appt.appointment_time}
                    </td>
                    <td className="whitespace-nowrap px-5 py-3.5">
                      <StatusBadge status={appt.status} />
                    </td>
                    <td className="whitespace-nowrap px-5 py-3.5 text-right">
                      {appt.status === "booked" ? (
                        <button
                          type="button"
                          onClick={() => void handleCancel(appt.id)}
                          disabled={cancellingId === appt.id}
                          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-rose-600 transition hover:border-rose-200 hover:bg-rose-50 disabled:opacity-50"
                        >
                          <XCircle className="h-3.5 w-3.5" />
                          {cancellingId === appt.id ? "Cancelling..." : "Cancel"}
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
