export type StreamRevealHandle = {
  append: (chunk: string) => void;
  finish: (finalText: string) => void;
  cancel: () => void;
  isRunning: () => boolean;
};

function charsForFrame(bufferLength: number): number {
  if (bufferLength > 200) {
    return 10;
  }
  if (bufferLength > 80) {
    return 5;
  }
  if (bufferLength > 20) {
    return 2;
  }
  return 1;
}

export function createStreamReveal(
  onUpdate: (visible: string) => void,
  onComplete?: () => void,
): StreamRevealHandle {
  let buffer = "";
  let visible = "";
  let finalText: string | null = null;
  let rafId: number | null = null;
  let cancelled = false;

  function schedule() {
    if (cancelled || rafId !== null) {
      return;
    }
    rafId = requestAnimationFrame(tick);
  }

  function tick() {
    rafId = null;
    if (cancelled) {
      return;
    }

    if (buffer.length > 0) {
      const step = charsForFrame(buffer.length);
      visible += buffer.slice(0, step);
      buffer = buffer.slice(step);
      onUpdate(visible);
      schedule();
      return;
    }

    if (finalText !== null) {
      if (visible !== finalText) {
        buffer = finalText.slice(visible.length);
        if (buffer.length > 0) {
          schedule();
          return;
        }
      }
      onComplete?.();
      return;
    }
  }

  return {
    append(chunk: string) {
      if (cancelled || !chunk) {
        return;
      }
      buffer += chunk;
      schedule();
    },
    finish(text: string) {
      if (cancelled) {
        return;
      }
      finalText = text;
      buffer = text.slice(visible.length);
      schedule();
    },
    cancel() {
      cancelled = true;
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
    },
    isRunning() {
      if (cancelled) {
        return false;
      }
      return buffer.length > 0 || (finalText !== null && visible !== finalText);
    },
  };
}
