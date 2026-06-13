import type { ExportedWorkflowNode, ExportedWorkflowPayload } from '../utils/exportWorkflow';
import type { ExecutionRun, NodeTraceState } from '../types';
import { ApiError } from '../utils/errorHandler';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export interface CompilePayload {
  nodes: ExportedWorkflowNode[];
  edges: ExportedWorkflowPayload['edges'];
  workflow_id?: string;
  workflow_type?: string;
  task_queue?: string;
  version?: string;
  description?: string;
}

export interface CompileResponse {
  success: boolean;
  workflow_id: string;
  dsl: Record<string, unknown>;
  file_path: string;
  content_hash: string;
  generated_at?: string;
}

export interface ExecuteResponse {
  run_id: string;
  workflow_id: string;
  status?: string;
}

export interface HistoryResponse {
  executions: ExecutionRun[];
}

export interface TraceResponse {
  steps: Record<string, NodeTraceState>;
  status: string;
}

interface PydanticErrorItem {
  loc?: unknown[];
  msg?: string;
}

async function parseError(response: Response): Promise<ApiError> {
  let detail: string | undefined;
  try {
    const data = await response.json();
    const raw = data.detail || data.message;
    if (Array.isArray(raw)) {
      detail = (raw as PydanticErrorItem[])
        .map((e) => {
          const last = Array.isArray(e.loc) ? e.loc.at(-1) : undefined;
          const field = (typeof last === 'string' || typeof last === 'number') ? String(last) : '';
          const msg: string = e.msg || 'Invalid value';
          return field ? `${field}: ${msg}` : msg;
        })
        .join('; ');
    } else if (typeof raw === 'string') {
      detail = raw;
    }
  } catch {
    // body not JSON
  }
  return new ApiError(
    detail || `HTTP error ${response.status}`,
    response.status,
    detail,
  );
}

export const compilerApi = {
  async compileWorkflow(payload: CompilePayload): Promise<CompileResponse> {
    const url = `${API_BASE_URL}/api/v1/workflows/compile`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nodes: payload.nodes,
        edges: payload.edges,
        workflow_id: payload.workflow_id || 'workflow-design',
        workflow_type: payload.workflow_type ?? import.meta.env.VITE_WORKFLOW_TYPE ?? 'flowautomate',
        task_queue: payload.task_queue ?? import.meta.env.VITE_TASK_QUEUE ?? 'flowautomate',
        version: payload.version || '1.0.0',
        description: payload.description || '',
      }),
    });
    if (!response.ok) throw await parseError(response);
    return response.json() as Promise<CompileResponse>;
  },

  async executeWorkflow(workflowId: string, dslHash: string, input: Record<string, unknown> = {}): Promise<ExecuteResponse> {
    const url = `${API_BASE_URL}/api/v1/executions/${workflowId}/execute`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dsl_hash: dslHash, input }),
    });
    if (!response.ok) throw await parseError(response);
    return response.json() as Promise<ExecuteResponse>;
  },

  async getHistory(workflowId: string): Promise<HistoryResponse> {
    const url = `${API_BASE_URL}/api/v1/executions/${workflowId}/history`;
    const response = await fetch(url);
    if (!response.ok) throw await parseError(response);
    return response.json() as Promise<HistoryResponse>;
  },

  async getTrace(workflowId: string, runId: string): Promise<TraceResponse> {
    const url = `${API_BASE_URL}/api/v1/executions/${workflowId}/${runId}/trace`;
    const response = await fetch(url);
    if (!response.ok) throw await parseError(response);
    return response.json() as Promise<TraceResponse>;
  },

  async cancelWorkflow(workflowId: string, runId: string): Promise<{ success: boolean }> {
    const url = `${API_BASE_URL}/api/v1/executions/${workflowId}/${runId}/cancel`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw await parseError(response);
    return response.json() as Promise<{ success: boolean }>;
  },

  async terminateWorkflow(workflowId: string, runId: string, reason = 'Terminated by user'): Promise<{ success: boolean }> {
    const url = `${API_BASE_URL}/api/v1/executions/${workflowId}/${runId}/terminate?reason=${encodeURIComponent(reason)}`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw await parseError(response);
    return response.json() as Promise<{ success: boolean }>;
  },
};
