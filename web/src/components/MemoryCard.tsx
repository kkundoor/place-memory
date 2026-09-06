import type { Memory } from '../types';

export function MemoryCard({ memory }: { memory: Memory }) {
  return (
    <article className="memory-card">
      <div className="memory-topline">
        <span className={`status ${memory.resolution_status}`}>{memory.resolution_status}</span>
        <span className="source">{memory.source_type}</span>
      </div>
      <h3>{memory.place?.name || memory.source_text}</h3>
      {memory.place?.formatted_address && <p>{memory.place.formatted_address}</p>}
      {memory.place && (
        <p className="muted">confidence {Math.round(memory.place.confidence * 100)}%</p>
      )}
    </article>
  );
}
