from dataclasses import dataclass, field
from threading import RLock
from uuid import uuid4


@dataclass(slots=True)
class SessionMessage:
    role: str
    content: str


@dataclass(slots=True)
class SessionState:
    session_id: str
    messages: list[SessionMessage] = field(default_factory=list)
    confirmed_drug_id: str | None = None
    confirmed_drug_name: str | None = None
    pending_drug_ids: list[str] = field(default_factory=list)
    rejected_drug_ids: list[str] = field(default_factory=list)
    pending_question: str | None = None

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(SessionMessage(role=role, content=content))

    def recent_complete_turns(self, limit: int) -> list[SessionMessage]:
        turns: list[tuple[SessionMessage, SessionMessage]] = []
        pending_user: SessionMessage | None = None
        for message in self.messages:
            if message.role == "user":
                pending_user = message
                continue
            if message.role == "assistant" and pending_user is not None:
                turns.append((pending_user, message))
                pending_user = None
        return [message for turn in turns[-limit:] for message in turn]

    def set_pending(self, drug_ids: list[str]) -> None:
        self.pending_drug_ids = drug_ids

    def set_pending_question(self, question: str) -> None:
        self.pending_question = question

    def confirm_drug(self, drug_id: str, drug_name: str) -> None:
        self.confirmed_drug_id = drug_id
        self.confirmed_drug_name = drug_name
        self.pending_drug_ids = []
        self.rejected_drug_ids = []

    def reject_drug(self, drug_id: str) -> None:
        if drug_id not in self.rejected_drug_ids:
            self.rejected_drug_ids.append(drug_id)
        self.pending_drug_ids = [
            pending_id
            for pending_id in self.pending_drug_ids
            if pending_id != drug_id
        ]

    def complete_answer(self, answer: str) -> None:
        self.add_message("assistant", answer)
        self.pending_question = None


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
