<script setup lang="ts">
import type { AgentInfo, SessionSummary } from "../types";

defineProps<{
  agents: AgentInfo[];
  activeAgentId: string;
  activeSessionId: string;
  sessionHistory: SessionSummary[];
}>();

const emit = defineEmits<{
  selectAgent: [agentId: string];
  openSession: [sessionId: string];
  newSession: [];
}>();
</script>

<template>
  <div class="drawer">
    <div class="drawer__header">Agent 调试台</div>

    <div class="drawer__subheader">选择 Agent</div>
    <van-cell-group inset>
      <van-cell
        v-for="agent in agents"
        :key="agent.id"
        :class="{ active: agent.id === activeAgentId }"
        is-link
        @click="emit('selectAgent', agent.id)"
      >
        <template #title>
          <div class="agent-item">
            <div class="agent-item__head">
              <span class="agent-item__name">{{ agent.name }}</span>
              <van-tag v-if="!agent.enabled" type="default">未启用</van-tag>
              <van-tag v-else-if="agent.id === activeAgentId" type="success">当前</van-tag>
            </div>
            <div class="agent-item__desc">{{ agent.description }}</div>
          </div>
        </template>
      </van-cell>
    </van-cell-group>

    <div class="drawer__subheader drawer__subheader--row">
      <span>历史会话</span>
      <button class="text-btn" type="button" @click="emit('newSession')">新建</button>
    </div>
    <van-cell-group inset>
      <van-empty v-if="sessionHistory.length === 0" description="暂无历史会话" />
      <van-cell
        v-for="item in sessionHistory"
        :key="item.session_id"
        :title="item.title || '未命名会话'"
        :label="item.updated_at || item.session_id.slice(0, 8)"
        :class="{ active: item.session_id === activeSessionId }"
        is-link
        @click="emit('openSession', item.session_id)"
      />
    </van-cell-group>
  </div>
</template>

<style scoped>
.drawer {
  height: 100%;
  overflow-y: auto;
  background: #fff;
  padding-top: env(safe-area-inset-top);
  -webkit-overflow-scrolling: touch;
}

.drawer__header {
  padding: 20px 16px 12px;
  font-size: 18px;
  font-weight: 600;
}

.drawer__subheader {
  padding: 16px 16px 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.drawer__subheader--row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.text-btn {
  border: none;
  background: transparent;
  color: var(--color-accent);
  font-size: 14px;
  padding: 0 4px;
}

.agent-item {
  width: 100%;
  padding-right: 8px;
}

.agent-item__head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.agent-item__name {
  font-size: 14px;
  font-weight: 500;
  color: #323233;
}

.agent-item__desc {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-text-muted);
  white-space: normal;
  word-break: break-word;
}

:deep(.van-cell.active) {
  background: var(--color-accent-soft);
}

:deep(.van-cell__title) {
  flex: 1;
  min-width: 0;
}
</style>
