import { useState } from "react";
import {
  Activity,
  Bell,
  ChevronDown,
  Menu,
  Search,
  UserCheck,
} from "lucide-react";
import type { ActivityItem, NavSection } from "../../types";

interface TopbarProps {
  activeSection: NavSection;
  searchQuery: string;
  onSearchChange: (value: string) => void;
  onOpenMobileMenu: () => void;
  notifications: ActivityItem[];
  onNavigate: (section: NavSection) => void;
}

const SECTION_TITLES: Record<NavSection, string> = {
  overview: "Clinic Overview",
  voice: "Voice AI Receptionist",
  doctors: "Doctors & Schedules",
  appointments: "Appointments",
  settings: "System Settings",
};

export function Topbar({
  activeSection,
  searchQuery,
  onSearchChange,
  onOpenMobileMenu,
  notifications,
  onNavigate,
}: TopbarProps) {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-4 border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-4 w-4" />
        </button>

        {/* Mobile/Compact Brand Logo + Active Section */}
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-600 text-white lg:hidden">
            <Activity className="h-4 w-4" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-900 sm:text-base">
              {SECTION_TITLES[activeSection]}
            </h1>
          </div>
        </div>
      </div>

      {/* Global Search */}
      <div className="hidden max-w-md flex-1 md:block">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search doctors, specialities, or appointment IDs..."
            className="w-full rounded-lg border border-slate-200 bg-slate-50/80 py-1.5 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/15"
          />
        </div>
      </div>

      {/* Right Actions: Notifications & Profile */}
      <div className="flex items-center gap-2">
        <div className="relative">
          <button
            type="button"
            onClick={() => {
              setShowNotifications((prev) => !prev);
              setShowProfile(false);
            }}
            className="relative flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
            {notifications.length > 0 ? (
              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-teal-500" />
            ) : null}
          </button>

          {showNotifications ? (
            <div className="absolute right-0 mt-2 w-80 rounded-xl border border-slate-200 bg-white p-2 shadow-elevated">
              <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2">
                <span className="text-xs font-semibold text-slate-900">
                  Clinic Notifications
                </span>
                <span className="text-[11px] font-medium text-teal-600">
                  {notifications.length} recent
                </span>
              </div>
              <div className="max-h-64 divide-y divide-slate-100 overflow-y-auto">
                {notifications.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      setShowNotifications(false);
                      onNavigate("appointments");
                    }}
                    className="w-full rounded-lg px-3 py-2.5 text-left transition hover:bg-slate-50"
                  >
                    <p className="text-xs font-medium text-slate-900">
                      {item.title}
                    </p>
                    <p className="mt-0.5 text-[11px] text-slate-500">
                      {item.subtitle}
                    </p>
                    <p className="mt-1 text-[10px] text-slate-400">
                      {item.timestamp}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <div className="relative">
          <button
            type="button"
            onClick={() => {
              setShowProfile((prev) => !prev);
              setShowNotifications(false);
            }}
            className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white py-1.5 pl-2 pr-2.5 text-left transition hover:bg-slate-50"
          >
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-slate-900 text-[11px] font-semibold text-white">
              CD
            </div>
            <div className="hidden sm:block">
              <p className="text-xs font-medium leading-none text-slate-900">
                CareDesk Admin
              </p>
              <p className="mt-0.5 text-[10px] leading-none text-slate-500">
                Clinic Operations
              </p>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
          </button>

          {showProfile ? (
            <div className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 bg-white p-1.5 shadow-elevated">
              <div className="border-b border-slate-100 px-3 py-2">
                <p className="text-xs font-semibold text-slate-900">
                  CareDesk Admin
                </p>
                <p className="text-[11px] text-slate-500">
                  operations@careflow.clinic
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowProfile(false);
                  onNavigate("settings");
                }}
                className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                <UserCheck className="h-3.5 w-3.5 text-slate-400" />
                Assistant Configuration
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
