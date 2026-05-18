from pathlib import Path

from atguigu.chitchat.handler import ChitchatHandler
from atguigu.chitchat.responder import ChitchatResponder
from atguigu.clarify.responder import ClarifyResponder
from atguigu.engine.dialogue_engine import DialogueEngine
from atguigu.knowledge.handler import KnowledgeHandler
from atguigu.knowledge.intents import KNOWLEDGE_INTENTS
from atguigu.knowledge.providers import ProductAPIProvider, OrderAPIProvider, FAQProvider, RAGProvider
from atguigu.knowledge.registry import KnowledgeProviderRegistry
from atguigu.knowledge.responder import KnowledgeResponder
from atguigu.plan.turn_planner import TurnPlanner
from atguigu.plan.validator import TurnPlanValidator
from atguigu.task.action.builder import build_action_runner
from atguigu.task.command.processor import CommandProcessor
from atguigu.task.flow.executor import FlowExecutor
from atguigu.task.flow.loader import FlowLoader
from atguigu.task.handler import TaskHandler

_PROJECT_ROOT = Path(__file__).parents[2]
_FLOW_CONFIG_DIR = _PROJECT_ROOT / "flow_config"
_FLOW_CONFIG_FILES = ("user_flows.yml", "system_flows.yml")


def build_dialogue_engine() -> DialogueEngine:
    flow_paths = [_FLOW_CONFIG_DIR / f for f in _FLOW_CONFIG_FILES]
    flows = FlowLoader().load_many(flow_paths)
    return DialogueEngine(
        turn_planner=TurnPlanner(),
        task_handler=TaskHandler(
            flows=flows,
            command_processor=CommandProcessor(),
            flow_executor=FlowExecutor(),
            action_runner=build_action_runner()
        ),
        knowledge_handler=KnowledgeHandler(
            knowledge_intents=KNOWLEDGE_INTENTS,
            knowledge_responder=KnowledgeResponder(),
            provider_registry=KnowledgeProviderRegistry(
                [
                    ProductAPIProvider(),
                    OrderAPIProvider(),
                    FAQProvider(),
                    RAGProvider(),
                ]
            ),
        ),
        chitchat_handler=ChitchatHandler(
            responder=ChitchatResponder()
        ),
        clarify_responder=ClarifyResponder(),
        turn_plan_validator=TurnPlanValidator()
    )
