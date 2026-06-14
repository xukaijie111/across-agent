export async function transcribeAudio(audio: Blob): Promise<string> {
  const form = new FormData();
  form.append("audio", audio, "recording.wav");

  const res = await fetch("/api/stt", {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    let message = `语音识别失败: ${res.status}`;
    try {
      const payload = await res.json();
      if (typeof payload.detail === "string") {
        message = payload.detail;
      }
    } catch {
      const text = await res.text();
      if (text) {
        message = text;
      }
    }
    throw new Error(message);
  }

  const data = (await res.json()) as { text?: string };
  return (data.text || "").trim();
}
