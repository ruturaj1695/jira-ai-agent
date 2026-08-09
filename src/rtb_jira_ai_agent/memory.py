from __future__ import annotations

from collections import defaultdict, deque


class ConversationMemory:
    """In-process demo memory; replace with Redis/database for multi-instance deployment."""

    def __init__(self, max_messages: int = 10) -> None:
        self._store: dict[str, deque[dict[str, str]]] = defaultdict(
            lambda: deque(maxlen=max_messages)
        )

    def history(self, conversation_id: str) -> list[dict[str, str]]:
        return list(self._store[conversation_id])

    def append(self, conversation_id: str, role: str, content: str) -> None:
        self._store[conversation_id].append({"role": role, "content": content})


conversation_memory = ConversationMemory()
