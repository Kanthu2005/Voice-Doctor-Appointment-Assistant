import type {
  Appointment,
  AppointmentActionResponse,
  AppointmentBookPayload,
  AvailabilitySlot,
  DashboardStats,
  Doctor,
  HealthStatusResponse,
  VoiceStatus,
} from "../types";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

  export const WS_BASE_URL =
    import.meta.env.VITE_WS_BASE_URL?.replace(/\/$/, "") ?? "ws://localhost:8000";

  async function requestJson<T>(
    path: string,
    init?: RequestInit
  ): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      ...init,
    });

    if (!response.ok) {
      let detail = `Request failed (${response.status})`;
      try {
        const errBody = (await response.json()) as { detail?: string };
        if (errBody.detail) {
          detail = errBody.detail;
        }
      } catch {
        // Preserve fallback HTTP status message when body is non-JSON.
      }
      throw new Error(detail);
    }

    return (await response.json()) as T;
  }

  export function fetchHealthStatus(signal?: AbortSignal): Promise<HealthStatusResponse> {
    return requestJson<HealthStatusResponse>("/api/health", { signal });
  }

  export function fetchDashboardStats(signal?: AbortSignal): Promise<DashboardStats> {
    return requestJson<DashboardStats>("/api/dashboard/stats", { signal });
  }

  export function fetchDoctors(
    speciality?: string,
    signal?: AbortSignal
  ): Promise<Doctor[]> {
    const params = new URLSearchParams();
    if (speciality && speciality !== "All") {
      params.set("speciality", speciality);
    }
    const query = params.toString();
    return requestJson<Doctor[]>(`/api/doctors${query ? `?${query}` : ""}`, { signal });
  }

  export function fetchDoctorById(
    doctorId: number,
    signal?: AbortSignal
  ): Promise<Doctor> {
    return requestJson<Doctor>(`/api/doctors/${doctorId}`, { signal });
  }

  export function fetchAvailability(
    filters?: {
      doctor_id?: number;
      doctor_name?: string;
      speciality?: string;
      appointment_date?: string;
    },
    signal?: AbortSignal
  ): Promise<AvailabilitySlot[]> {
    const params = new URLSearchParams();
    if (filters?.doctor_id) params.set("doctor_id", String(filters.doctor_id));
    if (filters?.doctor_name) params.set("doctor_name", filters.doctor_name);
    if (filters?.speciality && filters.speciality !== "All") {
      params.set("speciality", filters.speciality);
    }
    if (filters?.appointment_date) params.set("appointment_date", filters.appointment_date);
    const query = params.toString();
    return requestJson<AvailabilitySlot[]>(
      `/api/availability${query ? `?${query}` : ""}`,
      { signal }
    );
  }

  export function fetchAppointments(
    filters?: {
      patient_phone?: string;
      doctor_id?: number;
      status?: "booked" | "cancelled";
      appointment_date?: string;
    },
    signal?: AbortSignal
  ): Promise<Appointment[]> {
    const params = new URLSearchParams();
    if (filters?.patient_phone) params.set("patient_phone", filters.patient_phone);
    if (filters?.doctor_id) params.set("doctor_id", String(filters.doctor_id));
    if (filters?.status) params.set("status", filters.status);
    if (filters?.appointment_date) params.set("appointment_date", filters.appointment_date);
    const query = params.toString();
    return requestJson<Appointment[]>(
      `/api/appointments${query ? `?${query}` : ""}`,
      { signal }
    );
  }

  export function bookAppointment(
    payload: AppointmentBookPayload
  ): Promise<AppointmentActionResponse> {
    return requestJson<AppointmentActionResponse>("/api/appointments", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  export function cancelAppointment(
    appointmentId: number
  ): Promise<AppointmentActionResponse> {
    return requestJson<AppointmentActionResponse>(
      `/api/appointments/${appointmentId}/cancel`,
      { method: "POST" }
    );
  }

  export function fetchVoiceStatus(signal?: AbortSignal): Promise<VoiceStatus> {
    return requestJson<VoiceStatus>("/api/voice/status", { signal });
  }

  export function getVoiceWebSocketUrl(): string {
    return `${WS_BASE_URL}/ws/voice`;
  }
