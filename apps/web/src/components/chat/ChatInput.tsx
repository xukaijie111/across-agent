"use client";

import { KeyboardEvent, useRef, useState } from "react";
import { ArrowUp, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  disabled?: boolean;
  isLoading?: boolean;
  onSend: (content: string) => void;
  onStop: () => void;
}

export function ChatInput({
  disabled,
  isLoading,
  onSend,
  onStop,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    if (!value.trim()) return;
    onSend(value);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    const el = event.currentTarget;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
    setValue(el.value);
  };

  return (
    <div className="space-y-2">
      <div
        className={cn(
          "relative rounded-2xl border border-border/60 bg-card/80 shadow-sm transition-colors",
          "focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/15",
          disabled && "opacity-60",
        )}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={onKeyDown}
          placeholder="描述你的问题，Enter 发送，Shift+Enter 换行"
          rows={1}
          disabled={disabled}
          className="max-h-40 min-h-[52px] w-full resize-none bg-transparent px-4 py-3.5 pr-14 text-[0.9375rem] leading-6 outline-none placeholder:text-muted-foreground/70"
        />
        <div className="absolute bottom-2.5 right-2.5">
          {isLoading ? (
            <Button
              type="button"
              size="icon-sm"
              variant="outline"
              onClick={onStop}
              aria-label="停止生成"
            >
              <Square className="size-3.5 fill-current" />
            </Button>
          ) : (
            <Button
              type="button"
              size="icon-sm"
              onClick={submit}
              disabled={disabled || !value.trim()}
              aria-label="发送消息"
            >
              <ArrowUp className="size-4" />
            </Button>
          )}
        </div>
      </div>
      <p className="text-center text-xs text-muted-foreground/70">
        CrossAgent 可能产生不准确的信息，请核实重要代码变更。
      </p>
    </div>
  );
}
