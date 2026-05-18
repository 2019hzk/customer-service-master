from dataclasses import dataclass


@dataclass(slots=True)
class FlowStepLink:
    target: str

@dataclass(slots=True)
class StaticLink(FlowStepLink):
    pass


@dataclass(slots=True)
class ConditionalLink(FlowStepLink):
    condition: str


@dataclass(slots=True)
class FallbackLink(FlowStepLink):
    pass