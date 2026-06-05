"use client";

import type { ReactElement } from "react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";

import { useTheme } from "@/components/ThemeProvider";

function CodeBlock({
  language,
  children,
}: {
  language: string;
  children: string;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";

  return (
    <div className="not-prose my-4 overflow-hidden rounded-xl border border-border bg-muted/40">
      <div className="flex items-center border-b border-border px-4 py-2">
        <span className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
          {language || "text"}
        </span>
      </div>
      <SyntaxHighlighter
        language={language || "text"}
        style={isDark ? oneDark : oneLight}
        PreTag="div"
        customStyle={{
          margin: 0,
          padding: "1rem",
          background: "transparent",
          fontSize: "0.8125rem",
          lineHeight: "1.6",
        }}
        codeTagProps={{
          style: {
            fontFamily: "var(--font-geist-mono), ui-monospace, monospace",
          },
        }}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  );
}

function buildMarkdownComponents(): Components {
  return {
    h1: ({ children }) => (
      <h1 className="mb-3 mt-2 text-lg font-semibold tracking-tight">{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="mb-2 mt-5 text-base font-semibold tracking-tight first:mt-0">
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="mb-2 mt-4 text-sm font-semibold first:mt-0">{children}</h3>
    ),
    p: ({ children }) => (
      <p className="mb-4 leading-7 last:mb-0 [&+h2]:mt-6 [&+h3]:mt-5">{children}</p>
    ),
    ul: ({ children }) => (
      <ul className="mb-4 ml-5 list-disc space-y-2 last:mb-0">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="mb-4 ml-5 list-decimal space-y-2 last:mb-0">{children}</ol>
    ),
    li: ({ children }) => <li className="leading-7">{children}</li>,
    blockquote: ({ children }) => (
      <blockquote className="mb-4 border-l-2 border-primary/40 pl-4 text-muted-foreground last:mb-0">
        {children}
      </blockquote>
    ),
    hr: () => <hr className="my-6 border-border/60" />,
    a: ({ href, children }) => (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="text-primary underline-offset-2 hover:underline"
      >
        {children}
      </a>
    ),
    code: ({ className, children }) => {
      const text = String(children).replace(/\n$/, "");

      if (!className && !text.includes("\n")) {
        return (
          <code className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[0.8125rem] text-foreground">
            {text}
          </code>
        );
      }

      return <code className={className}>{text}</code>;
    },
    pre: ({ children }) => {
      const child = children as ReactElement<{
        className?: string;
        children?: string;
      }>;
      const className = child?.props?.className ?? "";
      const language = /language-(\w+)/.exec(className)?.[1] ?? "text";
      const code = String(child?.props?.children ?? "").replace(/\n$/, "");

      if (!code.includes("\n") && !className) {
        return <pre className="mb-4 overflow-x-auto">{children}</pre>;
      }

      return <CodeBlock language={language}>{code}</CodeBlock>;
    },
    table: ({ children }) => (
      <div className="mb-4 overflow-x-auto last:mb-0">
        <table className="w-full border-collapse text-sm">{children}</table>
      </div>
    ),
    th: ({ children }) => (
      <th className="border border-border bg-muted/40 px-3 py-2 text-left font-medium">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="border border-border px-3 py-2">{children}</td>
    ),
  };
}

interface MarkdownContentProps {
  content: string;
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div className="chat-prose break-words">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={buildMarkdownComponents()}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
