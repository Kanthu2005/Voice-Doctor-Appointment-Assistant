import {
  ArrowUpRight,
  CalendarCheck,
  CalendarClock,
  CalendarX2,
  Mic,
  RefreshCw,
  Stethoscope,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EmptyState } from "../components/common/EmptyState";
import { CardGridSkeleton } from "../components/common/LoadingSkeleton";
import { StatCard } from "../components/common/StatCard";
import { StatusBadge } from "../components/common/StatusBadge";
import type { Appointment, DashboardStats, NavSection } from "../types";
import { formatDateLabel, maskPhoneNumber } from "../utils/format";

interface OverviewPageProps {
  stats: DashboardStats;
  appointments: Appointment[];
  isLoading: boolean;
  isRefreshing: boolean;
  onRefresh: () => void;
  onNavigate: (section: NavSection) => void;
}

export function OverviewPage({
  stats,
  appointments,
  isLoading,
  isRefreshing,
  onRefresh,
  onNavigate,
}: OverviewPageProps) {
  const recentItems = appointments.slice(0, 5);

  const specialityChartData = stats.speciality_breakdown.map((item) => ({
    name: item.speciality.replace("General Medicine", "Gen. Med"),
    Available: item.available_slots,
    Booked: item.booked_appointments,
  }));

  // Aggregate real appointments by date for the secondary chart
  const dateMap = new Map<string, { date: string; Booked: number; Cancelled: number }>();
  for (const appt of appointments) {
    const existing = dateMap.get(appt.appointment_date) ?? {
      date: formatDateLabel(appt.appointment_date).split(",")[0],
      Booked: 0,
      Cancelled: 0,
    };
    if (appt.status === "booked") {
      existing.Booked += 1;
    } else {
      existing.Cancelled += 1;
    }
    dateMap.set(appt.appointment_date, existing);
  }
  const dateTrendData = Array.from(dateMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, value]) => value);

  return (
    <div className="space-y-6">
      {/* Header row */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-slate-900">
            Operations Summary
          </h2>
          <p className="text-sm text-slate-500">
            Live SQLite metrics across doctors, appointment slots, and voice bookings.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={onRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-card transition hover:bg-slate-50 disabled:opacity-60"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${isLoading || isRefreshing ? "animate-spin" : ""}`}
            />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => onNavigate("voice")}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-2 text-xs font-medium text-white shadow-card transition hover:bg-blue-700"
          >
            <Mic className="h-3.5 w-3.5" />
            Open Voice Assistant
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      {isLoading ? (
        <CardGridSkeleton count={4} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Total Doctors"
            value={stats.total_doctors}
            caption={`${stats.speciality_breakdown.length} active specialities`}
            icon={Stethoscope}
            accent="blue"
          />
          <StatCard
            label="Total Appointments"
            value={stats.total_appointments}
            caption={`${stats.active_appointments} active • ${stats.appointments_today} today`}
            icon={CalendarCheck}
            accent="slate"
          />
          <StatCard
            label="Available Slots"
            value={stats.available_slots}
            caption={`Out of ${stats.total_slots} total scheduled slots`}
            icon={CalendarClock}
            accent="teal"
          />
          <StatCard
            label="Cancelled Appointments"
            value={stats.cancelled_appointments}
            caption="Released slots automatically reopened"
            icon={CalendarX2}
            accent="rose"
          />
        </div>
      )}

      {/* Analytics + Recent Activity */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Appointment Analytics (Recharts backed by live SQLite data) */}
        <div className="rounded-xl border border-slate-200/90 bg-white p-5 shadow-card lg:col-span-2">
          <div className="mb-5 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Appointment &amp; Capacity Analytics
              </h3>
              <p className="text-xs text-slate-500">
                Live slot capacity and active bookings grouped by medical speciality
              </p>
            </div>
            <button
              type="button"
              onClick={() => onNavigate("doctors")}
              className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700"
            >
              View doctors
              <ArrowUpRight className="h-3.5 w-3.5" />
            </button>
          </div>

              {specialityChartData.length === 0 ? (
                <EmptyState
                  icon={Stethoscope}
                  title="No capacity metrics available"
                  description="Connect to the FastAPI backend to load live SQLite speciality metrics."
                />
              ) : (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={specialityChartData}
                      margin={{ top: 8, right: 8, left: -16, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                      <XAxis
                        dataKey="name"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#64748B", fontSize: 11 }}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#64748B", fontSize: 12 }}
                      />
                      <Tooltip
                        cursor={{ fill: "#F1F5F9" }}
                        contentStyle={{
                          backgroundColor: "#FFFFFF",
                          borderColor: "#E2E8F0",
                          borderRadius: "10px",
                          fontSize: "12px",
                          boxShadow: "0 4px 12px rgba(15,23,42,0.06)",
                        }}
                      />
                      <Legend
                        iconType="circle"
                        iconSize={8}
                        wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }}
                      />
                      <Bar
                        dataKey="Available"
                        name="Available Slots"
                        fill="#0D9488"
                        radius={[4, 4, 0, 0]}
                        barSize={20}
                      />
                      <Bar
                        dataKey="Booked"
                        name="Booked Appointments"
                        fill="#2563EB"
                        radius={[4, 4, 0, 0]}
                        barSize={20}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Appointments by Date */}
              <div className="mt-6 border-t border-slate-100 pt-5">
                <div className="mb-3 flex items-center justify-between">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Appointments by Scheduled Date
                  </h4>
                  <span className="text-[11px] text-slate-400 tabular-nums">
                    {appointments.length} total records
                  </span>
                </div>

                {dateTrendData.length === 0 ? (
                  <p className="py-6 text-center text-xs text-slate-400">
                    No appointments recorded yet. Book via Voice Assistant or Doctors page to see date trends.
                  </p>
                ) : (
                  <div className="h-44 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={dateTrendData}
                        margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                        <XAxis
                          dataKey="date"
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "#64748B", fontSize: 11 }}
                        />
                        <YAxis
                          allowDecimals={false}
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "#64748B", fontSize: 11 }}
                        />
                        <Tooltip
                          cursor={{ fill: "#F8FAFC" }}
                          contentStyle={{
                            backgroundColor: "#FFFFFF",
                            borderColor: "#E2E8F0",
                            borderRadius: "10px",
                            fontSize: "12px",
                          }}
                        />
                        <Bar
                          dataKey="Booked"
                          fill="#0F172A"
                          radius={[4, 4, 0, 0]}
                          barSize={20}
                        />
                        <Bar
                          dataKey="Cancelled"
                          fill="#E11D48"
                          radius={[4, 4, 0, 0]}
                          barSize={20}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            </div>

            {/* Recent Activity */}
            <div className="rounded-xl border border-slate-200/90 bg-white p-5 shadow-card">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    Recent Activity
                  </h3>
                  <p className="text-xs text-slate-500">Latest SQLite appointment events</p>
                </div>
                <button
                  type="button"
                  onClick={() => onNavigate("appointments")}
                  className="text-xs font-medium text-blue-600 hover:text-blue-700"
                >
                  View all
                </button>
              </div>

                        {recentItems.length === 0 ? (
                          <EmptyState
                            icon={CalendarCheck}
                            title="No recent appointments"
                            description="Bookings and cancellations made through the Voice Assistant or REST API will appear here."
                            actionLabel="Start Voice Call"
                            onAction={() => onNavigate("voice")}
                          />
                        ) : (
                          <div className="divide-y divide-slate-100">
                            {recentItems.map((appt) => (
                <div key={appt.id} className="py-3.5 first:pt-1 last:pb-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-semibold text-slate-900">
                      {appt.status === "booked"
                        ? `${appt.speciality} appointment booked`
                        : `${appt.speciality} appointment cancelled`}
                    </p>
                    <StatusBadge status={appt.status} />
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500">
                    {appt.doctor_name} • {formatDateLabel(appt.appointment_date)},{" "}
                    {appt.appointment_time} • {maskPhoneNumber(appt.patient_phone)}
                  </p>
                  <p className="mt-1.5 text-[11px] font-medium text-slate-400 tabular-nums">
                    Appointment #{appt.id}
                  </p>
                </div>
              ))}
                  </div>
                )}
              </div>
            </div>
          </div>
          );
}
