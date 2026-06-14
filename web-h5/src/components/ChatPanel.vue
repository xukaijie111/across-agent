<script setup lang="ts">
import { nextTick, onUnmounted, ref, watch } from "vue";
import { showFailToast, showToast } from "vant";
import {
  clearStoredSessionId,
  createSession,
  fetchSessionMessages,
  readStoredSessionId,
  resetSession,
  writeStoredSessionId,
} from "../api/agents";
import { streamChat, streamResume } from "../api/sse";
import { transcribeAudio } from "../api/stt";
import { syncChatUrl } from "../lib/chatUrl";
import { createAudioRecorder, isAudioRecordSupported, type AudioRecorderHandle } from "../lib/audioRecord";
import { renderMarkdown } from "../lib/renderMarkdown";
import { createStreamReveal, type StreamRevealHandle } from "../lib/streamReveal";
import { personaWelcome } from "../lib/personaWelcome";
import type { AgentInfo, ChatMessage, HistoryMessage, InterruptPayload } from "../types";

const props = defineProps<{
  agent: AgentInfo;
  active: boolean;
  showMenu?: boolean;
}>();

const emit = defineEmits<{
  sessionChange: [sessionId: string];
  openMenu: [];
}>();

const sessionId = ref("");
const input = ref("");
const loading = ref(false);
const pendingInterrupt = ref(false);
const messages = ref<ChatMessage[]>([]);
const listRef = ref<HTMLElement | null>(null);
const inputRef = ref<HTMLTextAreaElement | null>(null);
const initialized = ref(false);
const stickToBottom = ref(true);
const speechSupported = ref(isAudioRecordSupported());
const speechListening = ref(false);
const speechTranscribing = ref(false);

let abortController: AbortController | null = null;
let streamReveal: StreamRevealHandle | null = null;
let audioRecorder: AudioRecorderHandle | null = null;
let speechBase = "";

function stopStreamReveal() {
  streamReveal?.cancel();
  streamReveal = null;
}

function startStreamReveal(assistantId: string, onRevealDone?: () => void) {
  stopStreamReveal();
  streamReveal = createStreamReveal(
    (visible) => {
      const idx = messages.value.findIndex((m) => m.id === assistantId);
      if (idx < 0) {
        return;
      }
      messages.value[idx] = {
        ...messages.value[idx],
        content: visible,
        awaitingAction: false,
      };
      void scrollToBottom(true);
    },
    () => {
      const idx = messages.value.findIndex((m) => m.id === assistantId);
      if (idx >= 0) {
        messages.value[idx] = {
          ...messages.value[idx],
          streaming: false,
          awaitingAction: false,
          interrupt: undefined,
        };
      }
      stopStreamReveal();
      void scrollToBottom(true);
      onRevealDone?.();
    },
  );
}

const inputMaxLength = () => (props.agent.id === "meeting-notes" ? 20000 : 500);

const inputPlaceholder = () => {
  if (speechTranscribing.value) {
    return "正在识别语音…";
  }
  if (speechListening.value) {
    return "正在录音，点麦克风结束…";
  }
  if (pendingInterrupt.value) {
    return "请先确认或取消上方操作";
  }
  if (props.agent.id === "meeting-notes") {
    return "粘贴会议文字稿…";
  }
  return "输入消息，或点麦克风语音输入";
};

function showMarkdown(msg: ChatMessage): boolean {
  return msg.role === "assistant" && !msg.streaming && !msg.awaitingAction;
}

function ensureAudioRecorder() {
  if (!audioRecorder) {
    audioRecorder = createAudioRecorder();
  }
  return audioRecorder;
}

function stopSpeechInput() {
  audioRecorder?.cancel();
  speechListening.value = false;
  speechTranscribing.value = false;
  speechBase = "";
}

async function toggleSpeechInput() {
  if (!sessionId.value || loading.value || pendingInterrupt.value || speechTranscribing.value) {
    return;
  }
  if (!speechSupported.value) {
    showFailToast("当前浏览器不支持录音");
    return;
  }

  const recorder = ensureAudioRecorder();
  if (speechListening.value) {
    speechListening.value = false;
    speechTranscribing.value = true;
    try {
      const wav = await recorder.stop();
      const text = await transcribeAudio(wav);
      input.value = `${speechBase}${text}`;
      resizeInput();
      await focusInput();
    } catch (err) {
      const message = err instanceof Error ? err.message : "语音识别失败";
      showFailToast(message);
    } finally {
      speechTranscribing.value = false;
      speechBase = "";
    }
    return;
  }

  speechBase = input.value;
  speechListening.value = true;
  try {
    await recorder.start();
  } catch {
    speechListening.value = false;
    speechBase = "";
    showFailToast("无法访问麦克风，请检查权限");
  }
}

function composerDisabled() {
  return !sessionId.value || pendingInterrupt.value || speechListening.value || speechTranscribing.value;
}

function sendDisabled() {
  return (
    !input.value.trim() ||
    !sessionId.value ||
    pendingInterrupt.value ||
    speechListening.value ||
    speechTranscribing.value
  );
}

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function onListScroll() {
  const el = listRef.value;
  if (!el) {
    return;
  }
  const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
  stickToBottom.value = distance < 80;
}

async function scrollToBottom(force = false) {
  if (!force && !stickToBottom.value) {
    return;
  }
  await nextTick();
  requestAnimationFrame(() => {
    const el = listRef.value;
    if (!el) {
      return;
    }
    el.scrollTop = el.scrollHeight;
  });
}

function resizeInput() {
  const el = inputRef.value;
  if (!el) {
    return;
  }
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
}

async function focusInput() {
  await nextTick();
  const el = inputRef.value;
  if (!el || el.disabled) {
    return;
  }
  el.focus({ preventScroll: true });
}

function hydrateMessages(rows: HistoryMessage[]) {
  messages.value = rows.map((row) => ({
    id: row.id,
    role: row.role,
    content: row.content,
    interrupt: row.interrupt,
    awaitingAction: row.awaiting_action,
  }));
  pendingInterrupt.value = messages.value.some((m) => m.awaitingAction);
}

function rememberSession(sid: string, syncUrl: boolean) {
  writeStoredSessionId(props.agent.id, sid);
  if (syncUrl && props.active) {
    syncChatUrl(props.agent.id, sid);
  }
  emit("sessionChange", sid);
}

function handleStreamEvents(assistantId: string, onDone?: () => void) {
  return (event: string, data: Record<string, unknown>) => {
    const idx = messages.value.findIndex((m) => m.id === assistantId);
    if (idx < 0) {
      return;
    }

    if (event === "delta" && typeof data.content === "string") {
      streamReveal?.append(data.content);
    }

    if (event === "interrupt") {
      stopStreamReveal();
      const interrupt = {
        type: String(data.type ?? "return_confirm"),
        prompt: String(data.prompt ?? "请确认是否继续"),
        options: Array.isArray(data.options) ? data.options.map(String) : undefined,
      } satisfies InterruptPayload;
      messages.value[idx] = {
        ...messages.value[idx],
        content: interrupt.prompt || "请确认是否继续",
        streaming: false,
        interrupt,
        awaitingAction: true,
      };
      pendingInterrupt.value = true;
      void scrollToBottom();
    }

    if (event === "done" && typeof data.content === "string") {
      pendingInterrupt.value = false;
      onDone?.();
      if (streamReveal) {
        streamReveal.finish(data.content);
      } else {
        messages.value[idx] = {
          ...messages.value[idx],
          content: data.content,
          streaming: false,
          awaitingAction: false,
          interrupt: undefined,
        };
      }
    }

    if (event === "error") {
      stopStreamReveal();
      const msg = typeof data.message === "string" ? data.message : "未知错误";
      messages.value[idx] = {
        ...messages.value[idx],
        content: `出错了：${msg}`,
        streaming: false,
        awaitingAction: false,
      };
      pendingInterrupt.value = false;
      showFailToast(msg);
    }
  };
}

async function initSession(preferredSessionId?: string, showTip = false) {
  const keepaliveId = preferredSessionId || readStoredSessionId(props.agent.id) || undefined;
  const session = await createSession(props.agent.id, keepaliveId);
  sessionId.value = session.session_id;
  rememberSession(session.session_id, props.active);
  initialized.value = true;

  if (session.resumed) {
    const history = await fetchSessionMessages(session.session_id);
    if (history.length > 0) {
      hydrateMessages(history);
    }
  }

  await scrollToBottom(true);
  if (showTip) {
    showToast(session.resumed ? `已恢复：${props.agent.name}` : `已就绪：${props.agent.name}`);
  }
  await focusInput();
}

async function openSession(targetSessionId: string, showTip = false) {
  abortController?.abort();
  abortController = null;
  stopStreamReveal();
  loading.value = false;

  const session = await createSession(props.agent.id, targetSessionId);
  sessionId.value = session.session_id;
  rememberSession(session.session_id, true);

  const history = await fetchSessionMessages(session.session_id);
  hydrateMessages(history);
  await scrollToBottom();

  if (showTip) {
    showToast("已切换历史会话");
  }
}

async function newSession() {
  abortController?.abort();
  abortController = null;
  stopStreamReveal();
  clearStoredSessionId(props.agent.id);

  const session = await createSession(props.agent.id);
  sessionId.value = session.session_id;
  rememberSession(session.session_id, true);
  messages.value = [];
  input.value = "";
  loading.value = false;
  pendingInterrupt.value = false;
  showToast("已新建会话");
}

async function clearChat() {
  if (!sessionId.value) {
    return;
  }
  abortController?.abort();
  abortController = null;
  stopStreamReveal();
  stopSpeechInput();
  await resetSession(sessionId.value);
  messages.value = [];
  input.value = "";
  loading.value = false;
  pendingInterrupt.value = false;
  showToast("对话已清空");
}

function showPersonaWelcome() {
  return props.agent.id === "persona" && messages.value.length === 0 && !loading.value;
}

async function sendShortcut(text: string) {
  if (loading.value || !sessionId.value || pendingInterrupt.value) {
    return;
  }
  await submitMessage(text);
}

async function submitMessage(overrideText?: string) {
  stopSpeechInput();
  const text = (overrideText ?? input.value).trim();
  if (!text || loading.value || !sessionId.value || pendingInterrupt.value) {
    return;
  }

  input.value = "";
  resizeInput();
  loading.value = true;
  stickToBottom.value = true;
  messages.value.push({ id: uid(), role: "user", content: text });

  const assistantId = uid();
  messages.value.push({ id: assistantId, role: "assistant", content: "", streaming: true });
  startStreamReveal(assistantId);
  await scrollToBottom(true);

  abortController = new AbortController();

  try {
    await streamChat(
      sessionId.value,
      text,
      handleStreamEvents(assistantId, () => {
        loading.value = false;
      }),
      abortController.signal,
    );
  } catch (err) {
    stopStreamReveal();
    const idx = messages.value.findIndex((m) => m.id === assistantId);
    const msg = err instanceof Error ? err.message : "请求失败";
    if (idx >= 0) {
      messages.value[idx] = {
        ...messages.value[idx],
        content: `出错了：${msg}`,
        streaming: false,
      };
    }
    showFailToast(msg);
  } finally {
    loading.value = false;
    abortController = null;
    await scrollToBottom();
    if (!pendingInterrupt.value && !streamReveal?.isRunning()) {
      await focusInput();
    }
  }
}

async function sendMessage() {
  await submitMessage();
}

async function handleResume(decision: "confirm" | "cancel", sourceMessageId: string) {
  if (!sessionId.value || loading.value) {
    return;
  }

  const idx = messages.value.findIndex((m) => m.id === sourceMessageId);
  if (idx < 0) {
    return;
  }

  loading.value = true;
  pendingInterrupt.value = false;
  messages.value[idx] = {
    ...messages.value[idx],
    awaitingAction: false,
    interrupt: undefined,
    streaming: false,
  };

  const assistantId = uid();
  messages.value.push({ id: assistantId, role: "assistant", content: "", streaming: true });
  startStreamReveal(assistantId);
  await scrollToBottom();

  abortController = new AbortController();

  try {
    await streamResume(
      sessionId.value,
      decision,
      handleStreamEvents(assistantId),
      abortController.signal,
    );
  } catch (err) {
    stopStreamReveal();
    const msg = err instanceof Error ? err.message : "请求失败";
    const target = messages.value.findIndex((m) => m.id === assistantId);
    if (target >= 0) {
      messages.value[target] = {
        ...messages.value[target],
        content: `出错了：${msg}`,
        streaming: false,
      };
    }
    showFailToast(msg);
  } finally {
    loading.value = false;
    abortController = null;
    await scrollToBottom();
    if (!pendingInterrupt.value && !streamReveal?.isRunning()) {
      await focusInput();
    }
  }
}

onUnmounted(() => {
  stopStreamReveal();
  stopSpeechInput();
});

watch(
  () => props.active,
  (isActive) => {
    if (!isActive || !sessionId.value) {
      return;
    }
    syncChatUrl(props.agent.id, sessionId.value);
    emit("sessionChange", sessionId.value);
  },
);

defineExpose({
  initSession,
  openSession,
  newSession,
  clearChat,
  getSessionId: () => sessionId.value,
  isInitialized: () => initialized.value,
});
</script>

<template>
  <div class="chat-panel" :class="{ 'chat-panel--welcome': showPersonaWelcome() }">
    <van-nav-bar fixed placeholder safe-area-inset-top>
      <template v-if="showMenu" #left>
        <div class="menu-hint">
          <button class="icon-btn" type="button" aria-label="打开菜单" @click="emit('openMenu')">
            ☰
          </button>
          <span class="menu-hint__finger" aria-hidden="true">👈</span>
        </div>
      </template>
      <template #title>
        <div class="nav-title">
          <div class="nav-title__name">{{ agent.name }}</div>
          <div class="nav-title__desc">{{ agent.description }}</div>
        </div>
      </template>
      <template #right>
        <button class="text-btn" type="button" :disabled="loading" @click="clearChat">清空</button>
      </template>
    </van-nav-bar>

    <main
      ref="listRef"
      class="chat-list"
      :class="{ 'chat-list--welcome': showPersonaWelcome() }"
      @scroll="onListScroll"
    >
      <section v-if="showPersonaWelcome()" class="welcome">
        <h1 class="welcome__title">{{ personaWelcome.title }}</h1>
        <p class="welcome__subtitle">{{ personaWelcome.subtitle }}</p>
        <div class="welcome__chips">
          <button
            v-for="item in personaWelcome.shortcuts"
            :key="item"
            class="welcome__chip"
            type="button"
            :disabled="!sessionId || pendingInterrupt"
            @click="sendShortcut(item)"
          >
            {{ item }}
          </button>
        </div>
      </section>
      <van-empty v-else-if="messages.length === 0" description="发一条消息开始调试" />
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="bubble-row"
        :class="msg.role === 'user' ? 'bubble-row--user' : 'bubble-row--assistant'"
      >
        <div class="bubble" :class="msg.role">
          <div
            v-if="showMarkdown(msg)"
            class="bubble__markdown"
            v-html="renderMarkdown(msg.content)"
          />
          <span v-else>{{ msg.content }}</span>
          <van-loading v-if="msg.streaming" size="14px" class="bubble__loading" />
          <div v-if="msg.awaitingAction" class="confirm-actions">
            <van-button
              size="small"
              type="primary"
              :disabled="loading"
              @click="handleResume('confirm', msg.id)"
            >
              继续
            </van-button>
            <van-button
              size="small"
              plain
              :disabled="loading"
              @click="handleResume('cancel', msg.id)"
            >
              取消
            </van-button>
          </div>
        </div>
      </div>
    </main>

    <footer class="composer">
      <button
        v-if="speechSupported"
        class="composer__mic"
        :class="{ 'composer__mic--active': speechListening || speechTranscribing }"
        type="button"
        :disabled="!sessionId || loading || pendingInterrupt || speechTranscribing"
        :aria-label="speechListening ? '停止录音并识别' : '语音输入'"
        @click="toggleSpeechInput"
      >
        {{ speechTranscribing ? "…" : speechListening ? "◉" : "🎤" }}
      </button>
      <textarea
        ref="inputRef"
        v-model="input"
        class="composer__input"
        rows="1"
        :maxlength="inputMaxLength()"
        :placeholder="inputPlaceholder()"
        :disabled="composerDisabled()"
        @input="resizeInput"
        @keydown.enter.exact.prevent="sendMessage"
      />
      <van-button
        type="primary"
        size="small"
        :loading="loading"
        :disabled="sendDisabled()"
        @mousedown.prevent
        @click="sendMessage"
      >
        发送
      </van-button>
    </footer>
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg);
}

.chat-panel--welcome {
  background: var(--color-bg-welcome);
  justify-content: center;
  padding-bottom: env(safe-area-inset-bottom);
}

.chat-list--welcome {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  flex: 0 1 auto;
  overflow: visible;
}

.chat-panel--welcome .composer {
  flex: 0 0 auto;
  margin-top: 20px;
  border-top: none;
  box-shadow: none;
  background: transparent;
  padding-top: 0;
  padding-bottom: calc(12px + env(safe-area-inset-bottom));
}

.welcome {
  width: 100%;
  max-width: 720px;
  padding: 0 12px;
  text-align: center;
}

.welcome__title {
  margin: 0;
  font-size: 30px;
  font-weight: 700;
  line-height: 1.3;
  letter-spacing: 0.02em;
  background: linear-gradient(120deg, #1a1d26 10%, #4f6ef7 90%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.welcome__subtitle {
  margin: 12px 0 0;
  font-size: 15px;
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.welcome__chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 28px;
  margin-bottom: 4px;
}

.welcome__chip {
  border: 1px solid var(--color-chip-border);
  background: var(--color-chip-bg);
  color: #2f3a5c;
  padding: 10px 18px;
  border-radius: 999px;
  font-size: 14px;
  line-height: 1.4;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
  box-shadow: 0 1px 2px rgba(79, 110, 247, 0.06);
}

.welcome__chip:hover:not(:disabled) {
  background: var(--color-chip-hover);
  border-color: #b8c4f8;
}

.welcome__chip:active:not(:disabled) {
  transform: scale(0.98);
}

.welcome__chip:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.icon-btn,
.text-btn {
  border: none;
  background: transparent;
  color: var(--color-accent);
  padding: 0 4px;
}

.icon-btn {
  font-size: 18px;
}

.menu-hint {
  display: inline-flex;
  align-items: center;
  gap: 0;
}

.menu-hint__finger {
  display: inline-block;
  font-size: 22px;
  line-height: 1;
  margin-left: 2px;
  animation: finger-nudge 1.1s ease-in-out infinite;
  filter: sepia(1) saturate(4) hue-rotate(5deg) brightness(1.05);
  text-shadow: 0 0 8px rgba(255, 204, 0, 0.9), 0 2px 4px rgba(255, 160, 0, 0.45);
}

@keyframes finger-nudge {
  0%,
  100% {
    transform: translateX(0);
  }
  50% {
    transform: translateX(-7px) scale(1.1);
  }
}

.text-btn {
  font-size: 14px;
}

.text-btn:disabled {
  color: #c8c9cc;
}

.nav-title {
  line-height: 1.2;
}

.nav-title__name {
  font-size: 16px;
  font-weight: 600;
}

.nav-title__desc {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 12px 8px;
  -webkit-overflow-scrolling: touch;
  background: transparent;
}

.bubble-row {
  display: flex;
  margin-bottom: 12px;
}

.bubble-row--user {
  justify-content: flex-end;
}

.bubble-row--assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 82%;
  padding: 10px 12px;
  border-radius: 14px;
  font-size: 15px;
  line-height: 1.5;
  word-break: break-word;
}

.bubble > span {
  white-space: pre-wrap;
}

.bubble.user {
  background: linear-gradient(135deg, #5b7cfa 0%, #4f6ef7 100%);
  color: #fff;
  border-bottom-right-radius: 4px;
  box-shadow: 0 2px 8px rgba(79, 110, 247, 0.28);
}

.bubble.assistant {
  background: var(--color-surface);
  color: var(--color-text);
  border-bottom-left-radius: 4px;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-soft);
}

.bubble__markdown :deep(h1) {
  margin: 0 0 8px;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.4;
}

.bubble__markdown :deep(h2) {
  margin: 12px 0 6px;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.4;
}

.bubble__markdown :deep(p) {
  margin: 0 0 8px;
}

.bubble__markdown :deep(ul) {
  margin: 0 0 8px;
  padding-left: 1.2em;
}

.bubble__markdown :deep(li) {
  margin-bottom: 4px;
}

.bubble__markdown :deep(strong) {
  font-weight: 600;
}

.bubble__markdown :deep(code) {
  padding: 0 4px;
  border-radius: 4px;
  background: var(--color-accent-softer);
  font-size: 0.92em;
}

.bubble__markdown :deep(pre) {
  margin: 8px 0;
  padding: 10px;
  overflow-x: auto;
  border-radius: 8px;
  background: var(--color-accent-softer);
}

.bubble__markdown :deep(pre code) {
  padding: 0;
  background: transparent;
}

.bubble__loading {
  display: inline-block;
  margin-left: 6px;
  vertical-align: middle;
}

.confirm-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.composer {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding: 10px 12px calc(10px + env(safe-area-inset-bottom));
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  box-shadow: 0 -4px 16px rgba(79, 110, 247, 0.04);
  flex-shrink: 0;
}

.composer__mic {
  flex: 0 0 36px;
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-chip-border);
  border-radius: 10px;
  background: var(--color-accent-softer);
  font-size: 18px;
  line-height: 1;
  padding: 0;
}

.composer__mic:disabled {
  opacity: 0.45;
}

.composer__mic--active {
  background: #ffecec;
  color: #ee0a24;
}

.composer__input {
  flex: 1;
  min-height: 36px;
  max-height: 120px;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-input-bg);
  font-size: 15px;
  line-height: 1.5;
  resize: none;
  outline: none;
  color: var(--color-text);
}

.composer__input:focus {
  border-color: #b8c4f8;
  background: var(--color-surface);
}

.composer__input:disabled {
  color: #b0b6c3;
  background: var(--color-accent-softer);
}

.composer__input::placeholder {
  color: #a8b0bd;
}
</style>
