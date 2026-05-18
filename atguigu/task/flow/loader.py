from pathlib import Path

import yaml

from atguigu.task.flow.models import FlowsList, FlowSlot, Flow
from atguigu.task.flow.steps import FlowStep, CollectSlotStep


class FlowLoader:

    def load_many(self, paths: list[Path]) -> FlowsList:
        flows: list[Flow] = []
        slots: dict[str, FlowSlot] = {}
        for path in paths:
            flows_list: FlowsList = self.load(path)
            flows.extend(flows_list.flows)
            slots.update(flows_list.slots)
        return FlowsList(flows=flows, slots=slots)

    def load(self, path: Path) -> FlowsList:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        slots = self._load_slots(data.get('slots', {}))
        flows = self._load_flows(data.get('flows', {}), slots)
        return FlowsList(flows=flows, slots=slots)

    def _load_slots(self, slots_data: dict[str, dict]) -> dict[str, FlowSlot]:
        slots = {}
        for slot_name, slot_data in slots_data.items():
            slots[slot_name] = FlowSlot(**slot_data, name=slot_name)
        return slots

    def _load_flows(self, flows_data: dict[str, dict], slots: dict[str, FlowSlot]) -> list[Flow]:
        flows: list[Flow] = []
        for flow_id, flow_data in flows_data.items():
            steps: list[FlowStep] = [FlowStep.from_dict(step_data) for step_data in flow_data['steps']]
            flow_slots: list[FlowSlot] = []
            for step in steps:
                if isinstance(step, CollectSlotStep):
                    flow_slots.append(slots[step.slot_name])

            flow = Flow(
                id=flow_id,
                name=flow_data['name'],
                description=flow_data['description'],
                steps=steps,
                slots=flow_slots
            )
            flows.append(flow)
        return flows


if __name__ == '__main__':
    base_path = Path(__file__).parents[3]
    user_flow_path = base_path / 'flow_config' / 'user_flows.yml'
    system_flow_path = base_path / 'flow_config' / 'system_flows.yml'
    loader = FlowLoader()
    flows_list = loader.load_many([user_flow_path, system_flow_path])
    print(flows_list)
