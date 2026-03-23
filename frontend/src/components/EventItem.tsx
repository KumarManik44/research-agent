import type { StreamEvent } from '../types/events';

function formatTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '';
  }
}

function getMessage(ev: StreamEvent): string {
  switch (ev.event) {
    case 'status':
      return ev.message;
    case 'search_started':
      return `Searching: ${ev.query}`;
    case 'search_result':
      return `Found: ${ev.title}`;
    case 'synthesis_started':
      return 'Synthesizing report...';
    case 'final_report':
      return 'Report ready';
    case 'error':
      return ev.message;
    case 'done':
      return 'Done';
    default:
      return JSON.stringify(ev);
  }
}

function getIcon(ev: StreamEvent): string {
  switch (ev.event) {
    case 'status':
      return '○';
    case 'search_started':
      return '⌕';
    case 'search_result':
      return '≡';
    case 'synthesis_started':
      return '✎';
    case 'final_report':
      return '✓';
    case 'error':
      return '✗';
    case 'done':
      return '●';
    default:
      return '·';
  }
}

interface EventItemProps {
  event: StreamEvent;
}

export function EventItem({ event }: EventItemProps) {
  const isError = event.event === 'error';
  return (
    <div
      className={`flex gap-3 py-2 px-3 border-b border-zinc-800/50 last:border-0 text-sm ${
        isError ? 'text-red-400' : 'text-zinc-300'
      }`}
    >
      <span className="text-zinc-500 shrink-0 w-6 text-center" title={event.timestamp}>
        {getIcon(event)}
      </span>
      <span className="text-zinc-500 shrink-0 tabular-nums">{formatTime(event.timestamp)}</span>
      <span className="min-w-0 truncate">{getMessage(event)}</span>
    </div>
  );
}
