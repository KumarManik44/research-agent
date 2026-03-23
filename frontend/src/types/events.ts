export type StreamEvent =
  | { event: 'status'; timestamp: string; phase: string; message: string }
  | { event: 'search_started'; timestamp: string; query: string }
  | {
      event: 'search_result';
      timestamp: string;
      citation_id: number;
      title: string;
      url: string;
      snippet: string;
      score?: number;
    }
  | { event: 'synthesis_started'; timestamp: string }
  | { event: 'final_report'; timestamp: string; report: string }
  | { event: 'error'; timestamp: string; message: string }
  | { event: 'done'; timestamp: string };

export type ResearchStatus = 'idle' | 'submitting' | 'streaming' | 'done' | 'error';
