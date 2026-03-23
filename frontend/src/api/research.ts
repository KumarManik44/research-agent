const API_BASE = import.meta.env.VITE_API_BASE || '';

export interface ResearchJobResponse {
  job_id: string;
  stream_url: string;
}

export async function startResearch(topic: string): Promise<ResearchJobResponse> {
  const res = await fetch(`${API_BASE}/api/v1/research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to start research: ${res.status}`);
  }
  return res.json();
}
