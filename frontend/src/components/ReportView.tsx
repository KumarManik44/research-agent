import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ReportViewProps {
  report: string;
  citations: Map<number, string>;
}

function injectCitationLinks(report: string, citations: Map<number, string>): string {
  return report.replace(/\[(\d+)\]/g, (_, n) => {
    const num = parseInt(n, 10);
    const url = citations.get(num);
    if (url) return `[${n}](${url})`;
    return `[${n}]`;
  });
}

export function ReportView({ report, citations }: ReportViewProps) {
  const processed = injectCitationLinks(report, citations);

  return (
    <article className="prose prose-invert prose-zinc max-w-none mt-8 prose-headings:font-semibold prose-a:text-amber-400 prose-a:no-underline hover:prose-a:text-amber-300 prose-a:transition-colors">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children, ...props }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-amber-400 hover:text-amber-300 no-underline"
              {...props}
            >
              {children}
            </a>
          ),
        }}
      >
        {processed}
      </ReactMarkdown>
    </article>
  );
}
