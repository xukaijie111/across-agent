export type ToolRisk = "read" | "mutate" | "exec";

export type ToolPolicy = "readonly" | "standard" | "full";

/** 未绑定 session 时的兜底：最小权限 */
export const DEFAULT_TOOL_POLICY: ToolPolicy = "readonly";

const RISK_RANK: Record<ToolRisk, number> = {
  read: 0,
  mutate: 1,
  exec: 2,
};

export function maxRiskFor(policy: ToolPolicy): ToolRisk {
  switch (policy) {
    case "readonly":
      return "read";
    case "standard":
      return "mutate";
    case "full":
      return "exec";
  }
}

export function isToolAllowed(toolRisk: ToolRisk, policy: ToolPolicy): boolean {
  return RISK_RANK[toolRisk] <= RISK_RANK[maxRiskFor(policy)];
}

/** mutate / exec 执行前需用户确认（policy 已允许时） */
export function requiresHitlApproval(risk: ToolRisk): boolean {
  return risk === "mutate" || risk === "exec";
}

export function parseToolPolicy(value: unknown): ToolPolicy {
  if (value === "readonly" || value === "standard" || value === "full") {
    return value;
  }
  return DEFAULT_TOOL_POLICY;
}

/** 已登录用户 full；匿名 readonly */
export function policyForAuth(username: string | null | undefined): ToolPolicy {
  return username ? "full" : "readonly";
}
