import { useEffect, useRef } from 'react';
import type { StreamEvent } from '../types/events';
import { EventItem } from './EventItem';

interface ProgressFeedProps {
  events: StreamEvent[];
}

export function ProgressFeed({ events }: ProgressFeedProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  return (
    <div className="bg-zinc-900/50 rounded-lg border border-zinc-800 max-h-80 overflow-y-auto">
      {events.length === 0 ? (
        <div className="py-6 px-4 text-center text-zinc-500 text-sm">Waiting for events...</div>
      ) : (
        <div className="divide-y divide-zinc-800/50">
          {events.map((ev, i) => (
            <EventItem key={`${ev.event}-${ev.timestamp}-${i}`} event={ev} />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
