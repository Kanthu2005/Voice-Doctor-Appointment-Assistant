import {
  CalendarCheck,
  CalendarX2,
  Clock,
  Phone,
  Stethoscope,
} from "lucide-react";
import type { AppointmentConfirmationEvent } from "../../types";
import { formatDateLabel, maskPhoneNumber } from "../../utils/format";

export function BookingConfirmationCard({
  event,
}: {
  event: AppointmentConfirmationEvent;
}) {
  const { appointment } = event;

  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 shadow-card">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
            <CalendarCheck className="h-4 w-4" />
          </div>
          <div>
            <p className="text-xs font-semibold text-emerald-900">
              Booking Confirmed
            </p>
            <p className="text-[11px] text-emerald-700 tabular-nums">
              Appointment #{appointment.appointment_id} • {event.receivedAt}
            </p>
          </div>
        </div>
        <span className="rounded-full border border-emerald-200 bg-white px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
          Booked
        </span>
      </div>

      <dl className="mt-3 space-y-1.5 border-t border-emerald-200/70 pt-3 text-xs text-slate-700">
        <div className="flex items-center justify-between gap-2">
          <dt className="flex items-center gap-1.5 text-slate-500">
            <Stethoscope className="h-3.5 w-3.5" />
            Doctor
          </dt>
          <dd className="font-medium text-slate-900">
            {appointment.doctor_name} ({appointment.speciality})
          </dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="flex items-center gap-1.5 text-slate-500">
            <Clock className="h-3.5 w-3.5" />
            Schedule
          </dt>
          <dd className="font-medium text-slate-900 tabular-nums">
            {formatDateLabel(appointment.appointment_date)} •{" "}
            {appointment.appointment_time}
          </dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="flex items-center gap-1.5 text-slate-500">
            <Phone className="h-3.5 w-3.5" />
            Caller
          </dt>
          <dd className="font-mono text-[11px] text-slate-800">
            {maskPhoneNumber(appointment.patient_phone)}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function CancellationConfirmationCard({
  event,
}: {
  event: AppointmentConfirmationEvent;
}) {
  const { appointment } = event;

  return (
    <div className="rounded-xl border border-rose-200 bg-rose-50/50 p-4 shadow-card">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-100 text-rose-700">
            <CalendarX2 className="h-4 w-4" />
          </div>
          <div>
            <p className="text-xs font-semibold text-rose-900">
              Appointment Cancelled
            </p>
            <p className="text-[11px] text-rose-700 tabular-nums">
              Appointment #{appointment.appointment_id} • {event.receivedAt}
            </p>
          </div>
        </div>
        <span className="rounded-full border border-rose-200 bg-white px-2 py-0.5 text-[11px] font-semibold text-rose-700">
          Slot Released
        </span>
      </div>

      <dl className="mt-3 space-y-1.5 border-t border-rose-200/70 pt-3 text-xs text-slate-700">
        <div className="flex items-center justify-between gap-2">
          <dt className="flex items-center gap-1.5 text-slate-500">
            <Stethoscope className="h-3.5 w-3.5" />
            Doctor
          </dt>
          <dd className="font-medium text-slate-900">
            {appointment.doctor_name} ({appointment.speciality})
          </dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="flex items-center gap-1.5 text-slate-500">
            <Clock className="h-3.5 w-3.5" />
            Released Slot
          </dt>
          <dd className="font-medium text-slate-900 tabular-nums">
            {formatDateLabel(appointment.appointment_date)} •{" "}
            {appointment.appointment_time}
          </dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="flex items-center gap-1.5 text-slate-500">
            <Phone className="h-3.5 w-3.5" />
            Caller
          </dt>
          <dd className="font-mono text-[11px] text-slate-800">
            {maskPhoneNumber(appointment.patient_phone)}
          </dd>
        </div>
      </dl>
    </div>
  );
}
