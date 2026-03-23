import { useCallback, useState } from 'react';
import { startResearch } from './api/research';
import { TopicInput } from './components/TopicInput';
import { ProgressFeed } from './components/ProgressFeed';
import { ReportView } from './components/ReportView';
import { useResearchStream } from './hooks/useResearchStream';
import type { StreamEvent } from './types/events';

export default function App() {
  const [status, setStatus] = useState<'idle' | 'submitting' | 'streaming' | 'done' | 'error'>('idle');
  const [topic, setTopic] = useState('');
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [report, setReport] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [citations, setCitations] = useState<Map<number, string>>(new Map());

  const handleEvent = useCallback((ev: StreamEvent) => {
    setEvents((prev) => [...prev, ev]);
    if (ev.event === 'search_result') {
      setCitations((prev) => {
        const next = new Map(prev);
        next.set(ev.citation_id, ev.url);
        return next;
      });
    }
    if (ev.event === 'final_report') {
      setReport(ev.report);
    }
  }, []);

  const { connect } = useResearchStream({
    onEvent: handleEvent,
    onError: (msg) => {
      setError(msg);
      setStatus('error');
    },
    onDone: () => {
      setStatus('done');
    },
  });

  const handleSubmit = useCallback(
    async (t: string) => {
      setTopic(t);
      setError(null);
      setEvents([]);
      setReport(null);
      setCitations(new Map());
      setStatus('submitting');

      try {
        const { job_id } = await startResearch(t);
        setStatus('streaming');
        connect(job_id);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to start research');
        setStatus('error');
      }
    },
    [connect]
  );

  const isBusy = status === 'submitting' || status === 'streaming';

  return (
    <div className="min-h-screen bg-zinc-950">
      <div className="max-w-3xl mx-auto px-6 py-12">
        <header className="text-center mb-12">
          <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Research Agent</h1>
          <p className="text-zinc-500 mt-1 text-sm">Enter a topic to generate a sourced report</p>
        </header>

        <div className="flex flex-col items-center gap-8">
          <div className="w-full max-w-xl">
            <TopicInput onSubmit={handleSubmit} disabled={isBusy} />
          </div>

          {error && (
            <div className="w-full max-w-xl p-4 rounded-lg bg-red-950/50 border border-red-900/50 text-red-400 text-sm">
              {error}
            </div>
          )}

          {(status === 'streaming' || status === 'done') && events.length > 0 && (
            <div className="w-full">
              <h2 className="text-sm font-medium text-zinc-500 mb-2">Progress</h2>
              <ProgressFeed events={events} />
            </div>
          )}

          {report && (
            <div className="w-full">
              <h2 className="text-sm font-medium text-zinc-500 mb-2">
                Report{topic ? `: ${topic}` : ''}
              </h2>
              <ReportView report={report} citations={citations} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
