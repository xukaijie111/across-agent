export function TypingIndicator() {
  return (
    <div className="flex items-center gap-3 px-1">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-border/60 bg-card">
        <span className="size-2 rounded-full bg-emerald-400/80" />
      </div>
      <div className="flex items-center gap-1 rounded-2xl border border-border/50 bg-card/60 px-4 py-3">
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:0ms]" />
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:150ms]" />
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:300ms]" />
      </div>
    </div>
  );
}
