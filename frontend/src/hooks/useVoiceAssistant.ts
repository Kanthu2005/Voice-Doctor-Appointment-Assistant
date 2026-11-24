import { useCallback, useEffect, useRef, useState } from "react";
import { getVoiceWebSocketUrl } from "../services/api";
import type {
  AppointmentConfirmationEvent,
  CallState,
  TranscriptEntry,
  VoiceWebSocketMessage,
} from "../types";
import {
  TARGET_SAMPLE_RATE,
  computeAudioLevel,
  createMicWorkletBlobUrl,
  downsampleFloat32ToInt16Pcm,
  int16PcmToFloat32,
} from "../utils/audio";
import { formatDuration } from "../utils/format";

const WAVEFORM_BARS = 20;
const QUIET_WAVEFORM = Array.from({ length: WAVEFORM_BARS }, () => 0.08);

export interface VoiceAssistantUIState {
  callState: CallState;
  isMuted: boolean;
  isUserSpeaking: boolean;
  isAssistantSpeaking: boolean;
  audioLevels: number[];
  durationSeconds: number;
  transcript: TranscriptEntry[];
  latestBooking: AppointmentConfirmationEvent | null;
  latestCancellation: AppointmentConfirmationEvent | null;
  errorMessage: string | null;
  startCall: () => Promise<void>;
  endCall: () => void;
  toggleMute: () => void;
  resetCall: () => void;
}

function formatMicError(err: unknown): string {
  if (err instanceof DOMException) {
    if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
      return "Microphone permission was denied. Allow microphone access in your browser and try again.";
    }
    if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
      return "No microphone was detected on this device.";
    }
    if (err.name === "NotReadableError") {
      return "Microphone is busy in another application.";
    }
    return err.message;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "Unable to access microphone or start voice call.";
}

export function useVoiceAssistant(
  onAppointmentEvent?: (event: AppointmentConfirmationEvent) => void,
  onVoiceError?: (message: string) => void
): VoiceAssistantUIState {
  const [callState, setCallState] = useState<CallState>("idle");
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState<boolean>(false);
  const [isAssistantSpeaking, setIsAssistantSpeaking] = useState<boolean>(false);
  const [audioLevels, setAudioLevels] = useState<number[]>(QUIET_WAVEFORM);
  const [durationSeconds, setDurationSeconds] = useState<number>(0);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [latestBooking, setLatestBooking] =
    useState<AppointmentConfirmationEvent | null>(null);
  const [latestCancellation, setLatestCancellation] =
    useState<AppointmentConfirmationEvent | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const callStateRef = useRef<CallState>("idle");
  const isMutedRef = useRef<boolean>(false);
  const isAssistantSpeakingRef = useRef<boolean>(false);
  const durationRef = useRef<number>(0);
  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const micSourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const captureNodeRef = useRef<AudioWorkletNode | ScriptProcessorNode | null>(null);
  const workletUrlRef = useRef<string | null>(null);
  const playbackSourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const nextPlaybackTimeRef = useRef<number>(0);
  const userClosingRef = useRef<boolean>(false);
  const fatalErrorReceivedRef = useRef<boolean>(false);
  const onAppointmentEventRef = useRef(onAppointmentEvent);
  const onVoiceErrorRef = useRef(onVoiceError);

  onAppointmentEventRef.current = onAppointmentEvent;
  onVoiceErrorRef.current = onVoiceError;

  const updateCallState = useCallback((next: CallState) => {
    callStateRef.current = next;
    setCallState(next);
  }, []);

  const pushWaveformSample = useCallback((level: number) => {
    setAudioLevels((prev) => {
      const next = prev.slice(1);
      next.push(level);
      return next;
    });
  }, []);

  const appendSystemMessage = useCallback((text: string) => {
    setTranscript((prev) => [
      ...prev,
      {
        id: `sys-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        role: "system",
        text,
        timestamp: formatDuration(durationRef.current),
        final: true,
      },
    ]);
  }, []);

  const stopQueuedPlayback = useCallback(() => {
    for (const source of playbackSourcesRef.current) {
      try {
        source.stop();
        source.disconnect();
      } catch {
        // Ignore already-ended nodes.
      }
    }
    playbackSourcesRef.current.clear();
    if (audioContextRef.current) {
      nextPlaybackTimeRef.current = audioContextRef.current.currentTime;
    } else {
      nextPlaybackTimeRef.current = 0;
    }
    isAssistantSpeakingRef.current = false;
    setIsAssistantSpeaking(false);
  }, []);

  const releaseAllResources = useCallback(async () => {
    stopQueuedPlayback();

    if (captureNodeRef.current) {
      try {
        captureNodeRef.current.disconnect();
      } catch {
        // Ignore disconnect errors.
      }
      captureNodeRef.current = null;
    }

    if (micSourceRef.current) {
      try {
        micSourceRef.current.disconnect();
      } catch {
        // Ignore disconnect errors.
      }
      micSourceRef.current = null;
    }

    if (mediaStreamRef.current) {
      for (const track of mediaStreamRef.current.getTracks()) {
        track.stop();
      }
      mediaStreamRef.current = null;
    }

    if (workletUrlRef.current) {
      URL.revokeObjectURL(workletUrlRef.current);
      workletUrlRef.current = null;
    }

    if (audioContextRef.current) {
      const ctx = audioContextRef.current;
      audioContextRef.current = null;
      if (ctx.state !== "closed") {
        try {
          await ctx.close();
        } catch {
          // Ignore close errors.
        }
      }
    }

    if (wsRef.current) {
      const ws = wsRef.current;
      wsRef.current = null;
      if (
        ws.readyState === WebSocket.OPEN ||
        ws.readyState === WebSocket.CONNECTING
      ) {
        try {
          ws.close(1000, "Call ended");
        } catch {
          // Ignore close errors.
        }
      }
    }

    setIsUserSpeaking(false);
    setIsAssistantSpeaking(false);
    setAudioLevels(QUIET_WAVEFORM);
  }, [stopQueuedPlayback]);

  // Live call duration timer
  useEffect(() => {
    if (callState !== "connected" && callState !== "muted") {
      return;
    }

    const timer = window.setInterval(() => {
      setDurationSeconds((prev) => {
        const next = prev + 1;
        durationRef.current = next;
        return next;
      });
    }, 1000);

    return () => window.clearInterval(timer);
  }, [callState]);

  // Cleanup microphone, AudioContext, and WebSocket on unmount
  useEffect(() => {
    return () => {
      userClosingRef.current = true;
      void releaseAllResources();
    };
  }, [releaseAllResources]);

  const scheduleAudioPlayback = useCallback(
    (pcmBuffer: ArrayBuffer) => {
      const ctx = audioContextRef.current;
      if (!ctx || ctx.state === "closed") return;

      const floatSamples = int16PcmToFloat32(pcmBuffer);
      if (floatSamples.length === 0) return;

      pushWaveformSample(computeAudioLevel(floatSamples));

      const audioBuffer = ctx.createBuffer(
        1,
        floatSamples.length,
        TARGET_SAMPLE_RATE
      );
      audioBuffer.getChannelData(0).set(floatSamples);

      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      const now = ctx.currentTime;
      const startAt = Math.max(now, nextPlaybackTimeRef.current);
      nextPlaybackTimeRef.current = startAt + audioBuffer.duration;

      playbackSourcesRef.current.add(source);
      isAssistantSpeakingRef.current = true;
      setIsAssistantSpeaking(true);

      source.onended = () => {
        playbackSourcesRef.current.delete(source);
        if (playbackSourcesRef.current.size === 0) {
          isAssistantSpeakingRef.current = false;
          setIsAssistantSpeaking(false);
        }
      };

      source.start(startAt);
    },
    [pushWaveformSample]
  );

  const handleServerJsonMessage = useCallback(
    (rawText: string) => {
      let msg: VoiceWebSocketMessage;
      try {
        msg = JSON.parse(rawText) as VoiceWebSocketMessage;
      } catch {
        return;
      }

      if (msg.type === "status" && msg.state === "connected") {
        updateCallState(isMutedRef.current ? "muted" : "connected");
        appendSystemMessage("Connected to Maya AI voice pipeline.");
        return;
      }

      if (msg.type === "vad") {
        setIsUserSpeaking(msg.speaking);
        return;
      }

      if (msg.type === "interruption") {
        stopQueuedPlayback();
        return;
      }

      if (msg.type === "transcript") {
        const text = msg.text.trim();
        if (!text) return;

        setTranscript((prev) => {
          // Update the most recent non-final user transcript in place.
          if (msg.role === "user" && prev.length > 0) {
            const last = prev[prev.length - 1];
            if (last.role === "user" && !last.final) {
              const updated = prev.slice(0, -1);
              updated.push({
                ...last,
                text,
                final: msg.final,
                timestamp: formatDuration(durationRef.current),
              });
              return updated;
            }
          }

          return [
            ...prev,
            {
              id: `${msg.role}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
              role: msg.role,
              text,
              timestamp: formatDuration(durationRef.current),
              final: msg.final,
            },
          ];
        });
        return;
      }

      if (msg.type === "appointment_event") {
        const eventRecord: AppointmentConfirmationEvent = {
          action: msg.action,
          appointment: msg.appointment,
          receivedAt: formatDuration(durationRef.current),
        };
        if (msg.action === "booked") {
          setLatestBooking(eventRecord);
        } else {
          setLatestCancellation(eventRecord);
        }
        onAppointmentEventRef.current?.(eventRecord);
        return;
      }

      if (msg.type === "error") {
        setErrorMessage(msg.message);
        appendSystemMessage(`Pipeline error: ${msg.message}`);
        onVoiceErrorRef.current?.(msg.message);
        if (msg.fatal) {
          fatalErrorReceivedRef.current = true;
          updateCallState("error");
          void releaseAllResources();
        }
      }
    },
    [appendSystemMessage, releaseAllResources, stopQueuedPlayback, updateCallState]
  );

  const startCall = useCallback(async () => {
    if (
      callStateRef.current === "connecting" ||
      callStateRef.current === "connected" ||
      callStateRef.current === "muted" ||
      callStateRef.current === "ending"
    ) {
      return;
    }

    userClosingRef.current = false;
    fatalErrorReceivedRef.current = false;
    isMutedRef.current = false;
    durationRef.current = 0;

    setIsMuted(false);
    setDurationSeconds(0);
    setErrorMessage(null);
    setLatestBooking(null);
    setLatestCancellation(null);
    setTranscript([]);
    setAudioLevels(QUIET_WAVEFORM);
    updateCallState("connecting");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      const msg =
        "Browser microphone capture (navigator.mediaDevices.getUserMedia) is unavailable in this context.";
      setErrorMessage(msg);
      updateCallState("error");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      mediaStreamRef.current = stream;

      const audioCtx = new AudioContext();
      if (audioCtx.state === "suspended") {
        await audioCtx.resume();
      }
      audioContextRef.current = audioCtx;
      nextPlaybackTimeRef.current = audioCtx.currentTime;

      const micSource = audioCtx.createMediaStreamSource(stream);
      micSourceRef.current = micSource;

      const sendMicChunk = (floatChunk: Float32Array) => {
        const ws = wsRef.current;
        if (!ws || ws.readyState !== WebSocket.OPEN) return;

        if (isMutedRef.current) {
          pushWaveformSample(0.05);
          return;
        }

        const level = computeAudioLevel(floatChunk);
        if (!isAssistantSpeakingRef.current) {
          pushWaveformSample(level);
        }

        const pcmBuffer = downsampleFloat32ToInt16Pcm(
          floatChunk,
          audioCtx.sampleRate,
          TARGET_SAMPLE_RATE
        );
        if (pcmBuffer.byteLength > 0) {
          ws.send(pcmBuffer);
        }
      };

      // Prefer modern AudioWorkletNode, with ScriptProcessorNode fallback
      if (audioCtx.audioWorklet) {
        const workletUrl = createMicWorkletBlobUrl();
        workletUrlRef.current = workletUrl;
        await audioCtx.audioWorklet.addModule(workletUrl);
        const workletNode = new AudioWorkletNode(audioCtx, "mic-capture-processor");
        workletNode.port.onmessage = (event: MessageEvent<Float32Array>) => {
          sendMicChunk(event.data);
        };
        micSource.connect(workletNode);
        // Connect via silent gain so graph stays active without mic feedback
        const silentGain = audioCtx.createGain();
        silentGain.gain.value = 0;
        workletNode.connect(silentGain);
        silentGain.connect(audioCtx.destination);
        captureNodeRef.current = workletNode;
      } else {
        const scriptNode = audioCtx.createScriptProcessor(2048, 1, 1);
        scriptNode.onaudioprocess = (event: AudioProcessingEvent) => {
          sendMicChunk(event.inputBuffer.getChannelData(0));
        };
        micSource.connect(scriptNode);
        const silentGain = audioCtx.createGain();
        silentGain.gain.value = 0;
        scriptNode.connect(silentGain);
        silentGain.connect(audioCtx.destination);
        captureNodeRef.current = scriptNode;
      }

      const wsUrl = getVoiceWebSocketUrl();
      const ws = new WebSocket(wsUrl);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        appendSystemMessage(`WebSocket opened (${wsUrl}). Waiting for pipeline ready...`);
      };

      ws.onmessage = (event: MessageEvent) => {
        if (event.data instanceof ArrayBuffer) {
          scheduleAudioPlayback(event.data);
        } else if (typeof event.data === "string") {
          handleServerJsonMessage(event.data);
        }
      };

      ws.onerror = () => {
        if (!userClosingRef.current && !fatalErrorReceivedRef.current) {
          setErrorMessage(
            "Unable to establish real-time voice WebSocket connection. Verify the backend server is running."
          );
          updateCallState("error");
        }
      };

      ws.onclose = (closeEvent: CloseEvent) => {
        if (userClosingRef.current) {
          void releaseAllResources().then(() => {
            updateCallState("ended");
          });
          return;
        }

        if (fatalErrorReceivedRef.current) {
          void releaseAllResources();
          return;
        }

        if (closeEvent.code !== 1000 && callStateRef.current !== "ended") {
          setErrorMessage(
            closeEvent.reason ||
            `Voice connection closed unexpectedly (code ${closeEvent.code}).`
          );
          updateCallState("error");
        } else {
          updateCallState("ended");
        }
        void releaseAllResources();
      };
    } catch (err: unknown) {
      const message = formatMicError(err);
      setErrorMessage(message);
      appendSystemMessage(message);
      updateCallState("error");
      await releaseAllResources();
    }
  }, [
    appendSystemMessage,
    handleServerJsonMessage,
    pushWaveformSample,
    releaseAllResources,
    scheduleAudioPlayback,
    updateCallState,
  ]);

  const endCall = useCallback(() => {
    if (
      callStateRef.current === "idle" ||
      callStateRef.current === "ended" ||
      callStateRef.current === "ending"
    ) {
      return;
    }

    userClosingRef.current = true;
    updateCallState("ending");
    appendSystemMessage(`Ending call (${formatDuration(durationRef.current)})...`);

    void releaseAllResources().then(() => {
      updateCallState("ended");
    });
  }, [appendSystemMessage, releaseAllResources, updateCallState]);

  const toggleMute = useCallback(() => {
    if (callStateRef.current !== "connected" && callStateRef.current !== "muted") {
      return;
    }
    const nextMuted = !isMutedRef.current;
    isMutedRef.current = nextMuted;
    setIsMuted(nextMuted);

    if (mediaStreamRef.current) {
      for (const track of mediaStreamRef.current.getAudioTracks()) {
        track.enabled = !nextMuted;
      }
    }

    if (nextMuted) {
      setIsUserSpeaking(false);
      updateCallState("muted");
    } else {
      updateCallState("connected");
    }
  }, [updateCallState]);

  const resetCall = useCallback(() => {
    userClosingRef.current = true;
    void releaseAllResources().then(() => {
      isMutedRef.current = false;
      durationRef.current = 0;
      setIsMuted(false);
      setDurationSeconds(0);
      setErrorMessage(null);
      setTranscript([]);
      setLatestBooking(null);
      setLatestCancellation(null);
      updateCallState("idle");
    });
  }, [releaseAllResources, updateCallState]);

  return {
    callState,
    isMuted,
    isUserSpeaking,
    isAssistantSpeaking,
    audioLevels,
    durationSeconds,
    transcript,
    latestBooking,
    latestCancellation,
    errorMessage,
    startCall,
    endCall,
    toggleMute,
    resetCall,
  };
}
