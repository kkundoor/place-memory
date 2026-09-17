import type { FeasibleMemory, Memory, PlaceCandidate } from '../types';

const base = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000');

type IngestResponse = {
  memory: Memory;
  candidates: PlaceCandidate[];
  warning?: string;
};

export async function listMemories(): Promise<Memory[]> {
  const response = await fetch(`${base}/api/memories`);
  if (!response.ok) throw new Error('could not load memories');
  return response.json();
}

export async function deleteMemory(memoryId: string): Promise<void> {
  const response = await fetch(`${base}/api/memories/${memoryId}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('could not delete memory');
}

export async function ingestMemory(sourceText: string, sourceUrl: string): Promise<IngestResponse> {
  const response = await fetch(`${base}/api/memories/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_type: sourceUrl ? 'link' : 'note',
      source_text: sourceText,
      source_url: sourceUrl || null,
    }),
  });
  if (!response.ok) throw new Error('could not ingest memory');
  return response.json();
}

export async function ingestImage(file: File, sourceUrl: string): Promise<IngestResponse> {
  const body = new FormData();
  body.append('image', file);
  if (sourceUrl) body.append('source_url', sourceUrl);

  const response = await fetch(`${base}/api/memories/ingest-image`, {
    method: 'POST',
    body,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'could not ingest image');
  }
  return response.json();
}

export async function confirmMemory(memory: Memory, candidate: PlaceCandidate): Promise<Memory> {
  const response = await fetch(`${base}/api/memories/${memory.id}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(candidate),
  });
  if (!response.ok) throw new Error('could not confirm place');
  return response.json();
}

export async function getFeasible(
  query: string,
  latitude: number,
  longitude: number,
  availableMinutes: number,
): Promise<FeasibleMemory[]> {
  const response = await fetch(`${base}/api/feasible`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      origin: { latitude, longitude },
      available_minutes: availableMinutes,
    }),
  });
  if (!response.ok) throw new Error('could not check feasibility');
  const data = await response.json();
  return data.results;
}


export async function getMap(
  query: string,
  latitude: number,
  longitude: number,
  availableMinutes: number,
): Promise<string> {
  const response = await fetch(`${base}/api/map`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      origin: { latitude, longitude },
      available_minutes: availableMinutes,
    }),
  });
  if (!response.ok) throw new Error('could not load map');
  const data = await response.json();
  return `data:image/png;base64,${data.image_base64}`;
}
