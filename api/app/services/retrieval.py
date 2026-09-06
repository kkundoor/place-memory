import re

from app.models import Memory, ResolutionStatus


STOP = {
    'a', 'an', 'and', 'are', 'around', 'at', 'can', 'did', 'do', 'for', 'from',
    'i', 'in', 'is', 'it', 'me', 'my', 'near', 'of', 'or', 'saved', 'show',
    'something', 'that', 'the', 'this', 'to', 'what', 'which', 'with',
}


def _terms(text: str) -> set[str]:
    words = re.findall(r'[a-z0-9]+', text.lower())
    return {word for word in words if word not in STOP and len(word) > 1}


def search_memories(memories: list[Memory], query: str) -> list[Memory]:
    resolved = [m for m in memories if m.resolution_status == ResolutionStatus.resolved and m.place]
    if not query.strip():
        return resolved

    query_terms = _terms(query)
    if not query_terms:
        return resolved

    scored = []
    for memory in resolved:
        place = memory.place
        text = ' '.join(filter(None, [
            memory.source_text,
            memory.note,
            place.name if place else None,
            place.formatted_address if place else None,
            place.primary_type if place else None,
            ' '.join(place.types) if place else None,
        ]))
        overlap = len(query_terms & _terms(text))
        if overlap:
            scored.append((overlap, memory))

    scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
    return [memory for _, memory in scored]
