from dataclasses import dataclass, field
from threading import RLock
from uuid import uuid4


@dataclass(slots=True)
class SessionMessage:
    role: str
    content: str


@dataclass(slots=True)
class ConversationTurn:
    question: str
    answer: str
    evidence: list[str]


@dataclass(slots=True)
class SessionState:
    session_id: str
    messages: list[SessionMessage] = field(default_factory=list)
    confirmed_drug_id: str | None = None
    confirmed_drug_name: str | None = None
    pending_drug_ids: list[str] = field(default_factory=list)
    rejected_drug_ids: list[str] = field(default_factory=list)
    switch_pending: bool = False
    pending_question: str | None = None
    turns: list[ConversationTurn] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(SessionMessage(role=role, content=content))

    def recent_complete_turns(self, limit: int) -> list[SessionMessage]:
        messages: list[SessionMessage] = []
        for turn in self.turns[-limit:]:
            messages.append(SessionMessage(role="user", content=turn.question))
            messages.append(SessionMessage(role="assistant", content=turn.answer))
        return messages

    def begin_question(self, question: str) -> None:
        self.pending_question = question
        self.add_message("user", question)

    def continue_question(self, clarification: str) -> None:
        self.add_message("user", clarification)

    def set_pending(self, drug_ids: list[str]) -> None:
        self.pending_drug_ids = drug_ids

    def confirm_drug(self, drug_id: str, drug_name: str) -> None:
        self.confirmed_drug_id = drug_id
        self.confirmed_drug_name = drug_name
        self.pending_drug_ids = []
        self.rejected_drug_ids = []
        self.switch_pending = False

    def begin_drug_switch(self) -> None:
        self.switch_pending = True

    def clear_confirmed_drug(self) -> None:
        self.confirmed_drug_id = None
        self.confirmed_drug_name = None

    def reject_drug(self, drug_id: str) -> None:
        if drug_id not in self.rejected_drug_ids:
            self.rejected_drug_ids.append(drug_id)
        self.pending_drug_ids = [
            pending_id
            for pending_id in self.pending_drug_ids
            if pending_id != drug_id
        ]

    def complete_answer(self, answer: str, evidence: list[str]) -> None:
        if self.pending_question is not None:
            self.turns.append(
                ConversationTurn(
                    question=self.pending_question,
                    answer=answer,
                    evidence=evidence,
                )
            )
        self.add_message("assistant", answer)
        self.pending_question = None
        self.switch_pending = False


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
