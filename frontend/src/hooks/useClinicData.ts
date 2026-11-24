import { useCallback, useEffect, useState } from "react";
import {
  bookAppointment as bookAppointmentApi,
  cancelAppointment as cancelAppointmentApi,
  fetchAppointments,
  fetchAvailability,
  fetchDashboardStats,
  fetchDoctors,
  fetchHealthStatus,
  fetchVoiceStatus,
} from "../services/api";
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

const EMPTY_STATS: DashboardStats = {
  total_doctors: 0,
  total_slots: 0,
  available_slots: 0,
  booked_slots: 0,
  total_appointments: 0,
  active_appointments: 0,
  cancelled_appointments: 0,
  appointments_today: 0,
  speciality_breakdown: [],
};

const DEFAULT_VOICE_STATUS: VoiceStatus = {
  configured: false,
  missing_credentials: [],
  stt_provider: "elevenlabs_realtime",
  llm_provider: "google_gemini",
  tts_provider: "elevenlabs",
  vad_provider: "silero",
  transport: "fastapi_websocket",
  websocket_path: "/ws/voice",
};

export interface ClinicDataState {
  doctors: Doctor[];
  availability: AvailabilitySlot[];
  appointments: Appointment[];
  stats: DashboardStats;
  voiceStatus: VoiceStatus;
  health: HealthStatusResponse | null;
  isLoading: boolean;
  isRefreshing: boolean;
  isLiveBackend: boolean;
  errorMessage: string | null;
  refresh: (silent?: boolean) => Promise<void>;
  loadAvailabilityForFilters: (filters?: {
    doctor_id?: number;
    speciality?: string;
    appointment_date?: string;
  }) => Promise<AvailabilitySlot[]>;
  handleBookAppointment: (
    payload: AppointmentBookPayload
  ) => Promise<AppointmentActionResponse>;
  handleCancelAppointment: (
    appointmentId: number
  ) => Promise<AppointmentActionResponse>;
}

  export function useClinicData(autoRefreshSeconds = 0): ClinicDataState {
    const [doctors, setDoctors] = useState<Doctor[]>([]);
    const [availability, setAvailability] = useState<AvailabilitySlot[]>([]);
    const [appointments, setAppointments] = useState<Appointment[]>([]);
    const [stats, setStats] = useState<DashboardStats>(EMPTY_STATS);
    const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>(DEFAULT_VOICE_STATUS);
    const [health, setHealth] = useState<HealthStatusResponse | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
    const [isLiveBackend, setIsLiveBackend] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

        const loadData = useCallback(
          async (silent = false, signal?: AbortSignal) => {
            if (silent) {
              setIsRefreshing(true);
            } else {
              setIsLoading(true);
            }

              try {
                const [healthRes, docsRes, availRes, apptsRes, statsRes, voiceRes] =
                  await Promise.all([
                    fetchHealthStatus(signal),
                    fetchDoctors(undefined, signal),
                    fetchAvailability(undefined, signal),
                    fetchAppointments(undefined, signal),
                    fetchDashboardStats(signal),
                    fetchVoiceStatus(signal),
                  ]);

                setHealth(healthRes);
                setDoctors(docsRes);
                setAvailability(availRes);
                setAppointments(apptsRes);
                setStats(statsRes);
                setVoiceStatus(voiceRes);
                setIsLiveBackend(true);
                setErrorMessage(null);
              } catch (err: unknown) {
                if (err instanceof DOMException && err.name === "AbortError") {
                  return;
                }
                setIsLiveBackend(false);
                setHealth(null);
                setErrorMessage(
                  err instanceof Error
                    ? `Backend API connection failed: ${err.message}`
                    : "Unable to reach the FastAPI backend."
                );
              } finally {
                setIsLoading(false);
                setIsRefreshing(false);
              }
  },
  []
  );

  useEffect(() => {
    const controller = new AbortController();
    void loadData(false, controller.signal);
    return () => controller.abort();
  }, [loadData]);

        useEffect(() => {
          if (!autoRefreshSeconds || autoRefreshSeconds <= 0) return;
          const interval = window.setInterval(() => {
            void loadData(true);
          }, autoRefreshSeconds * 1000);
          return () => window.clearInterval(interval);
        }, [autoRefreshSeconds, loadData]);

        const loadAvailabilityForFilters = useCallback(
          async (filters?: {
            doctor_id?: number;
            speciality?: string;
            appointment_date?: string;
          }) => {
            const slots = await fetchAvailability(filters);
            if (!filters?.doctor_id && !filters?.speciality && !filters?.appointment_date) {
              setAvailability(slots);
            }
            return slots;
          },
          []
        );

        const handleBookAppointment = useCallback(
          async (payload: AppointmentBookPayload) => {
            const result = await bookAppointmentApi(payload);
            await loadData(true);
            return result;
          },
          [loadData]
        );

        const handleCancelAppointment = useCallback(
          async (appointmentId: number) => {
            const result = await cancelAppointmentApi(appointmentId);
            await loadData(true);
            return result;
          },
          [loadData]
        );

        return {
          doctors,
          availability,
          appointments,
          stats,
          voiceStatus,
          health,
          isLoading,
          isRefreshing,
          isLiveBackend,
          errorMessage,
          refresh: (silent = false) => loadData(silent),
          loadAvailabilityForFilters,
          handleBookAppointment,
          handleCancelAppointment,
        };
      }
