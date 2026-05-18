import json
from dataclasses import asdict
from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.domain.state import DialogueState
from atguigu.infrastructure.llm import llm
from atguigu.knowledge.intents import KnowledgeIntent
from atguigu.plan.models import TurnPlan
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.prompt_loader import load_prompt
from atguigu.task.flow.models import FlowsList, Flow


class TurnPlanner:
    async def predict(
            self,
            state: DialogueState,
            flows: FlowsList,
            knowledge_intents: dict[str, KnowledgeIntent],
    ) -> TurnPlan:
        prompt_inputs = self._build_prompt_inputs(state, flows, knowledge_intents)
        return await self._predict_from_prompt_inputs(prompt_inputs)

    def _build_prompt_inputs(
            self,
            state: DialogueState,
            flows: FlowsList,
            knowledge_intents: dict[str, KnowledgeIntent]
    ) -> dict[str, Any]:
        user_message = HistoryBuilder._render_user_message(state.pending_turn.user_message)
        history = HistoryBuilder.build(state.current_session().turns)
        active_task = state.active_task
        focused_object = state.focused_object
        _flows: list[Flow] = flows.flows
        return {
            "current_conversation": history,
            "user_message": user_message,
            "available_flows_json": json.dumps(
                {
                    "flows": [{k: v for k, v in asdict(flow).items() if k != "steps"} for flow in _flows]
                },
                ensure_ascii=False,
            ),
            "active_task_json": json.dumps(
                asdict(active_task) if active_task is not None else None,
                ensure_ascii=False,
            ),
            "interrupted_tasks_json": json.dumps(
                [asdict(task) for task in state.paused_tasks],
                ensure_ascii=False,
            ),
            "focused_object_json": json.dumps(
                asdict(focused_object) if focused_object is not None else None,
                ensure_ascii=False,
            ),
            "knowledge_intents_json": json.dumps(
                [
                    {"id": intent.id, "description": intent.description}
                    for intent in knowledge_intents.values()
                ],
                ensure_ascii=False,
            ),
        }

    async def _predict_from_prompt_inputs(
            self,
            prompt_inputs: dict[str, Any],
    ) -> TurnPlan:
        prompt_text = load_prompt("turn_plan")
        prompt = PromptTemplate.from_template(
            prompt_text,
            template_format="jinja2"
        )

        chain = prompt | llm | JsonOutputParser()
        llm_output = await chain.ainvoke(prompt_inputs)
        return TurnPlan.from_dict(llm_output)
