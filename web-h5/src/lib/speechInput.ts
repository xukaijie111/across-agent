export type SpeechInputOptions = {
  lang?: string;
  onInterim: (text: string) => void;
  onFinal: (text: string) => void;
  onError: (message: string) => void;
  onEnd: () => void;
};

type SpeechRecognitionCtor = new () => SpeechRecognition;

function getRecognitionCtor(): SpeechRecognitionCtor | null {
  const w = window as Window & {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function isSpeechInputSupported(): boolean {
  return getRecognitionCtor() !== null;
}

export type SpeechInputHandle = {
  start: () => void;
  stop: () => void;
  listening: () => boolean;
};

export function createSpeechInput(options: SpeechInputOptions): SpeechInputHandle | null {
  const Ctor = getRecognitionCtor();
  if (!Ctor) {
    return null;
  }

  const recognition = new Ctor();
  recognition.lang = options.lang ?? "zh-CN";
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  let active = false;
  let finalBuffer = "";

  recognition.onresult = (event: SpeechRecognitionEvent) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const chunk = event.results[i][0]?.transcript ?? "";
      if (event.results[i].isFinal) {
        finalBuffer += chunk;
        options.onFinal(finalBuffer);
        finalBuffer = "";
      } else {
        interim += chunk;
      }
    }
    if (interim) {
      options.onInterim(interim);
    }
  };

  recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
    if (event.error === "aborted") {
      return;
    }
    const hint =
      event.error === "not-allowed"
        ? "请允许麦克风权限"
        : event.error === "no-speech"
          ? "没有检测到语音"
          : `语音识别失败（${event.error}）`;
    options.onError(hint);
    active = false;
    options.onEnd();
  };

  recognition.onend = () => {
    if (!active) {
      options.onEnd();
      return;
    }
    try {
      recognition.start();
    } catch {
      active = false;
      options.onEnd();
    }
  };

  return {
    start() {
      finalBuffer = "";
      active = true;
      recognition.start();
    },
    stop() {
      active = false;
      recognition.stop();
    },
    listening() {
      return active;
    },
  };
}
