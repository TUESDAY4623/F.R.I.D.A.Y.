"""Intent / Context Manager module (Phase 1).

Per Section 4:
- Intent/Context Manager owns: Determining what the user wants, parsing parameters, flagging ambiguity.
- Intent/Context Manager does NOT own: Planning, execution, tool invocation.
- Receives: Normalized input, conversation history, read-only memory.
- Returns: Structured IntentResult (intent + action_type + entities + context).
- Called by: Input Processor / Orchestrator.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from jarvis.memory import MemoryManager, get_memory_manager


class IntentResult(BaseModel):
    """Structured representation of parsed user intent and extracted context."""

    intent: str
    action_type: str = "general"  # e.g., file_read, file_write, file_list, file_move, file_pipeline, general
    entities: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    is_ambiguous: bool = False
    clarification_prompt: Optional[str] = None
    raw_text: str = ""


class IntentManager:
    """Intent and Context Manager for Phase 1 Core Brain."""

    def __init__(self, memory_manager: Optional[MemoryManager] = None) -> None:
        self._memory_manager = memory_manager

    @property
    def memory_manager(self) -> Optional[MemoryManager]:
        return self._memory_manager

    def detect_intent(
        self,
        text: str,
        history: Optional[List[Any]] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> IntentResult:
        """Parse raw text input into a structured IntentResult.

        Reads conversation history and user preferences from MemoryManager
        in a read-only manner. Never executes tools or mutates Memory.
        """
        raw = text.strip() if text else ""

        # Check for empty or ambiguous input
        if not raw:
            return IntentResult(
                intent="",
                action_type="general",
                is_ambiguous=True,
                clarification_prompt="No command provided. Please enter a request.",
                raw_text=text,
            )

        # Collect read-only context from memory manager if available
        context_data: Dict[str, Any] = dict(extra_context or {})
        if self._memory_manager is not None:
            mem_slice = self._memory_manager.get_slice()
            context_data["user_preferences"] = mem_slice.preferences
            context_data["conversation_history"] = mem_slice.conversation
        elif history:
            context_data["conversation_history"] = list(history)

        lowered = raw.lower()

        # 1. Pattern: File Pipeline (Read earnings/report and save/write summary)
        # e.g., "read earnings report earnings.txt and save summary to summary.txt"
        pipeline_match = re.search(
            r"(?:read|process|analyze)\s+(?:(?:earnings|annual|quarterly|financial)\s+)?(?:report\s+|file\s+)?[\"']?([^\s\"']+)[\"']?\s+and\s+(?:save|write)\s+summary\s+to\s+[\"']?([^\s\"']+)[\"']?",
            raw,
            re.IGNORECASE,
        )
        if pipeline_match:
            source_path = pipeline_match.group(1)
            target_path = pipeline_match.group(2)
            return IntentResult(
                intent=raw,
                action_type="file_pipeline",
                entities={
                    "source_path": source_path,
                    "target_path": target_path,
                    "operation": "summarize_and_save",
                },
                context=context_data,
                raw_text=raw,
            )

        # 2. Pattern: Create directory / folder
        # e.g., "Create a directory called test", "Create directory test", "Make a new folder called test"
        create_dir_match = re.search(
            r"^(?:create|make)\s+(?:a\s+)?(?:new\s+)?(?:directory|folder|dir)(?:\s+called)?\s+(?:\"([^\"]+)\"|'([^']+)'|(.*))$",
            raw,
            re.IGNORECASE,
        )
        if create_dir_match:
            dir_path = (
                create_dir_match.group(1)
                or create_dir_match.group(2)
                or create_dir_match.group(3)
                or ""
            ).strip()
            if dir_path:
                return IntentResult(
                    intent=raw,
                    action_type="create_directory",
                    entities={"path": dir_path},
                    context=context_data,
                    raw_text=raw,
                )

        # 3. Pattern: Move/Rename file
        # e.g., "move file old.txt to new.txt", 'move file "A.txt" to "My Folder"', "Move file A to directory B", "move file from A to B"
        move_match = re.search(
            r"^(?:move|rename)\s+(?:file\s+)?(?:from\s+)?(?:\"([^\"]+)\"|'([^']+)'|(.+?))\s+to\s+(?:\"([^\"]+)\"|'([^']+)'|(.+))$",
            raw,
            re.IGNORECASE,
        )
        if move_match:
            src = (
                move_match.group(1)
                or move_match.group(2)
                or move_match.group(3)
                or ""
            ).strip()
            dest = (
                move_match.group(4)
                or move_match.group(5)
                or move_match.group(6)
                or ""
            ).strip()
            if src and dest:
                return IntentResult(
                    intent=raw,
                    action_type="file_move",
                    entities={
                        "source": src,
                        "destination": dest,
                        "source_path": src,
                        "destination_path": dest,
                    },
                    context=context_data,
                    raw_text=raw,
                )

        # 4. Pattern: Write file
        # Format 4a: "write 'Hello Jarvis' to test.txt" or 'write "content" to file path'
        write_to_match = re.search(
            r"^write\s+(?:content\s+)?(?:\"([^\"]+)\"|'([^']+)')\s+to\s+(?:file\s+)?(?:\"([^\"]+)\"|'([^']+)'|(.*))$",
            raw,
            re.IGNORECASE | re.DOTALL,
        )
        if write_to_match:
            content = (
                write_to_match.group(1) or write_to_match.group(2) or ""
            ).strip()
            path = (
                write_to_match.group(3)
                or write_to_match.group(4)
                or write_to_match.group(5)
                or ""
            ).strip()
            return IntentResult(
                intent=raw,
                action_type="file_write",
                entities={"path": path, "content": content},
                context=context_data,
                raw_text=raw,
            )

        # Format 4b: "write file C:\path\out.txt with content Hello World"
        write_match = re.search(
            r"^write\s+(?:to\s+|file\s+)?[\"']?(.*?)[\"']?\s+with\s+content\s+(.*)$",
            raw,
            re.IGNORECASE | re.DOTALL,
        )
        if not write_match:
            write_match = re.search(
                r"^write\s+(?:to\s+|file\s+)?[\"']?([^\s\"':]+)[\"']?\s*:\s*(.*)$",
                raw,
                re.IGNORECASE | re.DOTALL,
            )
        if write_match:
            path = write_match.group(1).strip()
            content = write_match.group(2).strip()
            return IntentResult(
                intent=raw,
                action_type="file_write",
                entities={"path": path, "content": content},
                context=context_data,
                raw_text=raw,
            )

        # 5. Pattern: Read file
        # e.g., "read file C:\path\with spaces\notes.txt"
        read_match = re.search(
            r"^(?:read\s+file|read|cat|view\s+file)\s+[\"']?(.*?)[\"']?$",
            raw,
            re.IGNORECASE,
        )
        if read_match:
            path = read_match.group(1).strip()
            return IntentResult(
                intent=raw,
                action_type="file_read",
                entities={"path": path},
                context=context_data,
                raw_text=raw,
            )

        # 6. Pattern: List directory
        # e.g., "list directory C:\path\with spaces\folder", "List files in this directory"
        list_match = re.search(
            r"^(?:list\s+(?:files\s+in\s+)?directory|list\s+files\s+in\s+this\s+directory|list\s+files\s+in|list\s+dir|list|ls|dir)\s*[\"']?(.*?)[\"']?$",
            raw,
            re.IGNORECASE,
        )
        if list_match:
            path = list_match.group(1).strip()
            if not path or path.lower() in (
                "this directory",
                "here",
                "current directory",
                ".",
            ):
                path = "."
            return IntentResult(
                intent=raw,
                action_type="file_list",
                entities={"path": path},
                context=context_data,
                raw_text=raw,
            )

        # Default fallback: general intent (preserves Phase 0 stub and Hello Loop behavior)
        return IntentResult(
            intent=raw,
            action_type="general",
            entities={},
            context=context_data,
            is_ambiguous=False,
            raw_text=raw,
        )


_default_intent_manager: Optional[IntentManager] = None


def get_intent_manager() -> IntentManager:
    """Return the shared singleton IntentManager."""
    global _default_intent_manager
    if _default_intent_manager is None:
        _default_intent_manager = IntentManager()
    return _default_intent_manager
