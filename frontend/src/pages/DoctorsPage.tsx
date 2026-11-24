import { useEffect, useMemo, useState } from "react";
import {
  Award,
  CalendarDays,
  Clock,
  Search,
  Stethoscope,
} from "lucide-react";
import { EmptyState } from "../components/common/EmptyState";
import { CardGridSkeleton } from "../components/common/LoadingSkeleton";
import { BookSlotModal } from "../components/doctors/BookSlotModal";
import type {
  AppointmentActionResponse,
  AppointmentBookPayload,
  AvailabilitySlot,
  Doctor,
} from "../types";
import { formatCurrency, formatDateLabel } from "../utils/format";

interface DoctorsPageProps {
  doctors: Doctor[];
  availability: AvailabilitySlot[];
  isLoading: boolean;
  globalSearch: string;
  loadAvailabilityForFilters: (filters?: {
    doctor_id?: number;
    speciality?: string;
    appointment_date?: string;
  }) => Promise<AvailabilitySlot[]>;
  onBookSlot: (
    payload: AppointmentBookPayload
  ) => Promise<AppointmentActionResponse>;
  onNotifySuccess: (title: string, description?: string) => void;
  onNotifyError: (title: string, description?: string) => void;
}

export function DoctorsPage({
  doctors,
  availability,
  isLoading,
  globalSearch,
  loadAvailabilityForFilters,
  onBookSlot,
  onNotifySuccess,
  onNotifyError,
}: DoctorsPageProps) {
  const [localSearch, setLocalSearch] = useState("");
  const [selectedSpeciality, setSelectedSpeciality] = useState("All");
  const [selectedDate, setSelectedDate] = useState("");
  const [filteredSlots, setFilteredSlots] = useState<AvailabilitySlot[] | null>(
    null
  );
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [bookingSlot, setBookingSlot] = useState<AvailabilitySlot | null>(null);

  const specialities = useMemo(() => {
    const unique = Array.from(new Set(doctors.map((d) => d.speciality))).sort();
    return ["All", ...unique];
  }, [doctors]);

  // Dynamically fetch slots from GET /api/availability when speciality or date filter changes
  useEffect(() => {
    if (selectedSpeciality === "All" && !selectedDate) {
      setFilteredSlots(null);
      return;
    }

    let active = true;
    setLoadingSlots(true);
    loadAvailabilityForFilters({
      speciality: selectedSpeciality === "All" ? undefined : selectedSpeciality,
      appointment_date: selectedDate || undefined,
    })
      .then((slots) => {
        if (active) setFilteredSlots(slots);
      })
      .catch((err: unknown) => {
        if (active) {
          onNotifyError(
            "Unable to load slots",
            err instanceof Error ? err.message : "Availability query failed."
          );
        }
      })
      .finally(() => {
        if (active) setLoadingSlots(false);
      });

    return () => {
      active = false;
    };
  }, [selectedSpeciality, selectedDate, loadAvailabilityForFilters, onNotifyError]);

  const effectiveQuery = (localSearch || globalSearch).trim().toLowerCase();

  const filteredDoctors = useMemo(() => {
    return doctors.filter((doc) => {
      const matchesSpeciality =
        selectedSpeciality === "All" || doc.speciality === selectedSpeciality;
      const matchesQuery =
        !effectiveQuery ||
        doc.name.toLowerCase().includes(effectiveQuery) ||
        doc.speciality.toLowerCase().includes(effectiveQuery) ||
        doc.qualification.toLowerCase().includes(effectiveQuery);
      return matchesSpeciality && matchesQuery;
    });
  }, [doctors, selectedSpeciality, effectiveQuery]);

  const activeSlotsSource = filteredSlots ?? availability;

  const slotsByDoctor = useMemo(() => {
    const grouped = new Map<number, AvailabilitySlot[]>();
      for (const slot of activeSlotsSource) {
        if (slot.status !== "available") continue;
        const list = grouped.get(slot.doctor_id) ?? [];
        list.push(slot);
        grouped.set(slot.doctor_id, list);
      }
      return grouped;
}, [activeSlotsSource]);

const handleConfirmBook = async (
  slot: AvailabilitySlot,
  patientPhone: string
) => {
  const res = await onBookSlot({
    patient_phone: patientPhone,
    slot_id: slot.id,
  });
  // Re-run active filtered availability if date/speciality filter is active
  if (selectedSpeciality !== "All" || selectedDate) {
    const updated = await loadAvailabilityForFilters({
      speciality: selectedSpeciality === "All" ? undefined : selectedSpeciality,
      appointment_date: selectedDate || undefined,
    });
    setFilteredSlots(updated);
  }
  onNotifySuccess(
    "Appointment booked",
    `${res.appointment.doctor_name} • ${formatDateLabel(res.appointment.appointment_date)} at ${res.appointment.appointment_time}`
  );
};

return (
  <div className="space-y-6">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h2 className="text-lg font-semibold tracking-tight text-slate-900">
          Medical Specialists
        </h2>
        <p className="text-sm text-slate-500">
          Live SQLite doctor directory and dynamic slot availability. Click any open slot to book.
        </p>
      </div>
      <span className="w-fit rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 tabular-nums">
        {filteredDoctors.length} of {doctors.length} doctors
      </span>
    </div>

    {/* Filters Bar */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200/90 bg-white p-4 shadow-card">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-1 flex-col gap-3 sm:flex-row">
            <div className="relative flex-1 sm:max-w-xs">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={localSearch}
                onChange={(e) => setLocalSearch(e.target.value)}
                placeholder="Filter by name or qualification..."
                className="w-full rounded-lg border border-slate-200 bg-slate-50/70 py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/15"
              />
            </div>

              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  aria-label="Filter available slots by date"
                  className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2 text-sm text-slate-700 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/15"
                />
                {selectedDate ? (
                  <button
                    type="button"
                    onClick={() => setSelectedDate("")}
                    className="text-xs font-medium text-slate-500 hover:text-slate-800"
                  >
                    Clear date
                  </button>
                ) : null}
              </div>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {specialities.map((spec) => {
                const active = selectedSpeciality === spec;
                return (
                  <button
                    key={spec}
                    type="button"
                    onClick={() => setSelectedSpeciality(spec)}
                    className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${active
                        ? "bg-slate-900 text-white"
                        : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                      }`}
                  >
                    {spec}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Doctors Grid */}
        {isLoading ? (
          <CardGridSkeleton count={6} />
        ) : filteredDoctors.length === 0 ? (
          <EmptyState
            icon={Stethoscope}
            title="No matching doctors found"
            description="Try clearing your search term or selecting a different speciality filter."
            actionLabel="Reset Filters"
            onAction={() => {
              setLocalSearch("");
              setSelectedSpeciality("All");
              setSelectedDate("");
            }}
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filteredDoctors.map((doctor) => {
              const doctorSlots = slotsByDoctor.get(doctor.id) ?? [];
              const previewSlots = doctorSlots.slice(0, 6);

              return (
                <article
                  key={doctor.id}
                  className="flex flex-col justify-between rounded-xl border border-slate-200/90 bg-white p-5 shadow-card transition hover:border-slate-300"
                >
                  <div>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <span className="inline-flex items-center rounded-md border border-blue-100 bg-blue-50 px-2 py-0.5 text-[11px] font-semibold text-blue-700">
                          {doctor.speciality}
                        </span>
                        <h3 className="mt-2 text-base font-semibold text-slate-900">
                          {doctor.name}
                        </h3>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {doctor.qualification}
                        </p>
                      </div>

                      <div className="text-right">
                        <p className="text-[11px] font-medium text-slate-400">
                          Fee
                        </p>
                        <p className="text-sm font-semibold text-slate-900 tabular-nums">
                          {formatCurrency(doctor.consultation_fee)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 grid grid-cols-2 gap-2 rounded-lg border border-slate-100 bg-slate-50/80 p-3 text-xs">
                      <div className="flex items-center gap-1.5 text-slate-600">
                        <Award className="h-3.5 w-3.5 text-slate-400" />
                        <span className="tabular-nums">{doctor.experience} yrs exp</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-slate-600">
                        <CalendarDays className="h-3.5 w-3.5 text-slate-400" />
                        <span className="truncate">{doctor.available_days}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 border-t border-slate-100 pt-4">
                    <div className="mb-2 flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-700">
                        Available Slots
                      </span>
                      <span className="font-semibold text-teal-600 tabular-nums">
                        {loadingSlots ? "Loading..." : `${doctorSlots.length} open`}
                      </span>
                    </div>

                    {previewSlots.length === 0 ? (
                      <p className="text-xs text-slate-400">
                        {selectedDate
                          ? `No open slots on ${formatDateLabel(selectedDate)}.`
                          : "No open slots in the current schedule window."}
                      </p>
                    ) : (
                      <div className="flex flex-wrap gap-1.5">
                        {previewSlots.map((slot) => (
                            <button
                          key={slot.id}
                            type="button"
                            onClick={() => setBookingSlot(slot)}
                            className="inline-flex items-center gap-1 rounded-md border border-teal-200/80 bg-teal-50/70 px-2 py-1 text-[11px] font-medium text-teal-800 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-800 tabular-nums"
                            title="Book this appointment slot"
                          >
                            <Clock className="h-3 w-3 text-teal-600" />
                            {formatDateLabel(slot.appointment_date).split(",")[0]} •{" "}
                            {slot.appointment_time}
                        </button>
                    ))}
                  </div>
                  )}
                </div>
              </article>
        );
          })}
      </div>
      )}

      <BookSlotModal
        slot={bookingSlot}
        onClose={() => setBookingSlot(null)}
        onConfirmBook={handleConfirmBook}
      />
    </div>
    );
}
