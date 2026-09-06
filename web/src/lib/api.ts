import type { FeasibleMemory, Memory } from '../types';

const base = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function listMemories(): Promise<Memory[]> {
  const response = await fetch(`${base}/api/memories`);
  if (!response.ok) throw new Error('could not load memories');
  return response.json();
}

export async function createMemory(sourceText: string, sourceUrl: string): Promise<Memory> {
  const response = await fetch(`${base}/api/memories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_type: sourceUrl ? 'link' : 'note',
      source_text: sourceText,
      source_url: sourceUrl || null,
    }),
  });
  if (!response.ok) throw new Error('could not save memory');
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
