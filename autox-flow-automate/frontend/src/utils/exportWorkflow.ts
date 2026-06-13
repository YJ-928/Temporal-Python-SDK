import type { Node, Edge } from 'reactflow';
import type { RFNodeData, RFEdgeData, NodeType } from '../types';
import { getAgentById } from '../constants/agents';

const TYPE_LABEL: Record<NodeType, string> = {
  start: 'START',
  end: 'END',
  input: 'INPUT',
  if: 'IF',
  action: 'ACTION',
  output: 'OUTPUT',
  agent: 'AGENT',
};

function cleanVarName(name: string): string {
  if (!name) return name;
  return name.replace(/^(ctx\.|context\.)/, '');
}

export type ExportedWorkflowNode =
  | {
      id: string;
      type: 'START' | 'END';
      data: { label: string };
    }
  | {
      id: string;
      type: 'INPUT';
      data: {
        label: string;
        inputs: Array<{ field: string; store_as: string; type: string }>;
      };
    }
  | {
      id: string;
      type: 'IF';
      data: {
        label: string;
        left: string;
        operator: string;
        right: string;
      };
    }
  | {
      id: string;
      type: 'OUTPUT';
      data: {
        label: string;
        outputs: Array<{ field: string; type: string }>;
      };
    }
  | {
      id: string;
      type: 'ACTION';
      data: {
        label: string;
        operation: string;
        inputs: Record<string, string>;
        output: string;
      };
    }
  | {
      id: string;
      type: 'AGENT';
      data: {
        label: string;
        agent: string;
        inputs?: Record<string, string>;
        output?: string;
        output_path?: string;
      };
    };

export interface ExportedWorkflowPayload {
  version: string;
  nodes: ExportedWorkflowNode[];
  edges: Array<{
    id: string;
    source: string;
    target: string;
    sourceHandle?: string | null;
    targetHandle?: string | null;
    label?: string;
    branch?: string;
    condition?: string;
  }>;
}

export function serializeNodeForExport(node: Node<RFNodeData>): ExportedWorkflowNode {
  const typeKey = (node.type || 'start') as NodeType;
  const label = node.data.label ?? TYPE_LABEL[typeKey];

  switch (node.type) {
    case 'input':
      return {
        id: node.id,
        type: 'INPUT',
        data: {
          label,
          inputs: (node.data.inputFields ?? []).map(({ field, store_as, type: fieldType }) => ({
            field,
            store_as: cleanVarName(store_as),
            type: fieldType,
          })),
        },
      };

    case 'if': {
      const cond = node.data.ifCondition;
      return {
        id: node.id,
        type: 'IF',
        data: {
          label,
          left: cleanVarName(cond?.left ?? ''),
          operator: cond?.operator ?? '',
          right: typeof cond?.right === 'string' ? cleanVarName(cond.right) : (cond?.right ?? ''),
        },
      };
    }

    case 'output':
      return {
        id: node.id,
        type: 'OUTPUT',
        data: {
          label,
          outputs: (node.data.outputFields ?? []).map(({ field, type: fieldType }) => ({
            field: cleanVarName(field),
            type: fieldType,
          })),
        },
      };

    case 'action': {
      let parsedInputs: Record<string, string> = {};
      if (node.data.actionInputs) {
        try {
          const parsed = JSON.parse(node.data.actionInputs);
          if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
            Object.keys(parsed).forEach((key) => {
              const val = parsed[key];
              parsedInputs[key] = typeof val === 'string' ? cleanVarName(val) : String(val);
            });
          }
        } catch {
          parsedInputs = {};
        }
      }

      return {
        id: node.id,
        type: 'ACTION',
        data: {
          label,
          operation: node.data.actionOperation ?? '',
          inputs: parsedInputs,
          output: cleanVarName(node.data.actionOutput ?? ''),
        },
      };
    }

    case 'agent': {
      const agentRecord = getAgentById(node.data.selectedAgentId);
      let parsedInputs: Record<string, string> = {};
      if (node.data.agentInputs) {
        try {
          const parsed = JSON.parse(node.data.agentInputs);
          if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
            Object.keys(parsed).forEach((key) => {
              const val = parsed[key];
              parsedInputs[key] = typeof val === 'string' ? cleanVarName(val) : String(val);
            });
          }
        } catch {
          parsedInputs = {};
        }
      }

      return {
        id: node.id,
        type: 'AGENT',
        data: {
          label,
          agent: agentRecord?.id ?? node.data.selectedAgentId ?? '',
          inputs: parsedInputs,
          output: cleanVarName(node.data.agentOutput ?? ''),
          output_path: node.data.agentOutputPath ? cleanVarName(node.data.agentOutputPath) : undefined,
        },
      };
    }

    case 'end':
      return {
        id: node.id,
        type: 'END',
        data: { label },
      };

    case 'start':
    default:
      return {
        id: node.id,
        type: 'START',
        data: { label },
      };
  }
}

export function buildExportPayload(
  nodes: Node<RFNodeData>[],
  edges: Edge<RFEdgeData>[]
): ExportedWorkflowPayload {
  return {
    version: '1.0.0',
    nodes: nodes.map(serializeNodeForExport),
    edges: edges.map((e) => {
      let branchVal: string | undefined = undefined;
      const rawBranch = e.data?.branch || e.sourceHandle;
      if (rawBranch === 'branch1' || rawBranch === 'true') {
        branchVal = 'true';
      } else if (rawBranch === 'branch2' || rawBranch === 'false') {
        branchVal = 'false';
      }
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle,
        targetHandle: e.targetHandle,
        label: typeof e.label === 'string' ? e.label : undefined,
        branch: branchVal,
        condition: e.data?.condition,
      };
    }),
  };
}
