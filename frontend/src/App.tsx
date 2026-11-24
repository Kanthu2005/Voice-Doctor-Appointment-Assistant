import { useCallback, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, RefreshCw } from "lucide-react";
import { ToastContainer, type ToastMessage } from "./components/common/Toast";
import { Sidebar } from "./components/layout/Sidebar";
import { Topbar } from "./components/layout/Topbar";
import { DEFAULT_APP_SETTINGS } from "./config/defaults";
import { useClinicData } from "./hooks/useClinicData";
import { useVoiceAssistant } from "./hooks/useVoiceAssistant";
import { AppointmentsPage } from "./pages/AppointmentsPage";
import { DoctorsPage } from "./pages/DoctorsPage";
import { OverviewPage } from "./pages/OverviewPage";
import { SettingsPage } from "./pages/SettingsPage";
import { VoiceAssistantPage } from "./pages/VoiceAssistantPage";
import type { ActivityItem, AppSettingsConfig, NavSection } from "./types";
import { formatDateLabel, maskPhoneNumber } from "./utils/format";

export function App() {
  const [activeSection, setActiveSection] = useState<NavSection>("overview");
  const [searchQuery, setSearchQuery] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [appSettings, setAppSettings] =
    useState<AppSettingsConfig>(DEFAULT_APP_SETTINGS);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const pushToast = useCallback(
    (type: ToastMessage["type"], title: string, description?: string) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
      setToasts((prev) => [...prev.slice(-3), { id, type, title, description }]);
      window.setTimeout(() => {
        setToasts((prev) => prev.filter((item) => item.id !== id));
      }, 5000);
    },
    []
  );

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const notifySuccess = useCallback(
    (title: string, description?: string) => pushToast("success", title, description),
    [pushToast]
  );

  const notifyError = useCallback(
    (title: string, description?: string) => pushToast("error", title, description),
    [pushToast]
  );

  const clinicData = useClinicData(appSettings.autoRefreshSeconds);

  const voiceUI = useVoiceAssistant(
    (event) => {
      void clinicData.refresh(true);
      if (event.action === "booked") {
        notifySuccess(
          "Voice AI booked appointment",
          `${event.appointment.doctor_name} • ${formatDateLabel(event.appointment.appointment_date)} at ${event.appointment.appointment_time}`
        );
      } else {
        notifySuccess(
          "Voice AI cancelled appointment",
          `Appointment #${event.appointment.appointment_id} cancelled and slot released.`
        );
      }
    },
    (message) => {
      notifyError("Voice pipeline error", message);
    }
  );

  const topbarNotifications: ActivityItem[] = useMemo(() => {
    return clinicData.appointments.slice(0, 5).map((appt) => ({
      id: `notif-${appt.id}`,
      type: appt.status,
      title:
        appt.status === "booked"
          ? `Appointment #${appt.id} booked`
          : `Appointment #${appt.id} cancelled`,
      subtitle: `${appt.doctor_name} • ${formatDateLabel(appt.appointment_date)}, ${appt.appointment_time} • ${maskPhoneNumber(appt.patient_phone)}`,
      timestamp: appt.status === "booked" ? "Active" : "Slot released",
    }));
  }, [clinicData.appointments]);

  const handleGlobalSearch = (value: string) => {
    setSearchQuery(value);
    if (
      value.trim().length > 0 &&
      activeSection !== "doctors" &&
      activeSection !== "appointments"
    ) {
      setActiveSection("doctors");
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      <Sidebar
        activeSection={activeSection}
        onSelect={setActiveSection}
        isOpenMobile={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        isLiveBackend={clinicData.isLiveBackend}
        voiceConfigured={clinicData.voiceStatus.configured}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          activeSection={activeSection}
          searchQuery={searchQuery}
          onSearchChange={handleGlobalSearch}
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
          notifications={topbarNotifications}
          onNavigate={setActiveSection}
        />

        <main className="mx-auto w-full max-w-7xl flex-1 space-y-4 p-4 sm:p-6">
          {clinicData.errorMessage ? (
            <div className="flex flex-col gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-800 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                <div>
                  <p className="font-semibold">Backend Connection Error</p>
                  <p className="mt-0.5">{clinicData.errorMessage}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => void clinicData.refresh()}
                className="inline-flex w-fit items-center gap-1.5 rounded-lg border border-rose-200 bg-white px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-100"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry Connection
              </button>
            </div>
          ) : null}

          <AnimatePresence mode="wait">
            <motion.div
              key={activeSection}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.16, ease: "easeOut" }}
            >
              {activeSection === "overview" ? (
                <OverviewPage
                  stats={clinicData.stats}
                  appointments={clinicData.appointments}
                  isLoading={clinicData.isLoading}
                  isRefreshing={clinicData.isRefreshing}
                  onRefresh={() => void clinicData.refresh(true)}
                  onNavigate={setActiveSection}
                />
              ) : null}

              {activeSection === "voice" ? (
                <VoiceAssistantPage
                  voiceUI={voiceUI}
                  voiceStatus={clinicData.voiceStatus}
                  isLiveBackend={clinicData.isLiveBackend}
                />
              ) : null}

              {activeSection === "doctors" ? (
                <DoctorsPage
                  doctors={clinicData.doctors}
                  availability={clinicData.availability}
                  isLoading={clinicData.isLoading}
                  globalSearch={searchQuery}
                  loadAvailabilityForFilters={
                    clinicData.loadAvailabilityForFilters
                  }
                  onBookSlot={clinicData.handleBookAppointment}
                  onNotifySuccess={notifySuccess}
                  onNotifyError={notifyError}
                />
              ) : null}

              {activeSection === "appointments" ? (
                <AppointmentsPage
                  appointments={clinicData.appointments}
                  isLoading={clinicData.isLoading}
                  globalSearch={searchQuery}
                  onCancelAppointment={clinicData.handleCancelAppointment}
                  onNotifySuccess={notifySuccess}
                  onNotifyError={notifyError}
                />
              ) : null}

              {activeSection === "settings" ? (
                <SettingsPage
                  settings={appSettings}
                  onUpdateSettings={(next) => {
                    setAppSettings(next);
                    notifySuccess("Settings updated", "Clinic preferences saved.");
                  }}
                  health={clinicData.health}
                  voiceStatus={clinicData.voiceStatus}
                  isLiveBackend={clinicData.isLiveBackend}
                />
              ) : null}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default App;
