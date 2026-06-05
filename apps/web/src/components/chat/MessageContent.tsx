import { MarkdownContent } from "@/components/chat/MarkdownContent";
import type { MessageRole } from "@/lib/chat-protocol";

interface MessageContentProps {
  role: MessageRole;
  content: string;
}

function PlainContent({ content }: { content: string }) {
  return (
    <div className="whitespace-pre-wrap break-words text-[0.9375rem] leading-7">
      {content}
    </div>
  );
}

/** user → plain；assistant → markdown */
export function MessageContent({ role, content }: MessageContentProps) {
  if (role === "user") {
    return <PlainContent content={content} />;
  }
  return <MarkdownContent content={content} />;
}
