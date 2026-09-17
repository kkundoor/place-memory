import type { Memory, PlaceCandidate } from '../types';

export function MemoryCard({
  memory,
  onConfirm,
  onDelete,
}: {
  memory: Memory;
  onConfirm: (memory: Memory, candidate: PlaceCandidate) => void;
  onDelete: (memory: Memory) => void;
}) {
  const candidates = memory.candidates.length ? memory.candidates : memory.place ? [memory.place] : [];

  return (
    <article className="memory-card">
      <div className="memory-topline">
        <span className={`status ${memory.resolution_status}`}>{memory.resolution_status}</span>
        <span className="source">{memory.source_type}</span>
      </div>
      <h3>{memory.place?.name || memory.hint?.name || memory.source_text}</h3>
      {memory.place?.formatted_address && <p>{memory.place.formatted_address}</p>}
      {memory.place && (
        <p className="muted">
          confidence {Math.round(memory.place.confidence * 100)}% · source {memory.place.provider}
        </p>
      )}
      {memory.resolution_status === 'needs_review' && candidates.length > 0 && (
        <div className="candidate-list">
          <p className="muted">choose the right match</p>
          {candidates.map((candidate) => (
            <button
              className="secondary candidate"
              key={candidate.place_id}
              onClick={() => onConfirm(memory, candidate)}
            >
              <span>{candidate.name}</span>
              {candidate.formatted_address && <small>{candidate.formatted_address}</small>}
            </button>
          ))}
        </div>
      )}
      <button className="delete" onClick={() => onDelete(memory)}>remove</button>
    </article>
  );
}
