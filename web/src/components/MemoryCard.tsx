import type { Memory, PlaceCandidate } from '../types';

export function MemoryCard({
  memory,
  onConfirm,
  onReject,
  onDelete,
}: {
  memory: Memory;
  onConfirm: (memory: Memory, candidate: PlaceCandidate) => void;
  onReject: (memory: Memory) => void;
  onDelete: (memory: Memory) => void;
}) {
  const displayPlace = memory.resolution_status === 'resolved' ? memory.place : null;
  const score = memory.pre_resolution_confidence ?? displayPlace?.confidence ?? null;

  return (
    <article className="memory-card">
      <div className="memory-topline">
        <span className={`status ${memory.resolution_status}`}>{memory.resolution_status}</span>
        <span className="source">{memory.source_type}</span>
      </div>
      <h3>{displayPlace?.name || memory.hint?.name || memory.source_text}</h3>
      {displayPlace?.formatted_address && <p>{displayPlace.formatted_address}</p>}
      {displayPlace && (
        <p className="muted">
          {score != null ? `match ${Math.round(score * 100)}% · ` : ''}
          {memory.resolution_method === 'manual' ? 'confirmed by you' : 'auto-resolved'}
          {' · '}source {displayPlace.provider}
        </p>
      )}
      {memory.resolution_status === 'needs_review' && memory.candidates.length > 0 && (
        <div className="candidate-list">
          <p className="muted">choose the right match</p>
          {memory.candidates.map((candidate) => (
            <button
              className="secondary candidate"
              key={candidate.place_id}
              onClick={() => onConfirm(memory, candidate)}
            >
              <span>{candidate.name}</span>
              {candidate.formatted_address && <small>{candidate.formatted_address}</small>}
            </button>
          ))}
          <button className="secondary" onClick={() => onReject(memory)}>
            none of these
          </button>
        </div>
      )}
      <button className="delete" onClick={() => onDelete(memory)}>remove</button>
    </article>
  );
}
