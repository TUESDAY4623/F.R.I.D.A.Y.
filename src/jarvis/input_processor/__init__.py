"""Input Processor module (Phase 0 stub).

Per Section 4 & Section 10.1:
- Input Processor owns: Audio capture, wake-word detection, VAD, STT,
  text normalization, capturing cancel signal (hotkey/voice).
- Input Processor does NOT own: Intent understanding.
- Receives: Raw audio/text, cancel gesture.
- Returns: Normalized text, cancel event.
- Called by: User.
"""

from typing import Optional
from pydantic import BaseModel


class NormalizedInput(BaseModel):
    text: str
    is_cancel_signal: bool = False
    source: str = "text"


class InputProcessor:
    """Input Processor stub."""

    def process_text(self, raw_text: str) -> NormalizedInput:
        normalized = raw_text.strip()
        is_cancel = normalized.lower() in ("cancel", "stop", "abort")
        return NormalizedInput(text=normalized, is_cancel_signal=is_cancel, source="text")
