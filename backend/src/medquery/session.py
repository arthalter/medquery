from dataclasses import dataclass
from threading import RLock
from uuid import uuid4


@dataclass(slots=True)
class SessionState:
    session_id: str


class InMemorySessionStore:
    """进程内会话仓库；进程重启即清空。"""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._lock = RLock()

    def create(self) -> SessionState:
        state = SessionState(session_id=str(uuid4()))
        with self._lock:
            self._sessions[state.session_id] = state
        return state

    def get(self, session_id: str) -> SessionState | None:
        with self._lock:
            return self._sessions.get(session_id)
