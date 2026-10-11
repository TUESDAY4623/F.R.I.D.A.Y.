"""Event Logger module.

First real component in the modular monolith per Section 13 & 16.
"""

from jarvis.logger.event_logger import EventLogger, get_logger, set_logger
from jarvis.logger.events import EventSensitivity, EventType, LogEvent, LogLevel

__all__ = [
    "EventLogger",
    "get_logger",
    "set_logger",
    "LogEvent",
    "EventType",
    "LogLevel",
    "EventSensitivity",
]
