import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ToolCall } from "@/types/chat";

interface ToolCardProps {
  tool: ToolCall;
}

const statusLabel = {
  running: "执行中",
  success: "完成",
  error: "失败",
} as const;

export function ToolCard({ tool }: ToolCardProps) {
  return (
    <Card className="border-dashed bg-muted/40">
      <CardHeader className="py-3">
        <CardTitle className="flex items-center justify-between text-sm font-medium">
          <span>{tool.name}</span>
          <span className="text-xs text-muted-foreground">
            {statusLabel[tool.status]}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 pb-3 pt-0 text-xs">
        <pre className="overflow-x-auto rounded bg-background p-2">
          {JSON.stringify(tool.args, null, 2)}
        </pre>
        {tool.result ? (
          <pre className="overflow-x-auto rounded bg-background p-2 text-green-700 dark:text-green-400">
            {tool.result}
          </pre>
        ) : null}
        {tool.error ? (
          <pre className="overflow-x-auto rounded bg-background p-2 text-red-600">
            {tool.error}
          </pre>
        ) : null}
      </CardContent>
    </Card>
  );
}
