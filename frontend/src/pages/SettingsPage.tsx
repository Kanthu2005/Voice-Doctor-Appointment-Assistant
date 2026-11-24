import { useEffect, useState } from "react";
import { Check, Info, Mic, Save, Server, Shield } from "lucide-react";
import { API_BASE_URL } from "../services/api";
import type {
  AppSettingsConfig,
  HealthStatusResponse,
  VoiceStatus,
} from "../types";

interface SettingsPageProps {
  settings: AppSettingsConfig;
  onUpdateSettings: (next: AppSettingsConfig) => void;
  health: HealthStatusResponse | null;
  voiceStatus: VoiceStatus;
  isLiveBackend: boolean;
}

export function SettingsPage({
  settings,
  onUpdateSettings,
  health,
  voiceStatus,
  isLiveBackend,
}: SettingsPageProps) {
  const [draft, setDraft] = useState<AppSettingsConfig>(settings);
  const [savedBanner, setSavedBanner] = useState(false);

  useEffect(() => {
    setDraft(settings);
  }, [settings]);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateSettings(draft);
    setSavedBanner(true);
    window.setTimeout(() => setSavedBanner(false), 2500);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold tracking-tight text-slate-900">
          System &amp; Voice Settings
        </h2>
        <p className="text-sm text-slate-500">
          Application metadata, Pipecat voice pipeline preferences, and clinic configuration.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Application Info */}
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200/90 bg-white p-5 shadow-card">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-blue-600" />
              <h3 className="text-sm font-semibold text-slate-900">
                Application Information
              </h3>
            </div>

            <dl className="mt-4 space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">Product</dt>
                <dd className="font-medium text-slate-900">CareFlow AI</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">Version</dt>
                <dd className="font-medium text-slate-900 tabular-nums">v0.3.0</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">Backend Mode</dt>
                <dd className="font-medium text-slate-900">
                  {isLiveBackend ? `Live (${health?.environment ?? "dev"})` : "Offline"}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">API Base URL</dt>
                <dd className="max-w-[165px] truncate font-mono text-[11px] text-slate-700">
                  {API_BASE_URL}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">Database</dt>
                <dd className="font-medium text-slate-900">
                  {health ? `SQLite (${health.database})` : "SQLite (Async)"}
                </dd>
              </div>
            </dl>
          </div>

          <div className="rounded-xl border border-slate-200/90 bg-white p-5 shadow-card">
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-teal-600" />
              <h3 className="text-sm font-semibold text-slate-900">
                Voice Providers
              </h3>
            </div>
            <dl className="mt-4 space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">STT Engine</dt>
                <dd className="font-medium text-slate-900">
                  {voiceStatus.stt_provider}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">LLM Engine</dt>
                <dd className="font-medium text-slate-900">
                  {voiceStatus.llm_provider}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">TTS Engine</dt>
                <dd className="font-medium text-slate-900">
                  {voiceStatus.tts_provider}
                </dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">VAD Model</dt>
                <dd className="font-medium text-slate-900">
                  {voiceStatus.vad_provider}
                </dd>
              </div>
            </dl>
          </div>
        </div>

        {/* Editable Configuration Form */}
        <form
          onSubmit={handleSave}
          className="space-y-6 rounded-xl border border-slate-200/90 bg-white p-6 shadow-card lg:col-span-2"
        >
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div className="flex items-center gap-2">
              <Mic className="h-4 w-4 text-blue-600" />
              <h3 className="text-sm font-semibold text-slate-900">
                Voice Assistant &amp; Clinic Configuration
              </h3>
            </div>
            {savedBanner ? (
              <span className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                <Check className="h-3.5 w-3.5" />
                Saved
              </span>
            ) : null}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="clinic-name"
                className="block text-xs font-medium text-slate-700"
              >
                Clinic Display Name
              </label>
              <input
                id="clinic-name"
                type="text"
                value={draft.clinicName}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, clinicName: e.target.value }))
                }
                className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
              />
            </div>

            <div>
              <label
                htmlFor="support-phone"
                className="block text-xs font-medium text-slate-700"
              >
                Clinic Reception Desk Phone
              </label>
              <input
                id="support-phone"
                type="text"
                value={draft.supportPhone}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, supportPhone: e.target.value }))
                }
                className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
              />
            </div>

            <div>
              <label
                htmlFor="voice-persona"
                className="block text-xs font-medium text-slate-700"
              >
                Assistant Voice Persona
              </label>
              <select
                id="voice-persona"
                value={draft.voicePersona}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, voicePersona: e.target.value }))
                }
                className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
              >
                <option value="Maya — Clinical Receptionist (ElevenLabs)">
                  Maya — Clinical Receptionist (ElevenLabs)
                </option>
                <option value="Aria — Calm Triage Specialist (ElevenLabs)">
                  Aria — Calm Triage Specialist (ElevenLabs)
                </option>
              </select>
            </div>

            <div>
              <label
                htmlFor="vad-sensitivity"
                className="block text-xs font-medium text-slate-700"
              >
                Silero VAD Turn Sensitivity
              </label>
              <select
                id="vad-sensitivity"
                value={draft.vadSensitivity}
                onChange={(e) =>
                  setDraft((prev) => ({
                    ...prev,
                    vadSensitivity: e.target.value as AppSettingsConfig["vadSensitivity"],
                  }))
                }
                className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
              >
                <option value="standard">Standard (0.6s silence)</option>
                <option value="high">Responsive (0.4s silence)</option>
                <option value="conservative">Patient (0.9s silence)</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="auto-refresh"
                className="block text-xs font-medium text-slate-700"
              >
                Dashboard Auto-Refresh
              </label>
              <select
                id="auto-refresh"
                value={draft.autoRefreshSeconds}
                onChange={(e) =>
                  setDraft((prev) => ({
                    ...prev,
                    autoRefreshSeconds: Number(e.target.value),
                  }))
                }
                className="mt-1.5 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/15"
              >
                <option value={0}>Manual only</option>
                <option value={15}>Every 15 seconds</option>
                <option value={30}>Every 30 seconds</option>
                <option value={60}>Every 60 seconds</option>
              </select>
            </div>
          </div>

          <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/80 p-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-start gap-2.5">
                <Shield className="mt-0.5 h-4 w-4 text-teal-600" />
                <div>
                  <p className="text-xs font-semibold text-slate-900">
                    Mandatory Phone Readback Confirmation
                  </p>
                  <p className="text-xs text-slate-500">
                    Enforces caller phone confirmation before booking or cancelling appointments.
                  </p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={draft.requirePhoneConfirmation}
                onChange={(e) =>
                  setDraft((prev) => ({
                    ...prev,
                    requirePhoneConfirmation: e.target.checked,
                  }))
                }
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-center justify-between gap-4 border-t border-slate-200/80 pt-3">
              <div>
                <p className="text-xs font-semibold text-slate-900">
                  Real-time Dashboard Notifications
                </p>
                <p className="text-xs text-slate-500">
                  Highlight incoming bookings and cancellations in the topbar feed.
                </p>
              </div>
              <input
                type="checkbox"
                checked={draft.desktopNotifications}
                onChange={(e) =>
                  setDraft((prev) => ({
                    ...prev,
                    desktopNotifications: e.target.checked,
                  }))
                }
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white shadow-card transition hover:bg-slate-800"
            >
              <Save className="h-3.5 w-3.5" />
              Save Configuration
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
