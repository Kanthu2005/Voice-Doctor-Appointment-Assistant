import { useState } from "react";
import { Calendar, Clock, Phone, Stethoscope, X } from "lucide-react";
import type { AvailabilitySlot } from "../../types";
import { formatCurrency, formatDateLabel } from "../../utils/format";

interface BookSlotModalProps {
  slot: AvailabilitySlot | null;
  onClose: () => void;
  onConfirmBook: (slot: AvailabilitySlot, patientPhone: string) => Promise<void>;
}

export function BookSlotModal({
  slot,
  onClose,
  onConfirmBook,
}: BookSlotModalProps) {
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  if (!slot) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned = phone.trim();
    if (!cleaned) {
      setFormError("Please enter a patient phone number.");
      return;
    }

    setSubmitting(true);
    setFormError(null);
    try {
      await onConfirmBook(slot, cleaned);
      setPhone("");
      onClose();
    } catch (err: unknown) {
      setFormError(
        err instanceof Error ? err.message : "Failed to book appointment."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-[1px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="book-slot-title"
    >
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-elevated">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3
              id="book-slot-title"
              className="text-base font-semibold text-slate-900"
            >
              Book Appointment Slot
            </h3>
            <p className="mt-0.5 text-xs text-slate-500">
              Saves directly to SQLite via <code className="font-mono">POST /api/appointments</code>.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Close modal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 space-y-2 rounded-xl border border-slate-200 bg-slate-50/80 p-3.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-slate-500">
              <Stethoscope className="h-3.5 w-3.5" />
              Doctor
            </span>
            <span className="font-semibold text-slate-900">
              {slot.doctor_name} ({slot.speciality})
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-slate-500">
              <Calendar className="h-3.5 w-3.5" />
              Date
            </span>
            <span className="font-medium text-slate-900 tabular-nums">
              {formatDateLabel(slot.appointment_date)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-slate-500">
              <Clock className="h-3.5 w-3.5" />
              Time &amp; Fee
            </span>
            <span className="font-medium text-slate-900 tabular-nums">
              {slot.appointment_time} • {formatCurrency(slot.consultation_fee)}
            </span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label
              htmlFor="patient-phone-input"
              className="block text-xs font-medium text-slate-700"
            >
              Patient Phone Number
            </label>
            <div className="relative mt-1.5">
              <Phone className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                id="patient-phone-input"
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+919876543210 or 07911123456"
                className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
                autoFocus
              />
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              Stored as a string to preserve leading zeros and country codes.
            </p>
          </div>

          {formError ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
              {formError}
            </div>
          ) : null}

          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-card transition hover:bg-blue-700 disabled:opacity-60"
            >
              {submitting ? "Booking..." : "Confirm Booking"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
