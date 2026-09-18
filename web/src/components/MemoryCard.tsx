import type { Memory, PlaceCandidate } from '../types';

const statusLabel = {
  resolved: 'Place identified',
  needs_review: 'Choose a match',
  unresolved: "Couldn't identify",
} as const;

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
  const unresolvedWithoutName = memory.resolution_status === 'unresolved' && !memory.hint?.name;
  const title = displayPlace?.name
    || memory.hint?.name
    || (unresolvedWithoutName ? 'Unidentified place' : memory.source_text);

  return (
    <article className="memory-card">
      <div className="memory-topline">
        <span className={`status ${memory.resolution_status}`}>
          {statusLabel[memory.resolution_status]}
        </span>
        <span className="source">{memory.source_type}</span>
      </div>

      <h3>{title}</h3>
      {displayPlace?.formatted_address && <p>{displayPlace.formatted_address}</p>}

      {displayPlace && (
        <p className="muted">
          {score != null ? `match score ${Math.round(score * 100)}% · ` : ''}
          {memory.resolution_method === 'manual' ? 'confirmed by you' : 'auto-resolved'}
          {' · '}source {displayPlace.provider}
        </p>
      )}

      {unresolvedWithoutName && (
        <p className="source-evidence">{memory.source_text}</p>
      )}

      {memory.resolution_status === 'needs_review' && memory.candidates.length > 0 && (
        <div className="candidate-list">
          <div className="candidate-heading">
            <strong>Suggested matches</strong>
            <span>Choose the place you meant.</span>
          </div>
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
          <button className="reject" onClick={() => onReject(memory)}>
            None of these places
          </button>
        </div>
      )}

      <button className="delete" onClick={() => onDelete(memory)}>remove save</button>
    </article>
  );
}
