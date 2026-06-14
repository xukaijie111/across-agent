<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { showFailToast, showToast } from "vant";
import AgentSidebar from "../components/AgentSidebar.vue";
import ChatPanel from "../components/ChatPanel.vue";
import { fetchAgents, fetchSession, fetchSessions } from "../api/agents";
import { parseChatUrl, syncChatUrl } from "../lib/chatUrl";
import type { AgentInfo, SessionSummary } from "../types";

const agents = ref<AgentInfo[]>([]);
const drawerOpen = ref(false);
const activeAgentId = ref("");
const activeSessionId = ref("");
const sessionHistory = ref<SessionSummary[]>([]);
const mountedAgentIds = ref<string[]>([]);
const panelRefs = ref<Record<string, InstanceType<typeof ChatPanel> | null>>({});

const enabledAgents = computed(() => agents.value.filter((a) => a.enabled));
const mountedAgents = computed(() =>
  enabledAgents.value.filter((a) => mountedAgentIds.value.includes(a.id)),
);

function setPanelRef(agentId: string, el: InstanceType<typeof ChatPanel> | null) {
  if (el) {
    panelRefs.value[agentId] = el;
  }
}

function ensureMounted(agentId: string) {
  if (!mountedAgentIds.value.includes(agentId)) {
    mountedAgentIds.value = [...mountedAgentIds.value, agentId];
  }
}

function getPanel(agentId: string) {
  return panelRefs.value[agentId] ?? null;
}

async function refreshSessionHistory() {
  if (!activeAgentId.value) {
    sessionHistory.value = [];
    return;
  }
  sessionHistory.value = await fetchSessions(activeAgentId.value);
}

async function selectAgent(agentId: string, showTip = true) {
  const agent = agents.value.find((a) => a.id === agentId);
  if (!agent?.enabled) {
    showFailToast("该 Agent 尚未启用");
    return;
  }
  if (agentId === activeAgentId.value) {
    drawerOpen.value = false;
    return;
  }

  ensureMounted(agentId);
  activeAgentId.value = agentId;
  await nextTick();

  const panel = getPanel(agentId);
  if (panel && !panel.isInitialized()) {
    await panel.initSession();
  }

  await refreshSessionHistory();

  const sid = panel?.getSessionId();
  if (sid) {
    activeSessionId.value = sid;
    syncChatUrl(agentId, sid);
  }

  drawerOpen.value = false;
  if (showTip) {
    showToast(`已切换：${agent.name}`);
  }
}

async function openSession(targetSessionId: string) {
  try {
    const detail = await fetchSession(targetSessionId);
    ensureMounted(detail.agent_id);
    activeAgentId.value = detail.agent_id;
    activeSessionId.value = targetSessionId;
    await nextTick();

    const panel = getPanel(detail.agent_id);
    await panel?.openSession(targetSessionId, true);
    syncChatUrl(detail.agent_id, targetSessionId);
    await refreshSessionHistory();
    drawerOpen.value = false;
  } catch (err) {
    showFailToast(err instanceof Error ? err.message : "会话不存在");
  }
}

async function handleNewSession() {
  const panel = getPanel(activeAgentId.value);
  await panel?.newSession();
  activeSessionId.value = panel?.getSessionId() ?? "";
  if (activeAgentId.value && activeSessionId.value) {
    syncChatUrl(activeAgentId.value, activeSessionId.value);
  }
  await refreshSessionHistory();
  drawerOpen.value = false;
}

function onSessionChange(agentId: string, sessionId: string) {
  if (agentId === activeAgentId.value) {
    activeSessionId.value = sessionId;
    syncChatUrl(agentId, sessionId);
    void refreshSessionHistory();
  }
}

async function bootstrap() {
  agents.value = await fetchAgents();
  const { agentId: urlAgentId, sessionId: urlSessionId } = parseChatUrl();

  if (urlSessionId) {
    try {
      const detail = await fetchSession(urlSessionId);
      ensureMounted(detail.agent_id);
      activeAgentId.value = detail.agent_id;
      activeSessionId.value = urlSessionId;
      await nextTick();
      const panel = getPanel(detail.agent_id);
      await panel?.initSession(urlSessionId);
      syncChatUrl(detail.agent_id, urlSessionId);
      await refreshSessionHistory();
      return;
    } catch {
      if (urlAgentId) {
        ensureMounted(urlAgentId);
        activeAgentId.value = urlAgentId;
        await nextTick();
        const panel = getPanel(urlAgentId);
        if (panel && !panel.isInitialized()) {
          await panel.initSession();
        }
        await refreshSessionHistory();
        return;
      }
    }
  }

  if (urlAgentId) {
    ensureMounted(urlAgentId);
    activeAgentId.value = urlAgentId;
    await nextTick();
    const panel = getPanel(urlAgentId);
    if (panel && !panel.isInitialized()) {
      await panel.initSession();
    }
    await refreshSessionHistory();
    return;
  }

  const first = enabledAgents.value[0];
  if (first) {
    ensureMounted(first.id);
    activeAgentId.value = first.id;
    await nextTick();
    const panel = getPanel(first.id);
    if (panel && !panel.isInitialized()) {
      await panel.initSession();
    }
    await refreshSessionHistory();
  }
}

function onPopState() {
  const { agentId: urlAgentId, sessionId: urlSessionId } = parseChatUrl();
  if (urlSessionId) {
    void openSession(urlSessionId);
    return;
  }
  if (urlAgentId) {
    void selectAgent(urlAgentId, false);
  }
}

onMounted(() => {
  bootstrap().catch((err) => {
    showFailToast(err instanceof Error ? err.message : "初始化失败");
  });
  window.addEventListener("popstate", onPopState);
});

onUnmounted(() => {
  window.removeEventListener("popstate", onPopState);
});
</script>

<template>
  <div class="playground">
    <van-popup v-model:show="drawerOpen" position="left" :style="{ width: '78%', height: '100%' }">
      <AgentSidebar
        :agents="agents"
        :active-agent-id="activeAgentId"
        :active-session-id="activeSessionId"
        :session-history="sessionHistory"
        @select-agent="selectAgent($event)"
        @open-session="openSession($event)"
        @new-session="handleNewSession"
      />
    </van-popup>

    <ChatPanel
      v-for="agent in mountedAgents"
      :key="agent.id"
      v-show="activeAgentId === agent.id"
      :ref="(el) => setPanelRef(agent.id, el as InstanceType<typeof ChatPanel> | null)"
      :agent="agent"
      :active="activeAgentId === agent.id"
      :show-menu="activeAgentId === agent.id"
      @open-menu="drawerOpen = true"
      @session-change="onSessionChange(agent.id, $event)"
    />
    <van-empty v-if="mountedAgents.length === 0" class="playground__loading" description="正在加载..." />
  </div>
</template>

<style scoped>
.playground {
  height: 100%;
  background: var(--color-bg);
}

.playground__loading {
  margin-top: 40vh;
}
</style>
