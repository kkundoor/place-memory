import type { Memory } from '../types';

export function MemoryCard({
  memory,
  onConfirm,
}: {
  memory: Memory;
  onConfirm: (memory: Memory) => void;
}) {
  return (
    <article className="memory-card">
      <div className="memory-topline">
        <span className={`status ${memory.resolution_status}`}>{memory.resolution_status}</span>
        <span className="source">{memory.source_type}</span>
      </div>
      <h3>{memory.place?.name || memory.hint?.name || memory.source_text}</h3>
      {memory.place?.formatted_address && <p>{memory.place.formatted_address}</p>}
      {memory.place && (
        <p className="muted">confidence {Math.round(memory.place.confidence * 100)}%</p>
      )}
      {memory.resolution_status === 'needs_review' && memory.place && (
        <button className="secondary" onClick={() => onConfirm(memory)}>confirm this place</button>
      )}
    </article>
  );
}
