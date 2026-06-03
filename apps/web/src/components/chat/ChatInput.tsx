"use client";

import { KeyboardEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

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

  const submit = () => {
    if (!value.trim()) return;
    onSend(value);
    setValue("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="space-y-3 border-t bg-background p-4">
      <Textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="输入问题，Enter 发送，Shift+Enter 换行"
        rows={3}
        disabled={disabled}
      />
      <div className="flex justify-end gap-2">
        {isLoading ? (
          <Button variant="outline" onClick={onStop}>
            停止
          </Button>
        ) : null}
        <Button onClick={submit} disabled={disabled || !value.trim()}>
          发送
        </Button>
      </div>
    </div>
  );
}
