import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from atguigu.domain.contexts import TaskContext, SystemContext
from atguigu.domain.messages import UserMessage, BotMessage


@dataclass
class FocusedObject:
    type: str
    id: str
    title: str | None = None
    attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "id": self.id,
            "title": self.title,
            "attributes": self.attributes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FocusedObject":
        return cls(
            type=data["type"],
            id=data["id"],
            title=data["title"],
            attributes=data["attributes"],
        )


@dataclass
class Turn:
    turn_id: str
    user_message: UserMessage
    bot_messages: list[BotMessage]

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "user_message": self.user_message.to_dict(),
            "bot_messages": [msg.to_dict() for msg in self.bot_messages],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Turn":
        return cls(
            turn_id=data["turn_id"],
            user_message=UserMessage.from_dict(data["user_message"]),
            bot_messages=[BotMessage.from_dict(msg) for msg in data["bot_messages"]],
        )


@dataclass
class Session:
    session_id: str
    started_at: float
    last_activity_at: float
    closed_at: float | None = None
    turns: list[Turn] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "last_activity_at": self.last_activity_at,
            "closed_at": self.closed_at,
            "turns": [turn.to_dict() for turn in self.turns],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        return cls(
            session_id=data["session_id"],
            started_at=data["started_at"],
            last_activity_at=data["last_activity_at"],
            closed_at=data["closed_at"],
            turns=[Turn.from_dict(turn) for turn in data["turns"]],
        )


@dataclass
class DialogueState:
    sender_id: str
    active_task: TaskContext | None = None
    paused_tasks: list[TaskContext] = field(default_factory=list)
    active_system_task: SystemContext | None = None
    focused_object: FocusedObject | None = None
    sessions: list[Session] = field(default_factory=list)
    current_session_id: str | None = None
    pending_turn: Turn | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sender_id": self.sender_id,
            "active_task": self.active_task.to_dict() if self.active_task else None,
            "paused_tasks": [task.to_dict() for task in self.paused_tasks],
            "active_system_task": self.active_system_task.to_dict() if self.active_system_task else None,
            "focused_object": self.focused_object.to_dict() if self.focused_object else None,
            "sessions": [session.to_dict() for session in self.sessions],
            "current_session_id": self.current_session_id,
            "pending_turn": self.pending_turn.to_dict() if self.pending_turn else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DialogueState":
        return cls(
            sender_id=data["sender_id"],
            active_task=TaskContext.from_dict(data["active_task"]) if data["active_task"] else None,
            paused_tasks=[TaskContext.from_dict(task) for task in data["paused_tasks"]],
            active_system_task=SystemContext.from_dict(data["active_system_task"]) if data[
                "active_system_task"] else None,
            focused_object=FocusedObject.from_dict(data["focused_object"]) if data["focused_object"] else None,
            sessions=[Session.from_dict(session) for session in data["sessions"]],
            current_session_id=data["current_session_id"],
            pending_turn=Turn.from_dict(data["pending_turn"]) if data["pending_turn"] else None
        )

    def start_system_task(self, system_context: SystemContext):
        """
        启动系统任务
        :param system_context:
        :return:
        """
        self.active_system_task = system_context

    def end_system_task(self):
        """
        关闭当前的系统任务
        :return:
        """
        self.active_system_task = None

    def interrupt_active_task(self):
        """
        中断当前任务
        :return:
        """
        self.paused_tasks.append(self.active_task)
        self.active_task = None

    def start_task(self, task_context: TaskContext):
        """
        启动任务
        :param task_context:
        :return:
        """
        self.active_task = task_context

    def set_slots(self, slots: dict[str, Any]):
        """
        更新slots
        :param slots: set_slots command中的slots
        :return:
        """
        self.active_task.slots.update(slots)

    def cancel_active_task(self):
        self.active_task = None
        self.active_system_task = None

    def resume_task(self, flow_id: str | None = None) -> bool:
        if not self.paused_tasks:
            return False
        if flow_id is None:
            self.active_task = self.paused_tasks.pop()
            return True
        for i, task in enumerate(self.paused_tasks):
            if task.flow_id == flow_id:
                self.active_task = task
                del self.paused_tasks[i]
                return True
        return False

    def current_session(self) -> Session | None:
        for session in self.sessions:
            if session.session_id == self.current_session_id:
                return session
        return None

    def current_task(self):
        return self.active_system_task or self.active_task

    def remove_slot(self, slot_name: str):
        self.active_task.slots.pop(slot_name)

    def end_active_task(self):
        self.active_task = None

    def start_session(self):
        now = time.time()
        session = Session(session_id=str(uuid.uuid4()),
                          started_at=now,
                          last_activity_at=now)
        self.sessions.append(session)
        self.current_session_id = session.session_id

    def close_current_session(self):
        self.current_session().closed_at = time.time()
        self.current_session_id = None

    def reset_runtime_state_for_new_session(self):
        self.active_task = None
        self.active_system_task = None
        self.focused_object = None
        self.paused_tasks = []

    def begin_turn(self, message: UserMessage):
        self.pending_turn = Turn(
            turn_id=str(uuid.uuid4()),
            user_message=message,
            bot_messages=[]
        )

    def commit_pending_turn(self):
        self.current_session().turns.append(self.pending_turn)
        self.pending_turn = None

    def set_focused_object(self, object: FocusedObject):
        self.focused_object = object
