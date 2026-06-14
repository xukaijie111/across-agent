export type PersonaWelcomeConfig = {
  title: string;
  subtitle: string;
  shortcuts: string[];
};

export const personaWelcome: PersonaWelcomeConfig = {
  title: "你好，我是徐开洁",
  subtitle: "数字分身 · 了解我的履历与 Agent 实践",
  shortcuts: [
    "介绍一下你自己",
    "为什么转向 Agent？",
    "Playground 有哪些子 Agent？",
    "你的技术优势和亮点",
    "Agent 架构是怎么设计的？",
    "客服 Agent 的 HITL 怎么做的？",
    "上下文治理是什么？",
    "这个 Playground 怎么部署的？",
    "最近一年的职业规划",
  ],
};
