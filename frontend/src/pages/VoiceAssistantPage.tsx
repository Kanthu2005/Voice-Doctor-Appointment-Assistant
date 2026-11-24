import { useEffect, useRef } from "react";
import {
  AlertCircle,
  Cpu,
  MessageSquare,
  Mic,
  MicOff,
  Phone,
  PhoneOff,
  RotateCcw,
  ShieldCheck,
  Stethoscope,
  Volume2,
} from "lucide-react";
import { EmptyState } from "../components/common/EmptyState";
import { StatusBadge } from "../components/common/StatusBadge";
import { AudioWaveform } from "../components/voice/AudioWaveform";
import {
  BookingConfirmationCard,
  CancellationConfirmationCard,
} from "../components/voice/ConfirmationCards";
import type { VoiceAssistantUIState } from "../hooks/useVoiceAssistant";
import type { VoiceStatus } from "../types";
import { formatDuration } from "../utils/format";

interface VoiceAssistantPageProps {
  voiceUI: VoiceAssistantUIState;
  voiceStatus: VoiceStatus;
  isLiveBackend: boolean;
}

export function VoiceAssistantPage({
  voiceUI,
  voiceStatus,
  isLiveBackend,
}: VoiceAssistantPageProps) {
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [voiceUI.transcript]);

  const isCallActive =
    voiceUI.callState === "connecting" ||
    voiceUI.callState === "connected" ||
  voiceUI.callState === "muted" ||
    voiceUI.callState === "ending";

  const canMute =
    voiceUI.callState === "connected" || voiceUI.callState === "muted";

  const statusDescription = (() => {
    switch (voiceUI.callState) {
      case "idle":
        return "Ready to connect your microphone to the Pipecat voice pipeline.";
      case "connecting":
        return "Requesting microphone access and opening real-time WebSocket...";
      case "connected":
        return voiceUI.isAssistantSpeaking
          ? "Maya AI is speaking..."
          : voiceUI.isUserSpeaking
            ? "Speech detected — listening..."
            : "Call active — speak naturally into your microphone.";
      case "muted":
        return "Microphone muted — unmute to resume speaking.";
      case "ending":
        return "Ending call and releasing audio devices...";
      case "ended":
        return "Call ended. Microphone has been released.";
      case "error":
        return "Call interrupted due to a connection, permission, or configuration error.";
    }
  })();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-slate-900">
            Voice AI Call Console
          </h2>
          <p className="text-sm text-slate-500">
            Live browser-to-Pipecat voice call with ElevenLabs STT/TTS, Silero VAD, and Gemini tools.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge status={voiceUI.callState} size="md" />
            <span className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-800 tabular-nums">
              {formatDuration(voiceUI.durationSeconds)}
            </span>
        </div>
      </div>

      {/* Backend / Credential Alert */}
      {!isLiveBackend ? (
        <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          <div>
            <p className="font-semibold">Backend server offline</p>
            <p className="mt-0.5">
              Start FastAPI on port 8000 before placing a live voice call to{" "}
              <code className="font-mono">{voiceStatus.websocket_path}</code>.
            </p>
          </div>
        </div>
      ) : !voiceStatus.configured ? (
        <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          <div>
            <p className="font-semibold">Voice pipeline credentials missing</p>
            <p className="mt-0.5">
              Configure{" "}
              <code className="font-mono">
                {voiceStatus.missing_credentials.join(", ")}
              </code>{" "}
              in <code className="font-mono">backend/.env</code> to enable live ElevenLabs and Gemini audio.
            </p>
          </div>
        </div>
      ) : null}

      {voiceUI.errorMessage ? (
        <div className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-800">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
          <div>
            <p className="font-semibold">Voice Call Error</p>
            <p className="mt-0.5">{voiceUI.errorMessage}</p>
          </div>
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Phone Call Stage + Live Transcript */}
        <div className="flex flex-col rounded-xl border border-slate-200/90 bg-white shadow-card lg:col-span-2">
                {/* Phone Call Header & Controls */}
                <div className="space-y-5 border-b border-slate-200 p-5">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-3.5">
                      {/* AI Assistant Avatar */}
                      <div className="relative">
                        <div
                          className={`flex h-12 w-12 items-center justify-center rounded-full border-2 bg-slate-900 text-white transition-all ${voiceUI.isAssistantSpeaking
                              ? "border-blue-500 ring-4 ring-blue-100"
                              : voiceUI.callState === "connected"
                                ? "border-teal-500 ring-4 ring-teal-50"
                                : "border-slate-200"
                            }`}
                        >
                          <Stethoscope className="h-5 w-5 text-teal-400" />
                        </div>
                        <span
                          className={`absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-white ${voiceUI.callState === "connected"
                              ? "bg-emerald-500"
                              : voiceUI.callState === "muted"
                                ? "bg-amber-500"
                                : voiceUI.callState === "error"
                                  ? "bg-rose-500"
                                  : "bg-slate-400"
                            }`}
                        />
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold text-slate-900">
                            Maya — AI Medical Receptionist
                          </h3>
                          {voiceUI.isAssistantSpeaking ? (
                            <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700">
                              <Volume2 className="h-3 w-3" />
                              Speaking
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {statusDescription}
                        </p>
                      </div>
                    </div>

                      {/* Call Action Buttons */ }
                      < div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={voiceUI.toggleMute}
                      disabled={!canMute}
                      className={`inline-flex items-center gap-1.5 rounded-lg border px-3.5 py-2 text-xs font-medium transition ${!canMute
                          ? "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400"
                          : voiceUI.isMuted
                            ? "border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100"
                            : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                        }`}
                    >
                      {voiceUI.isMuted ? (
                        <>
                          <MicOff className="h-3.5 w-3.5" />
                          Unmute
                        </>
                      ) : (
                        <>
                          <Mic className="h-3.5 w-3.5" />
                          Mute
                        </>
                      )}
                    </button>

                        {!isCallActive ? (
                      <button
                        type="button"
                        onClick={() => void voiceUI.startCall()}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-4 py-2 text-xs font-semibold text-white shadow-card transition hover:bg-teal-700"
                      >
                        <Phone className="h-3.5 w-3.5" />
                        Start Call
                      </button>
                      ) : (
                      <button
                        type="button"
                        onClick={voiceUI.endCall}
                        disabled={voiceUI.callState === "ending"}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-4 py-2 text-xs font-semibold text-white shadow-card transition hover:bg-rose-700 disabled:opacity-60"
                      >
                        <PhoneOff className="h-3.5 w-3.5" />
                        {voiceUI.callState === "ending" ? "Ending..." : "End Call"}
                      </button>
                )}

                      {voiceUI.callState === "ended" || voiceUI.callState === "error" ? (
                        <button
                          type="button"
                          onClick={voiceUI.resetCall}
                          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                          Reset
                        </button>
                ) : null}
                    </div>
                  </div>

                  {/* Real-time Audio Waveform */}
                  <AudioWaveform
                    levels={voiceUI.audioLevels}
                    callState={voiceUI.callState}
                    isUserSpeaking={voiceUI.isUserSpeaking}
                    isAssistantSpeaking={voiceUI.isAssistantSpeaking}
                  />
                </div>

                {/* Live Conversation Transcript */}
                <div className="flex-1 p-5">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Live Conversation Transcript
                    </span>
                    <span className="text-[11px] font-medium text-slate-400 tabular-nums">
                      {voiceUI.transcript.length} events
                    </span>
                  </div>

                  {voiceUI.transcript.length === 0 ? (
                    <EmptyState
                      icon={MessageSquare}
                      title="Waiting for voice call"
                      description="Click Start Call, grant microphone access, and speak naturally to check availability, book, or cancel an appointment."
                    />
                  ) : (
                      <div className="max-h-[400px] space-y-3 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50/70 p-4">
                        {voiceUI.transcript.map((entry) => {
                          if (entry.role === "system") {
                            return (
                              <div
                                key={entry.id}
                                className="flex items-center justify-center gap-2 py-1 text-center text-[11px] font-medium text-slate-500"
                              >
                                <span>{entry.text}</span>
                                <span className="tabular-nums text-slate-400">
                                  {entry.timestamp}
                                </span>
                              </div>
                            );
                          }

                          const isUser = entry.role === "user";
                          return (
                            <div
                              key={entry.id}
                              className={`flex flex-col ${isUser ? "items-end" : "items-start"
                                }`}
                            >
                              <div
                                className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${isUser
                                    ? "bg-blue-600 text-white"
                                    : "border border-slate-200 bg-white text-slate-800 shadow-card"
                                  }`}
                              >
                                <div className="mb-1 flex items-center justify-between gap-4 text-[11px]">
                                  <span
                                    className={`font-semibold ${isUser ? "text-blue-100" : "text-slate-500"
                                      }`}
                                  >
                                    {isUser
                                      ? entry.final
                                        ? "Caller"
                                        : "Caller (speaking...)"
                                      : "Maya AI"}
                                  </span>
                                  <span
                                    className={`tabular-nums ${isUser ? "text-blue-100/80" : "text-slate-400"
                                      }`}
                                  >
                                    {entry.timestamp}
                                  </span>
                                </div>
                                <p className={!entry.final ? "opacity-85" : ""}>
                                  {entry.text}
                                </p>
                              </div>
                            </div>
                          );
                        })}
                        <div ref={transcriptEndRef} />
                      </div>
            )}
                    </div>
        </div>

                {/* Right Sidebar: Confirmations & Pipeline Diagnostics */}
                <div className="space-y-4">
                  {voiceUI.latestBooking ? (
                    <BookingConfirmationCard event={voiceUI.latestBooking} />
                  ) : null}

                  {voiceUI.latestCancellation ? (
                    <CancellationConfirmationCard event={voiceUI.latestCancellation} />
                  ) : null}

                  <div className="rounded-xl border border-slate-200/90 bg-white p-5 shadow-card">
                    <div className="flex items-center gap-2">
                      <Cpu className="h-4 w-4 text-blue-600" />
                      <h3 className="text-sm font-semibold text-slate-900">
                        Pipecat Voice Transport
                      </h3>
                    </div>
                    <dl className="mt-4 space-y-3 text-xs">
                      <div className="flex items-center justify-between">
                          <dt className="text-slate-500">WebSocket Path</dt>
                          <dd className="font-mono text-[11px] font-medium text-slate-900">
                            {voiceStatus.websocket_path}
                          </dd>
                      </div>
                      <div className="flex items-center justify-between">
                        <dt className="text-slate-500">Audio Format</dt>
                        <dd className="font-medium text-slate-900">16 kHz PCM16 Mono</dd>
                      </div>
                      <div className="flex items-center justify-between">
                        <dt className="text-slate-500">VAD</dt>
                        <dd className="font-medium text-slate-900">
                          {voiceStatus.vad_provider}
                        </dd>
                      </div>
                      <div className="flex items-center justify-between">
                        <dt className="text-slate-500">STT / TTS</dt>
                        <dd className="font-medium text-slate-900">ElevenLabs</dd>
                      </div>
                      <div className="flex items-center justify-between">
                        <dt className="text-slate-500">Reasoning LLM</dt>
                        <dd className="font-medium text-slate-900">Google Gemini</dd>
                      </div>
                    </dl>
                  </div>

                  <div className="rounded-xl border border-slate-200/90 bg-white p-5 shadow-card">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-teal-600" />
                      <h3 className="text-sm font-semibold text-slate-900">
                        Live Safeguards
                      </h3>
                    </div>
                    <ul className="mt-3 space-y-2 text-xs leading-relaxed text-slate-600">
                      <li className="flex items-start gap-2">
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
                        Microphone tracks and AudioContext are released immediately when ending a call.
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
                        Booking and cancellation cards appear automatically when SQLite mutations succeed.
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
            );
}
