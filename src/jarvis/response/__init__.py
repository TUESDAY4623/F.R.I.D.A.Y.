"""Response Manager module (Phase 0 stub).

Per Section 4 & Section 10:
- Response Manager owns: Formatting agent result for output, routing to text UI and/or TTS.
- Response Manager does NOT own: STT, intent.
- Receives: Task result.
- Returns: Rendered response.
- Called by: Orchestrator.
(To be fully implemented by Tanmay in Phase 1 & 7).
"""

from typing import Any, Dict


class ResponseManager:
    """Response Manager stub."""

    def format_response(self, result: Dict[str, Any]) -> str:
        return f"Jarvis: Task finished with result: {result}"


_default_response_manager = None


def get_response_manager() -> ResponseManager:
    global _default_response_manager
    if _default_response_manager is None:
        _default_response_manager = ResponseManager()
    return _default_response_manager
