const USER_ID_KEY = "agent_playground_user_id";

function generateUserId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID().replace(/-/g, "");
  }
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 14)}`;
}

/** 浏览器本地持久身份；无过期，已有则复用。 */
export function getUserId(): string {
  const existing = localStorage.getItem(USER_ID_KEY);
  if (existing) {
    return existing;
  }
  const id = generateUserId();
  localStorage.setItem(USER_ID_KEY, id);
  return id;
}
