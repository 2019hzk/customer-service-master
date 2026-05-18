from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any

from atguigu.task.flow.links import FlowStepLink, StaticLink, ConditionalLink, FallbackLink


class FlowStepType(Enum):
    START = "start"
    ACTION = "action"
    COLLECT = "collect"
    END = "end"


@dataclass(slots=True)
class ResponseDefinition:
    mode: str = "static"
    text: str | None = None
    prompt: str | None = None


@dataclass(slots=True)
class SlotValidation:
    condition: str | None = None
    failure_response: ResponseDefinition | None = None


@dataclass(slots=True)
class FlowStep:
    id: str
    type: FlowStepType
    next: List[FlowStepLink] = field(default_factory=list)
    description: str = ""

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "FlowStep":
        step_type = step_data['type']
        clz = STEP_TYPE_TO_CLASS[step_type]
        return clz.from_dict(step_data)

    @staticmethod
    def base_fields(step_data: dict[str, Any]) -> dict[str, Any]:
        return {
            'id': step_data['id'],
            'type': FlowStepType(step_data['type']),
            'description': step_data.get('description', ""),
            'next': FlowStep.build_links(step_data['next'])
        }

    @staticmethod
    def build_links(next_data: str | list) -> list[FlowStepLink]:
        if isinstance(next_data, str):
            return [StaticLink(target=next_data)]
        else:
            links = []
            for link_data in next_data:
                if 'if' in link_data:
                    links.append(ConditionalLink(target=link_data['then'], condition=link_data['if']))
                else:
                    links.append(FallbackLink(target=link_data['else']))
            return links


@dataclass(slots=True)
class StartFlowStep(FlowStep):

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "StartFlowStep":
        return cls(**FlowStep.base_fields(step_data))


@dataclass(slots=True)
class ActionFlowStep(FlowStep):
    action: str = ""
    args: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "ActionFlowStep":
        return cls(**FlowStep.base_fields(step_data),
                   action=step_data['action'],
                   args=step_data.get('args', {}))


@dataclass(slots=True)
class CollectSlotStep(FlowStep):
    slot_name: str = ""
    response: ResponseDefinition = field(default_factory=ResponseDefinition)
    validation: SlotValidation | None = None

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "CollectSlotStep":
        return cls(
            **FlowStep.base_fields(step_data),
            slot_name=step_data['slot_name'],
            response=ResponseDefinition(**step_data['response']),
            validation=SlotValidation(condition=step_data['validation']['condition'],
                                      failure_response=ResponseDefinition(**step_data['validation'][
                                          'failure_response'])) if 'validation' in step_data else None
        )


@dataclass(slots=True)
class EndFlowStep(FlowStep):

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "EndFlowStep":
        return cls(**FlowStep.base_fields(step_data))


STEP_TYPE_TO_CLASS = {
    "start": StartFlowStep,
    "action": ActionFlowStep,
    "collect": CollectSlotStep,
    "end": EndFlowStep
}
