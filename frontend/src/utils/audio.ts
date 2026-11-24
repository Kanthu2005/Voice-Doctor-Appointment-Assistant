export const TARGET_SAMPLE_RATE = 16000;

/**
 * Downsample Float32 PCM audio from the hardware AudioContext sample rate to
 * 16 kHz mono signed 16-bit little-endian PCM expected by Pipecat.
 */
export function downsampleFloat32ToInt16Pcm(
  input: Float32Array,
  inputSampleRate: number,
  targetSampleRate: number = TARGET_SAMPLE_RATE
): ArrayBuffer {
  if (input.length === 0) {
    return new ArrayBuffer(0);
  }

  let samples: Float32Array;
  if (inputSampleRate === targetSampleRate) {
    samples = input;
  } else {
    const ratio = inputSampleRate / targetSampleRate;
    const outputLength = Math.max(1, Math.floor(input.length / ratio));
    samples = new Float32Array(outputLength);

    for (let i = 0; i < outputLength; i++) {
      const srcIndex = i * ratio;
      const idx0 = Math.floor(srcIndex);
      const idx1 = Math.min(idx0 + 1, input.length - 1);
      const frac = srcIndex - idx0;
      samples[i] = input[idx0] * (1 - frac) + input[idx1] * frac;
    }
  }

  const buffer = new ArrayBuffer(samples.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < samples.length; i++) {
    const clamped = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
  }
  return buffer;
}

/**
 * Convert incoming 16-bit little-endian PCM audio bytes into Float32 samples
 * for Web Audio API playback.
 */
export function int16PcmToFloat32(buffer: ArrayBuffer): Float32Array {
  const view = new DataView(buffer);
  const sampleCount = Math.floor(buffer.byteLength / 2);
  const float32 = new Float32Array(sampleCount);

  for (let i = 0; i < sampleCount; i++) {
    const int16 = view.getInt16(i * 2, true);
    float32[i] = int16 / (int16 < 0 ? 0x8000 : 0x7fff);
  }

  return float32;
}

/**
 * Compute normalized RMS amplitude (0..1) for live audio waveform rendering.
 */
export function computeAudioLevel(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sumSquares = 0;
  for (let i = 0; i < samples.length; i++) {
    sumSquares += samples[i] * samples[i];
  }
  const rms = Math.sqrt(sumSquares / samples.length);
  return Math.min(1, rms * 4.5);
}

const WORKLET_SOURCE = `
class MicCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input && input[0] && input[0].length > 0) {
      this.port.postMessage(input[0].slice());
    }
    return true;
  }
}
registerProcessor("mic-capture-processor", MicCaptureProcessor);
`;

export function createMicWorkletBlobUrl(): string {
  const blob = new Blob([WORKLET_SOURCE], { type: "application/javascript" });
  return URL.createObjectURL(blob);
}
