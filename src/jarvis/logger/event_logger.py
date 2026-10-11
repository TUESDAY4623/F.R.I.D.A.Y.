"""Event Logger implementation.

Per Section 13 (Logging Architecture):
- Structured, redacted event log for every lifecycle/tool/policy/approval/error event.
- Mandatory constraints:
  - Never log passwords, API keys, tokens, or raw credentials.
  - Screenshots/raw observations are not retained permanently by default.
  - Log levels and retention are configurable, not fixed.
- Provides live streaming subscription for UI / log viewer components.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import threading
from collections import deque
from pathlib import Path
from typing import Any, Callable, List, Optional

from jarvis.logger.events import EventSensitivity, EventType, LogEvent, LogLevel


SENSITIVE_KEY_PATTERNS = [
    re.compile(r"pass(word)?", re.IGNORECASE),
    re.compile(r"api[-_]?key", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"auth(orization)?", re.IGNORECASE),
    re.compile(r"bearer", re.IGNORECASE),
    re.compile(r"private[-_]?key", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
]

REDACTED_VALUE = "[REDACTED]"


def sanitize_value(val: Any) -> Any:
    """Recursively sanitize a dictionary or list, masking sensitive fields."""
    if isinstance(val, dict):
        sanitized = {}
        for k, v in val.items():
            if any(pat.search(str(k)) for pat in SENSITIVE_KEY_PATTERNS):
                sanitized[k] = REDACTED_VALUE
            else:
                sanitized[k] = sanitize_value(v)
        return sanitized
    elif isinstance(val, list):
        return [sanitize_value(item) for item in val]
    elif isinstance(val, str):
        # Basic pattern match for bearer tokens or key=value strings
        for pat in SENSITIVE_KEY_PATTERNS:
            if pat.search(val) and ("=" in val or ":" in val):
                # Mask entire string if it contains sensitive key assignments
                return REDACTED_VALUE
        return val
    return val


class EventLogger:
    """First real component: Thread-safe, structured, redacted Event Logger."""

    def __init__(
        self,
        min_level: LogLevel = LogLevel.INFO,
        max_memory_events: int = 5000,
        log_file_path: Optional[Path | str] = None,
        console_output: bool = True,
    ) -> None:
        self._min_level = min_level
        self._max_memory_events = max_memory_events
        self._log_file_path = Path(log_file_path) if log_file_path else None
        self._console_output = console_output
        self._lock = threading.RLock()
        self._events: deque[LogEvent] = deque(maxlen=max_memory_events)
        self._subscribers: List[Callable[[LogEvent], None]] = []

        if self._log_file_path:
            self._log_file_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def min_level(self) -> LogLevel:
        return self._min_level

    @min_level.setter
    def min_level(self, level: LogLevel) -> None:
        with self._lock:
            self._min_level = level

    def add_subscriber(self, callback: Callable[[LogEvent], None]) -> None:
        """Register a subscriber callback for streaming live events (e.g. for UI log pane)."""
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def remove_subscriber(self, callback: Callable[[LogEvent], None]) -> None:
        """Remove an existing subscriber callback."""
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def _level_num(self, level: LogLevel) -> int:
        levels = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARNING: 30,
            LogLevel.ERROR: 40,
            LogLevel.CRITICAL: 50,
        }
        return levels.get(level, 20)

    def log(self, event: LogEvent) -> LogEvent:
        """Ingest, redact, store, persist, and dispatch a structured event."""
        # Sanitize payload to enforce sensitive data constraints
        sanitized_payload = sanitize_value(event.payload)
        is_redacted = sanitized_payload != event.payload

        sanitized_event = event.model_copy(
            update={
                "payload": sanitized_payload,
                "redacted": is_redacted or event.redacted,
            }
        )

        with self._lock:
            if self._level_num(sanitized_event.level) >= self._level_num(self._min_level):
                self._events.append(sanitized_event)

                if self._console_output:
                    print(sanitized_event.to_log_line(), file=sys.stderr, flush=True)

                if self._log_file_path:
                    try:
                        with open(self._log_file_path, "a", encoding="utf-8") as f:
                            f.write(sanitized_event.model_dump_json() + "\n")
                    except Exception as e:
                        print(f"Failed to write to log file: {e}", file=sys.stderr)

                for subscriber in list(self._subscribers):
                    try:
                        subscriber(sanitized_event)
                    except Exception as err:
                        print(f"Error in event subscriber {subscriber}: {err}", file=sys.stderr)

        return sanitized_event

    def log_event(
        self,
        event_type: EventType,
        source: str,
        message: str,
        task_id: Optional[str] = None,
        step_name: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        level: LogLevel = LogLevel.INFO,
        sensitivity: EventSensitivity = EventSensitivity.NORMAL,
    ) -> LogEvent:
        """Convenience method to construct and record an event."""
        event = LogEvent(
            task_id=task_id,
            step_name=step_name,
            event_type=event_type,
            level=level,
            source=source,
            message=message,
            payload=payload or {},
            sensitivity=sensitivity,
        )
        return self.log(event)

    def log_step(
        self,
        step_name: str,
        task_id: Optional[str] = None,
        message: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
    ) -> LogEvent:
        """Convenience method for logging Orchestrator loop steps."""
        msg = message or f"Executed step: {step_name}"
        return self.log_event(
            event_type=EventType.ORCHESTRATOR_STEP,
            source="orchestrator",
            message=msg,
            task_id=task_id,
            step_name=step_name,
            payload=payload or {},
            level=LogLevel.INFO,
        )

    def get_events(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        min_level: Optional[LogLevel] = None,
    ) -> List[LogEvent]:
        """Query buffered in-memory events."""
        with self._lock:
            results = list(self._events)

        if task_id is not None:
            results = [e for e in results if e.task_id == task_id]
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        if min_level is not None:
            threshold = self._level_num(min_level)
            results = [e for e in results if self._level_num(e.level) >= threshold]

        return results

    def clear(self) -> None:
        """Clear buffered events."""
        with self._lock:
            self._events.clear()


# Default singleton instance for the process
_default_logger: Optional[EventLogger] = None
_logger_lock = threading.Lock()


def get_logger() -> EventLogger:
    """Obtain or initialize the process-wide default Event Logger."""
    global _default_logger
    with _logger_lock:
        if _default_logger is None:
            _default_logger = EventLogger()
        return _default_logger


def set_logger(logger: EventLogger) -> None:
    """Override the process-wide default Event Logger."""
    global _default_logger
    with _logger_lock:
        _default_logger = logger
