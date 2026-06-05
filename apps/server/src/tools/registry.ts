import {
  DEFAULT_TOOL_POLICY,
  isToolAllowed,
  type ToolPolicy,
  type ToolRisk,
} from "./policy.js";

export type ToolHandler = (args: Record<string, unknown>) => Promise<string> | string;

export type ExecuteToolOptions = {
  toolCallId?: string;
  onStart?: (id: string, name: string, args: Record<string, unknown>) => void;
};

export interface ToolDef {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
  risk: ToolRisk;
  handler: ToolHandler;
}

class ToolRegistry {
  private tools = new Map<string, ToolDef>();

  register(def: ToolDef): void {
    if (this.tools.has(def.name)) {
      throw new Error(`Tool ${def.name} already registered`);
    }
    this.tools.set(def.name, def);
  }

  openaiTools(policy: ToolPolicy = DEFAULT_TOOL_POLICY): Array<Record<string, unknown>> {
    return [...this.tools.values()]
      .filter((t) => isToolAllowed(t.risk, policy))
      .map((t) => ({
        type: "function",
        function: {
          name: t.name,
          description: t.description,
          parameters: t.parameters,
        },
      }));
  }

  getRisk(name: string): ToolRisk | null {
    return this.tools.get(name)?.risk ?? null;
  }

  async invoke(
    name: string,
    args: Record<string, unknown>,
    policy: ToolPolicy = DEFAULT_TOOL_POLICY,
    options?: ExecuteToolOptions,
  ): Promise<string> {
    const tool = this.tools.get(name);
    if (!tool) {
      return JSON.stringify({ ok: false, error: `unknown tool: ${name}` });
    }
    if (!isToolAllowed(tool.risk, policy)) {
      return JSON.stringify({
        ok: false,
        error: `permission denied: tool ${name} (${tool.risk}) not allowed under policy ${policy}`,
      });
    }
    options?.onStart?.(options.toolCallId ?? "", name, args);
    try {
      const result = await tool.handler(args);
      return typeof result === "string" ? result : String(result);
    } catch (err) {
      return JSON.stringify({
        ok: false,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }
}

export const registry = new ToolRegistry();

export function registerTool(def: ToolDef): void {
  registry.register(def);
}

export function getTools(policy?: ToolPolicy): Array<Record<string, unknown>> {
  return registry.openaiTools(policy ?? DEFAULT_TOOL_POLICY);
}

export async function executeTool(
  name: string,
  args: Record<string, unknown>,
  policy?: ToolPolicy,
  options?: ExecuteToolOptions,
): Promise<string> {
  return registry.invoke(name, args, policy ?? DEFAULT_TOOL_POLICY, options);
}

export function getToolRisk(name: string): ToolRisk | null {
  return registry.getRisk(name);
}
