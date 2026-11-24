import {
  CalendarCheck,
  LayoutDashboard,
  Mic,
  Settings,
  Stethoscope,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { NavSection } from "../../types";

interface NavItem {
  id: NavSection;
  label: string;
  icon: LucideIcon;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "voice", label: "Voice Assistant", icon: Mic, badge: "AI" },
  { id: "doctors", label: "Doctors", icon: Stethoscope },
  { id: "appointments", label: "Appointments", icon: CalendarCheck },
  { id: "settings", label: "Settings", icon: Settings },
];

interface SidebarProps {
  activeSection: NavSection;
  onSelect: (section: NavSection) => void;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
  isLiveBackend: boolean;
  voiceConfigured: boolean;
}

export function Sidebar({
  activeSection,
  onSelect,
  isOpenMobile,
  onCloseMobile,
  isLiveBackend,
  voiceConfigured,
}: SidebarProps) {
  const handlePick = (id: NavSection) => {
    onSelect(id);
    onCloseMobile();
  };

  return (
    <>
      {isOpenMobile ? (
        <div
          className="fixed inset-0 z-30 bg-slate-900/30 backdrop-blur-[1px] lg:hidden"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      ) : null}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform duration-200 lg:static lg:translate-x-0 ${isOpenMobile ? "translate-x-0" : "-translate-x-full"
          }`}
      >
        <div className="flex h-16 items-center justify-between border-b border-slate-200 px-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white">
              <Stethoscope className="h-4 w-4 text-teal-400" />
            </div>
            <div>
              <span className="block text-sm font-semibold tracking-tight text-slate-900">
                CareFlow AI
              </span>
              <span className="block text-[11px] font-medium text-slate-500">
                Clinical Scheduling
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onCloseMobile}
            className="rounded-md p-1 text-slate-500 hover:bg-slate-100 lg:hidden"
            aria-label="Close navigation"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Primary">
          <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Workspace
          </p>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = activeSection === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => handlePick(item.id)}
                className={`group flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors ${active
                    ? "bg-blue-50/90 text-blue-700"
                    : "text-slate-600 hover:bg-slate-100/80 hover:text-slate-900"
                  }`}
              >
                <span className="flex items-center gap-2.5">
                  <Icon
                    className={`h-4 w-4 transition-colors ${active
                        ? "text-blue-600"
                        : "text-slate-400 group-hover:text-slate-600"
                      }`}
                  />
                  {item.label}
                </span>
                {item.badge ? (
                  <span
                    className={`rounded-md px-1.5 py-0.5 text-[10px] font-semibold ${active
                        ? "bg-blue-100 text-blue-700"
                        : "bg-teal-50 text-teal-700"
                      }`}
                  >
                    {item.badge}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>

        <div className="border-t border-slate-200 p-4">
          <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-700">API Connection</span>
              <span className="inline-flex items-center gap-1.5 font-medium text-slate-700">
                <span
                  className={`h-2 w-2 rounded-full ${
                    isLiveBackend ? "bg-emerald-500" : "bg-rose-500"
                  }`}
                />
                {isLiveBackend ? "Connected" : "Offline"}
              </span>
            </div>
            <p className="mt-1.5 text-[11px] leading-relaxed text-slate-500">
              {!isLiveBackend
                ? "Start FastAPI backend on port 8000."
                : voiceConfigured
                  ? "Pipecat + Gemini + ElevenLabs ready."
                  : "SQLite live. Set voice API keys in backend/.env."}
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
