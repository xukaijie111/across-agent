export type ToolHandler = (args: Record<string, unknown>) => Promise<string> | string;

export interface ToolDef {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
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

  openaiTools(): Array<Record<string, unknown>> {
    return [...this.tools.values()].map((t) => ({
      type: "function",
      function: {
        name: t.name,
        description: t.description,
        parameters: t.parameters,
      },
    }));
  }

  async invoke(name: string, args: Record<string, unknown>): Promise<string> {
    const tool = this.tools.get(name);
    if (!tool) {
      return JSON.stringify({ ok: false, error: `unknown tool: ${name}` });
    }
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

export function getTools(): Array<Record<string, unknown>> {
  return registry.openaiTools();
}

export async function executeTool(
  name: string,
  args: Record<string, unknown>,
): Promise<string> {
  return registry.invoke(name, args);
}
