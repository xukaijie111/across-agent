import DOMPurify from "dompurify";
import { marked } from "marked";

marked.setOptions({
  gfm: true,
  breaks: true,
});

export function renderMarkdown(source: string): string {
  if (!source.trim()) {
    return "";
  }
  const html = marked.parse(source, { async: false }) as string;
  return DOMPurify.sanitize(html);
}
