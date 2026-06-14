const TARGET_SAMPLE_RATE = 16000;

export function isAudioRecordSupported(): boolean {
  return !!(
    navigator.mediaDevices &&
    "getUserMedia" in navigator.mediaDevices &&
    typeof window.MediaRecorder !== "undefined" &&
    typeof window.AudioContext !== "undefined"
  );
}

export type AudioRecorderHandle = {
  start: () => Promise<void>;
  stop: () => Promise<Blob>;
  cancel: () => void;
  isRecording: () => boolean;
};

export function createAudioRecorder(): AudioRecorderHandle {
  let stream: MediaStream | null = null;
  let recorder: MediaRecorder | null = null;
  let chunks: Blob[] = [];
  let recording = false;

  const cleanupStream = () => {
    stream?.getTracks().forEach((track) => track.stop());
    stream = null;
  };

  return {
    async start() {
      if (recording) {
        return;
      }
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks = [];
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      recorder = new MediaRecorder(stream, { mimeType });
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };
      recorder.start();
      recording = true;
    },
    async stop() {
      if (!recorder || !recording) {
        throw new Error("录音未开始");
      }
      return new Promise<Blob>((resolve, reject) => {
        recorder!.onstop = async () => {
          recording = false;
          try {
            const webm = new Blob(chunks, { type: recorder?.mimeType || "audio/webm" });
            cleanupStream();
            recorder = null;
            chunks = [];
            const wav = await webmToWav16k(webm);
            resolve(wav);
          } catch (err) {
            cleanupStream();
            recorder = null;
            chunks = [];
            reject(err);
          }
        };
        recorder!.onerror = () => {
          recording = false;
          cleanupStream();
          recorder = null;
          chunks = [];
          reject(new Error("录音失败"));
        };
        recorder!.stop();
      });
    },
    cancel() {
      if (recorder && recording) {
        recorder.stop();
      }
      recording = false;
      cleanupStream();
      recorder = null;
      chunks = [];
    },
    isRecording() {
      return recording;
    },
  };
}

async function webmToWav16k(blob: Blob): Promise<Blob> {
  const audioContext = new AudioContext();
  try {
    const buffer = await blob.arrayBuffer();
    const decoded = await audioContext.decodeAudioData(buffer.slice(0));
    const mono = mixToMono(decoded);
    const resampled = resampleBuffer(mono, decoded.sampleRate, TARGET_SAMPLE_RATE);
    return encodeWav(resampled, TARGET_SAMPLE_RATE);
  } finally {
    await audioContext.close();
  }
}

function mixToMono(buffer: AudioBuffer): Float32Array {
  if (buffer.numberOfChannels === 1) {
    return buffer.getChannelData(0).slice();
  }
  const length = buffer.length;
  const mixed = new Float32Array(length);
  for (let ch = 0; ch < buffer.numberOfChannels; ch += 1) {
    const data = buffer.getChannelData(ch);
    for (let i = 0; i < length; i += 1) {
      mixed[i] += data[i] / buffer.numberOfChannels;
    }
  }
  return mixed;
}

function resampleBuffer(samples: Float32Array, sourceRate: number, targetRate: number): Float32Array {
  if (samples.length === 0) {
    return samples;
  }
  const ratio = sourceRate / targetRate;
  if (Math.abs(ratio - 1) < 0.001) {
    return samples;
  }
  const newLength = Math.max(1, Math.round(samples.length / ratio));
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i += 1) {
    const sourceIndex = i * ratio;
    const left = Math.floor(sourceIndex);
    const right = Math.min(left + 1, samples.length - 1);
    const weight = sourceIndex - left;
    result[i] = samples[left] * (1 - weight) + samples[right] * weight;
  }
  return result;
}

function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  const writeString = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i += 1) {
      view.setUint8(offset + i, value.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    offset += 2;
  }

  return new Blob([buffer], { type: "audio/wav" });
}
