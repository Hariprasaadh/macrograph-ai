import React, { Children, cloneElement, isValidElement, memo, type ReactElement, type ReactNode } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CopyButton } from './CopyButton';
import { MermaidDiagram } from '../MermaidDiagram';
import { ScrollableTable, useTableLayout } from './ScrollableTable';
import {
  isNumericText,
  numericColumns,
  signedDirection,
  statusTone,
  textOf,
  type HastNode,
  type StatusTone,
} from './cellFormat';

interface MarkdownMessageProps {
  content: string;
  isStreaming?: boolean;
}

interface CellExtras {
  colIndex?: number;
}

const STICKY_FIRST_COLUMN_MIN_COLS = 5;

const TONE_CLASSES: Record<StatusTone, string> = {
  good: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300',
  warn: 'border-amber-400/30 bg-amber-400/10 text-amber-300',
  bad: 'border-rose-400/30 bg-rose-400/10 text-rose-300',
  neutral: 'border-white/10 bg-white/5 text-slate-300',
};

const StatusPill: React.FC<{ tone: StatusTone; label: string }> = ({ tone, label }) => (
  <span
    className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide ${TONE_CLASSES[tone]}`}
  >
    <span className="h-1.5 w-1.5 rounded-full bg-current" />
    {label}
  </span>
);

function CodeBlock({ language, code }: { language: string; code: string }): React.ReactElement {
  if (language === 'mermaid') return <MermaidDiagram code={code} title="Causal Transmission Path" />;
  return (
    <figure className="my-4 overflow-hidden rounded-xl border border-white/10 bg-slate-950/80">
      <figcaption className="flex items-center justify-between border-b border-white/5 bg-white/[0.03] px-3 py-1.5">
        <span className="font-mono text-[10.5px] uppercase tracking-wider text-slate-500">{language || 'text'}</span>
        <CopyButton text={code} />
      </figcaption>
      <pre className="overflow-x-auto p-3.5 text-[12.5px] leading-relaxed [scrollbar-width:thin]">
        <code className="font-mono text-slate-200">{code}</code>
      </pre>
    </figure>
  );
}

function renderCell(children: ReactNode, numeric: boolean): ReactNode {
  const text = textOf(children).trim();
  const tone = statusTone(text);
  if (tone) return <StatusPill tone={tone} label={text.replace(/[`*]/g, '').replace(/_/g, ' ')} />;
  if (numeric && isNumericText(text)) {
    const direction = signedDirection(text);
    const color = direction > 0 ? 'text-emerald-300' : direction < 0 ? 'text-rose-300' : 'text-slate-100';
    return <span className={`font-mono font-medium tabular-nums [&_strong]:text-inherit ${color}`}>{children}</span>;
  }
  return children;
}

const COMPONENTS: Components = {
  h1: ({ node, ...props }) => (
    <h1 {...props} className="mb-4 mt-1 border-b border-white/10 pb-3 text-xl font-bold tracking-tight text-white sm:text-[22px]" />
  ),
  h2: ({ node, ...props }) => (
    <h2
      {...props}
      className="mb-3 mt-7 flex items-center gap-2.5 text-[15px] font-semibold tracking-tight text-white before:h-4 before:w-1 before:shrink-0 before:rounded-full before:bg-gradient-to-b before:from-brand-300 before:to-brand-600 before:content-['']"
    />
  ),
  h3: ({ node, ...props }) => <h3 {...props} className="mb-2 mt-5 text-sm font-semibold text-cyan-300" />,
  h4: ({ node, ...props }) => (
    <h4 {...props} className="mb-1.5 mt-4 text-[11px] font-semibold uppercase tracking-wider text-slate-400" />
  ),
  p: ({ node, ...props }) => <p {...props} className="my-3 leading-7 text-slate-300 first:mt-0 last:mb-0" />,
  strong: ({ node, ...props }) => <strong {...props} className="font-semibold text-white" />,
  em: ({ node, ...props }) => <em {...props} className="text-slate-200" />,
  ul: ({ node, ...props }) => (
    <ul {...props} className="my-3 list-disc space-y-1.5 pl-5 marker:text-cyan-400/70 [&_ol]:mt-1.5 [&_ul]:mt-1.5" />
  ),
  ol: ({ node, ...props }) => (
    <ol
      {...props}
      className="my-3 list-decimal space-y-1.5 pl-5 marker:font-mono marker:text-cyan-300/80 [&_ol]:mt-1.5 [&_ul]:mt-1.5"
    />
  ),
  li: ({ node, ...props }) => <li {...props} className="pl-1 leading-7 text-slate-300" />,
  hr: ({ node, ...props }) => (
    <hr {...props} className="my-6 h-px border-0 bg-gradient-to-r from-transparent via-white/15 to-transparent" />
  ),
  blockquote: ({ node, ...props }) => (
    <blockquote
      {...props}
      className="my-4 rounded-r-xl border-l-2 border-amber-400/70 bg-amber-400/[0.06] px-4 py-2.5 text-[13px] text-amber-100/90 [&>p]:my-1"
    />
  ),
  a: ({ node, href, children, ...props }) =>
    // react-markdown strips unsafe URLs (e.g. javascript:); render those as plain text, not as links.
    href ? (
      <a
        {...props}
        href={href}
        target="_blank"
        rel="noreferrer noopener"
        className="font-medium text-cyan-300 underline decoration-cyan-400/30 underline-offset-4 transition-colors hover:text-cyan-200 hover:decoration-cyan-300"
      >
        {children}
      </a>
    ) : (
      <span>{children}</span>
    ),
  img: ({ alt }) => <span className="text-slate-500">[image: {alt || 'omitted'}]</span>,
  pre: ({ children }) => <>{children}</>,
  code: ({ node, className, children, ...props }) => {
    const text = textOf(children).replace(/\n$/, '');
    const language = /language-([\w-]+)/.exec(className ?? '')?.[1] ?? '';
    if (language || text.includes('\n')) return <CodeBlock language={language} code={text} />;
    return (
      <code
        {...props}
        className="rounded-md border border-white/[0.07] bg-slate-800/60 px-1.5 py-0.5 font-mono text-[0.82em] text-cyan-300 [overflow-wrap:anywhere]"
      >
        {children}
      </code>
    );
  },
  table: ({ node, children }) => {
    const numeric = numericColumns(node as unknown as HastNode);
    return (
      <ScrollableTable layout={{ numeric, stickyFirstColumn: numeric.length >= STICKY_FIRST_COLUMN_MIN_COLS }}>
        {children}
      </ScrollableTable>
    );
  },
  thead: ({ node, ...props }) => <thead {...props} />,
  tbody: ({ node, ...props }) => <tbody {...props} />,
  tr: ({ node, children, ...props }) => {
    const cells = Children.toArray(children).filter(isValidElement) as ReactElement<CellExtras>[];
    return (
      <tr {...props} className="transition-colors even:bg-white/[0.025] hover:bg-cyan-400/[0.05]">
        {cells.map((cell, index) => cloneElement(cell, { colIndex: index }))}
      </tr>
    );
  },
  th: ({ children, colIndex }: React.ComponentPropsWithoutRef<'th'> & CellExtras) => {
    const layout = useTableLayout();
    const numeric = layout.numeric[colIndex ?? -1] ?? false;
    const sticky = layout.stickyFirstColumn && colIndex === 0;
    return (
      <th
        scope="col"
        className={`whitespace-nowrap border-b border-white/10 bg-slate-900 px-3.5 py-2.5 text-[10.5px] font-semibold uppercase tracking-wider text-slate-400 ${
          numeric ? 'text-right' : 'text-left'
        } ${sticky ? 'sticky left-0 z-[1]' : ''}`}
      >
        {children}
      </th>
    );
  },
  td: ({ children, colIndex }: React.ComponentPropsWithoutRef<'td'> & CellExtras) => {
    const layout = useTableLayout();
    const numeric = layout.numeric[colIndex ?? -1] ?? false;
    const sticky = layout.stickyFirstColumn && colIndex === 0;
    return (
      <td
        className={`max-w-[26rem] border-b border-white/[0.05] px-3.5 py-2.5 align-top text-slate-300 [overflow-wrap:anywhere] ${
          numeric ? 'whitespace-nowrap text-right' : ''
        } ${sticky ? 'sticky left-0 z-[1] bg-slate-950 font-medium text-slate-100' : ''}`}
      >
        {renderCell(children, numeric)}
      </td>
    );
  },
};

const REMARK_PLUGINS = [remarkGfm];

export const MarkdownMessage: React.FC<MarkdownMessageProps> = memo(({ content, isStreaming = false }) => (
  <div className="min-w-0 max-w-full text-[14px] text-slate-300 [overflow-wrap:break-word]">
    <ReactMarkdown remarkPlugins={REMARK_PLUGINS} components={COMPONENTS}>
      {content}
    </ReactMarkdown>
    {isStreaming && (
      <span aria-hidden="true" className="ml-0.5 inline-block h-4 w-[3px] translate-y-0.5 animate-pulse rounded-sm bg-cyan-400" />
    )}
  </div>
));
MarkdownMessage.displayName = 'MarkdownMessage';
