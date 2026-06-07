export type NodeType =
  | 'input'
  | 'if'
  | 'action'
  | 'output'
  | 'agent'
  | 'start'
  | 'end';

export type FieldDataType =
  | 'string'
  | 'number'
  | 'boolean'
  | 'object'
  | 'array'
  | 'date';

export interface InputFieldRow {
  id: string;
  field: string;
  store_as: string;
  type: FieldDataType;
}

export interface OutputFieldRow {
  id: string;
  field: string;
  type: FieldDataType;
}

export interface IfCondition {
  left: string;
  operator: string;
  right: string;
}

export interface RFNodeData {
  label?: string;

  /** INPUT node — list of incoming field mappings */
  inputFields?: InputFieldRow[];

  /** IF node */
  ifCondition?: IfCondition;

  /** OUTPUT node */
  outputFields?: OutputFieldRow[];

  /** ACTION node */
  actionOperation?: string;
  actionInputs?: string;
  actionOutput?: string;

  /** AGENT node */
  selectedAgentId?: string;
  agentInputs?: string;
  agentOutput?: string;
  agentOutputPath?: string;
}

export interface RFEdgeData {
  branch?: 'branch1' | 'branch2';
  condition?: string;
  label?: string;
}

export const FIELD_TYPE_OPTIONS: FieldDataType[] = [
  'string',
  'number',
  'boolean',
  'object',
  'array',
  'date',
];

export const IF_OPERATOR_OPTIONS = [
  { value: '==', label: 'equals (==)' },
  { value: '!=', label: 'not equals (!=)' },
  { value: '>', label: 'greater than (>)' },
  { value: '<', label: 'less than (<)' },
  { value: '>=', label: 'greater or equal (>=)' },
  { value: '<=', label: 'less or equal (<=)' },
  { value: 'contains', label: 'contains' },
  { value: 'starts_with', label: 'starts with' },
  { value: 'ends_with', label: 'ends with' },
  { value: 'is_empty', label: 'is empty' },
  { value: 'is_not_empty', label: 'is not empty' },
] as const;

export interface WorkflowMetadata {
  workflow_id: string;
  workflow_type: string;
  task_queue: string;
  version: string;
  description: string;
}

export interface ExecutionRun {
  run_id: string;
  workflow_id: string;
  status: string;
  start_time?: string;
  close_time?: string | null;
  workflow_type?: string;
}

export interface NodeTraceState {
  status: string;
  input?: unknown;
  output?: unknown;
  error?: string;
  duration_seconds?: number;
}
