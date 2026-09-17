"""MCP adapter over Place Memory's deterministic domain services.

Run with:
    python -m app.mcp_server

The agent-facing layer intentionally does not decide canonical place identity. It only
exposes already-grounded memories and resolver explanations.
"""

from mcp.server.fastmcp import FastMCP

from app.main import store
from app.services.resolver import explain_resolution
from app.services.retrieval import search_memories


mcp = FastMCP('place-memory')


@mcp.tool()
def search_saved_places(query: str = '') -> list[dict]:
    """Search saved place memories using the application's deterministic retrieval path."""
    memories = store.list()
    results = search_memories(memories, query) if query else memories
    return [memory.model_dump(mode='json') for memory in results]


@mcp.tool()
def get_place_memory(memory_id: str) -> dict | None:
    """Return one saved memory, including its evidence, canonical place, and candidates."""
    memory = store.get(memory_id)
    return memory.model_dump(mode='json') if memory else None


@mcp.tool()
def explain_place_resolution(memory_id: str) -> dict:
    """Explain the confidence policy and evidence used for a saved place resolution."""
    memory = store.get(memory_id)
    if not memory:
        return {'error': 'memory not found', 'memory_id': memory_id}
    return {
        'memory_id': memory.id,
        'hint': memory.hint.model_dump() if memory.hint else None,
        **explain_resolution(memory.resolution_status, memory.candidates),
    }


if __name__ == '__main__':
    mcp.run()
