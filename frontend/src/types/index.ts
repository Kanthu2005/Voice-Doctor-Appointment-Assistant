export type NavSection =
  | "overview"
  | "voice"
  | "doctors"
  | "appointments"
  | "settings";

export interface HealthStatusResponse {
  status: string;
  service: string;
  environment: string;
  database: string;
}

export interface DoctorSlot {
  id: number;
  doctor_id: number;
  appointment_date: string;
  appointment_time: string;
  status: "available" | "booked";
}

export interface Doctor {
  id: number;
  name: string;
  speciality: string;
  qualification: string;
  experience: number;
  consultation_fee: number;
  available_days: string;
  slots?: DoctorSlot[];
}

export interface AvailabilitySlot extends DoctorSlot {
  doctor_name: string;
  speciality: string;
  consultation_fee: number;
}

export interface Appointment {
  id: number;
  patient_phone: string;
  doctor_id: number;
  slot_id: number;
  doctor_name: string;
  speciality: string;
  appointment_date: string;
  appointment_time: string;
  status: "booked" | "cancelled";
  created_at: string;
}

export interface AppointmentBookPayload {
  patient_phone: string;
  slot_id?: number;
  doctor_id?: number;
  appointment_date?: string;
  appointment_time?: string;
}

export interface AppointmentActionResponse {
  message: string;
  appointment: Appointment;
}

export interface SpecialityStat {
  speciality: string;
  doctor_count: number;
  available_slots: number;
  booked_appointments: number;
}

export interface DashboardStats {
  total_doctors: number;
  total_slots: number;
  available_slots: number;
  booked_slots: number;
  total_appointments: number;
  active_appointments: number;
  cancelled_appointments: number;
  appointments_today: number;
  speciality_breakdown: SpecialityStat[];
}

export interface VoiceStatus {
  configured: boolean;
  missing_credentials: string[];
  stt_provider: string;
  llm_provider: string;
  tts_provider: string;
  vad_provider: string;
  transport: string;
  websocket_path: string;
}

export type CallState =
  | "idle"
  | "connecting"
  | "connected"
  | "muted"
  | "ending"
  | "ended"
  | "error";

export interface VoiceAppointmentPayload {
  appointment_id: number;
  patient_phone: string;
  doctor_id: number;
  doctor_name: string;
  speciality: string;
  slot_id: number;
  appointment_date: string;
  appointment_time: string;
  status: string;
}

export interface AppointmentConfirmationEvent {
  action: "booked" | "cancelled";
  appointment: VoiceAppointmentPayload;
  receivedAt: string;
}

export type VoiceWebSocketMessage =
  | { type: "status"; state: string }
  | { type: "vad"; speaking: boolean }
  | {
    type: "transcript";
    role: "user" | "assistant";
    text: string;
    final: boolean;
  }
  | {
    type: "appointment_event";
    action: "booked" | "cancelled";
    appointment: VoiceAppointmentPayload;
  }
  | { type: "interruption" }
  | { type: "error"; message: string; fatal?: boolean };

export interface TranscriptEntry {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
  timestamp: string;
  final: boolean;
  toolTag?: string;
}

export interface ActivityItem {
  id: string;
  type: "booked" | "cancelled" | "availability";
  title: string;
  subtitle: string;
  timestamp: string;
}

export interface AppSettingsConfig {
  clinicName: string;
  supportPhone: string;
  vadSensitivity: "standard" | "high" | "conservative";
  vadStopSeconds: number;
  requirePhoneConfirmation: boolean;
  autoRefreshSeconds: number;
  voicePersona: string;
  desktopNotifications: boolean;
}
