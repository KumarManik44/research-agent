import { useCallback, useRef } from 'react';
import type { StreamEvent } from '../types/events';
const API_BASE = import.meta.env.VITE_API_BASE || '';

const EVENT_TYPES = [
  'status',
  'search_started',
  'search_result',
  'synthesis_started',
  'final_report',
  'error',
  'done',
] as const;

function parseEventData(data: string): StreamEvent {
  const parsed = JSON.parse(data) as Record<string, unknown>;
  return parsed as StreamEvent;
}

export interface UseResearchStreamResult {
  connect: (jobId: string) => void;
  disconnect: () => void;
  isConnected: boolean;
}

export interface UseResearchStreamCallbacks {
  onEvent: (ev: StreamEvent) => void;
  onError: (message: string) => void;
  onDone: () => void;
}

export function useResearchStream(callbacks: UseResearchStreamCallbacks): UseResearchStreamResult {
  const esRef = useRef<EventSource | null>(null);
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  const disconnect = useCallback(() => {
    const es = esRef.current;
    if (es) {
      es.close();
      esRef.current = null;
    }
  }, []);

  const connect = useCallback(
    (jobId: string) => {
      disconnect();
      const url = `${API_BASE}/api/v1/research/${jobId}/stream`;
      const es = new EventSource(url);
      esRef.current = es;

      const handleEvent = (e: MessageEvent) => {
        try {
          const ev = parseEventData(e.data);
          callbacksRef.current.onEvent(ev);
          if (ev.event === 'error') {
            callbacksRef.current.onError(ev.message);
            disconnect();
          }
          if (ev.event === 'done') {
            callbacksRef.current.onDone();
            disconnect();
          }
        } catch (err) {
          callbacksRef.current.onError(
            err instanceof Error ? err.message : 'Failed to parse event'
          );
          disconnect();
        }
      };

      for (const type of EVENT_TYPES) {
        es.addEventListener(type, handleEvent as EventListener);
      }

      es.onerror = () => {
        callbacksRef.current.onError('Connection lost');
        disconnect();
      };
    },
    [disconnect]
  );

  return {
    connect,
    disconnect,
    isConnected: esRef.current != null,
  };
}
