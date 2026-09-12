"""Intent / Context Manager module (Phase 0 stub).

Per Section 4:
- Intent/Context Manager owns: Determining what the user wants, flagging ambiguity.
- Intent/Context Manager does NOT own: Planning, execution.
- Receives: Normalized input, conversation history.
- Returns: Intent + entities, or clarification request.
- Called by: Input Processor.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IntentResult(BaseModel):
    intent: str
    entities: Dict[str, Any] = Field(default_factory=dict)
    is_ambiguous: bool = False
    clarification_prompt: Optional[str] = None


class IntentManager:
    """Intent / Context Manager stub."""

    def detect_intent(self, text: str, history: Optional[List[Any]] = None) -> IntentResult:
        return IntentResult(
            intent=text,
            entities={},
            is_ambiguous=False,
        )
