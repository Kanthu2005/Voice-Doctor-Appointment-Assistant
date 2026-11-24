import type { AppSettingsConfig } from "../types";

export const DEFAULT_APP_SETTINGS: AppSettingsConfig = {
  clinicName: "CareFlow Medical Clinic",
  supportPhone: "+1 (800) 555-0192",
  vadSensitivity: "standard",
  vadStopSeconds: 0.6,
  requirePhoneConfirmation: true,
  autoRefreshSeconds: 30,
  voicePersona: "Maya — Clinical Receptionist (ElevenLabs)",
  desktopNotifications: true,
};
