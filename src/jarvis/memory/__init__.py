"""Memory / Conversation Manager module (Phase 0 stub).

Per Section 4 & Section 8:
- Memory/Conversation Manager owns: Conversation history (short-lived) +
  persistent preferences (long-lived), write policy.
- Memory/Conversation Manager does NOT own: Current task execution state (that's State Manager).
- Receives: Read/write requests.
- Returns: Relevant memory/conversation slice.
- Called by: Planner, Intent Manager, Context Budget Manager.
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class MemorySlice(BaseModel):
    conversation: List[Dict[str, Any]] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)


class MemoryManager:
    """Memory / Conversation Manager stub."""

    def __init__(self) -> None:
        self._conversation: List[Dict[str, Any]] = []
        self._preferences: Dict[str, Any] = {}

    def get_slice(self) -> MemorySlice:
        return MemorySlice(conversation=list(self._conversation), preferences=dict(self._preferences))

    def add_message(self, role: str, content: str) -> None:
        self._conversation.append({"role": role, "content": content})


_default_memory_manager = None


def get_memory_manager() -> MemoryManager:
    global _default_memory_manager
    if _default_memory_manager is None:
        _default_memory_manager = MemoryManager()
    return _default_memory_manager
