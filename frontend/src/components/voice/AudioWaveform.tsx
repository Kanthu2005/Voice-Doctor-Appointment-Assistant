import { motion } from "framer-motion";
import type { CallState } from "../../types";

interface AudioWaveformProps {
  levels: number[];
  callState: CallState;
  isUserSpeaking: boolean;
  isAssistantSpeaking: boolean;
}

export function AudioWaveform({
  levels,
  callState,
  isUserSpeaking,
  isAssistantSpeaking,
}: AudioWaveformProps) {
  const isLive = callState === "connected";
  const barColor = isAssistantSpeaking
    ? "bg-blue-600"
    : isUserSpeaking
      ? "bg-teal-500"
      : isLive
        ? "bg-slate-400"
        : callState === "muted"
          ? "bg-amber-400"
          : "bg-slate-200";

  return (
    <div
      className="flex h-12 items-center justify-center gap-1 rounded-xl border border-slate-200/80 bg-slate-50/80 px-4"
      aria-label="Live audio waveform"
    >
      {levels.map((level, index) => {
        const heightPercent = isLive
          ? Math.max(14, Math.round(level * 100))
          : callState === "connecting"
            ? 24
            : 12;

        return (
          <motion.span
            key={index}
            animate={{ height: `${heightPercent}%` }}
            transition={{ duration: 0.08, ease: "easeOut" }}
            className={`w-1 rounded-full transition-colors duration-150 ${barColor}`}
          />
        );
      })}
    </div>
  );
}
