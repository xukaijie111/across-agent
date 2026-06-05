export type HitlDecisionType = "approve" | "reject";

export type HitlDecision = {
  type: HitlDecisionType;
  message?: string;
};

export type HitlActionRequest = {
  name: string;
  args: Record<string, unknown>;
};

export type HitlRequest = {
  action_requests: HitlActionRequest[];
};

export type HitlResumePayload = {
  decisions: HitlDecision[];
};

export function parseHitlResume(value: unknown): HitlDecision[] {
  if (Array.isArray(value)) {
    return value as HitlDecision[];
  }
  if (typeof value === "object" && value !== null && "decisions" in value) {
    const decisions = (value as HitlResumePayload).decisions;
    return Array.isArray(decisions) ? decisions : [];
  }
  return [];
}
