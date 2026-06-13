import { StartNode, EndNode, InputNode, IfNode, ActionNode, OutputNode, AgentNode } from '../components/CustomNodes';

export const nodeTypes = {
  start: StartNode,
  end: EndNode,
  input: InputNode,
  if: IfNode,
  action: ActionNode,
  output: OutputNode,
  agent: AgentNode,
};
