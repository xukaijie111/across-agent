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
import { syncChatUrl } from "../lib/chatUrl";
import { renderMarkdown } from "../lib/renderMarkdown";
import { createStreamReveal, type StreamRevealHandle } from "../lib/streamReveal";
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

let abortController: AbortController | null = null;
let streamReveal: StreamRevealHandle | null = null;

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
  if (pendingInterrupt.value) {
    return "请先确认或取消上方操作";
  }
  if (props.agent.id === "meeting-notes") {
    return "粘贴会议文字稿…";
  }
  return "输入消息...";
};

function showMarkdown(msg: ChatMessage): boolean {
  return msg.role === "assistant" && !msg.streaming && !msg.awaitingAction;
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
  await resetSession(sessionId.value);
  messages.value = [];
  input.value = "";
  loading.value = false;
  pendingInterrupt.value = false;
  showToast("对话已清空");
}

async function sendMessage() {
  const text = input.value.trim();
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
  <div class="chat-panel">
    <van-nav-bar fixed placeholder safe-area-inset-top>
      <template v-if="showMenu" #left>
        <button class="icon-btn" type="button" aria-label="打开菜单" @click="emit('openMenu')">
          ☰
        </button>
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

    <main ref="listRef" class="chat-list" @scroll="onListScroll">
      <van-empty v-if="messages.length === 0" description="发一条消息开始调试" />
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

    <footer class="composer safe-area-bottom">
      <textarea
        ref="inputRef"
        v-model="input"
        class="composer__input"
        rows="1"
        :maxlength="inputMaxLength()"
        :placeholder="inputPlaceholder()"
        :disabled="!sessionId || pendingInterrupt"
        @input="resizeInput"
        @keydown.enter.exact.prevent="sendMessage"
      />
      <van-button
        type="primary"
        size="small"
        :loading="loading"
        :disabled="!input.trim() || !sessionId || pendingInterrupt"
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
  background: #f5f6f8;
}

.icon-btn,
.text-btn {
  border: none;
  background: transparent;
  color: #1989fa;
  padding: 0 4px;
}

.icon-btn {
  font-size: 18px;
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
  color: #969799;
  margin-top: 2px;
}

.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 12px 8px;
  -webkit-overflow-scrolling: touch;
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
  background: #1989fa;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.bubble.assistant {
  background: #fff;
  color: #1f2329;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
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
  background: #f2f3f5;
  font-size: 0.92em;
}

.bubble__markdown :deep(pre) {
  margin: 8px 0;
  padding: 10px;
  overflow-x: auto;
  border-radius: 8px;
  background: #f2f3f5;
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
  padding: 8px 10px calc(8px + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 1px solid #ebedf0;
}

.composer__input {
  flex: 1;
  min-height: 36px;
  max-height: 120px;
  padding: 8px 12px;
  border: none;
  border-radius: 10px;
  background: #f7f8fa;
  font-size: 15px;
  line-height: 1.5;
  resize: none;
  outline: none;
  color: #323233;
}

.composer__input:disabled {
  color: #c8c9cc;
  background: #f2f3f5;
}

.composer__input::placeholder {
  color: #c8c9cc;
}

.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
}
</style>
