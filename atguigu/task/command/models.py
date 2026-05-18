from dataclasses import dataclass
from typing import Any


@dataclass
class Command:
    command: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Command":
        clz = COMMAND_NAME_TO_CLASS[data["command"]]
        return clz(**data)


@dataclass
class StartFlowCommand(Command):
    flow: str


@dataclass
class SetSlotsCommand(Command):
    slots: dict[str, Any]


@dataclass
class CancelFlowCommand(Command):
    pass


@dataclass
class ResumeFlowCommand(Command):
    flow: str


COMMAND_NAME_TO_CLASS = {
    "start_flow": StartFlowCommand,
    "set_slots": SetSlotsCommand,
    "cancel_flow": CancelFlowCommand,
    "resume_flow": ResumeFlowCommand
}

if __name__ == '__main__':
    command = {"command": "set_slots", "slots": {"order_number": "10001"}}
    print(Command.from_dict(command))
