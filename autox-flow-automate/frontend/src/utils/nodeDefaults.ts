import type { NodeType, RFNodeData } from '../types';

const TYPE_LABELS: Record<NodeType, string> = {
  start: 'START',
  end: 'END',
  input: 'INPUT',
  if: 'IF',
  action: 'ACTION',
  output: 'OUTPUT',
  agent: 'AGENT',
};

export function getDefaultNodeData(type: NodeType): RFNodeData {
  const label = TYPE_LABELS[type];

  switch (type) {
    case 'input':
      return { label, inputFields: [] };
    case 'if':
      return {
        label,
        ifCondition: { left: '', operator: '==', right: '' },
      };
    case 'output':
      return { label, outputFields: [] };
    case 'action':
      return {
        label,
        actionOperation: '',
        actionInputs: '',
        actionOutput: '',
      };
    case 'agent':
      return { label, selectedAgentId: '' };
    case 'start':
    case 'end':
      return { label };
    default:
      return { label };
  }
}

export function getNodeDisplayLabel(data: RFNodeData, type?: string): string {
  if (data.label) return data.label;
  if (type) return TYPE_LABELS[type as NodeType] || type;
  return 'Node';
}
