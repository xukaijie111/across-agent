import {
  CheckCircle2,
  ChevronDown,
  Loader2,
  Wrench,
  XCircle,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { ToolPart } from "@/lib/chat-protocol";

interface ToolCardProps {
  tool: ToolPart;
}

const statusConfig = {
  running: {
    label: "执行中",
    icon: Loader2,
    className: "text-amber-400",
    spin: true,
  },
  success: {
    label: "完成",
    icon: CheckCircle2,
    className: "text-emerald-400",
    spin: false,
  },
  error: {
    label: "失败",
    icon: XCircle,
    className: "text-destructive",
    spin: false,
  },
} as const;

export function ToolCard({ tool }: ToolCardProps) {
  const status = statusConfig[tool.status];
  const StatusIcon = status.icon;

  return (
    <details
      open={tool.status === "running"}
      className="group overflow-hidden rounded-xl border border-border/60 bg-background/60"
    >
      <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3 marker:content-none">
        <div className="flex size-7 items-center justify-center rounded-md bg-muted/60">
          <Wrench className="size-3.5 text-muted-foreground" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate font-mono text-sm">{tool.name}</span>
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
                status.className,
                "bg-current/10",
              )}
            >
              <StatusIcon
                className={cn("size-3", status.spin && "animate-spin")}
              />
              {status.label}
            </span>
          </div>
        </div>
        <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
      </summary>

      <div className="space-y-2 border-t border-border/50 px-4 py-3">
        <div>
          <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            参数
          </p>
          <pre className="overflow-x-auto rounded-lg bg-muted/40 p-3 font-mono text-xs leading-5 text-foreground/90">
            {JSON.stringify(tool.args, null, 2)}
          </pre>
        </div>
        {tool.result ? (
          <div>
            <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              结果
            </p>
            <pre className="overflow-x-auto rounded-lg bg-emerald-500/5 p-3 font-mono text-xs leading-5 text-emerald-300/90">
              {tool.result}
            </pre>
          </div>
        ) : null}
        {tool.error ? (
          <div>
            <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              错误
            </p>
            <pre className="overflow-x-auto rounded-lg bg-destructive/10 p-3 font-mono text-xs leading-5 text-destructive">
              {tool.error}
            </pre>
          </div>
        ) : null}
      </div>
    </details>
  );
}
