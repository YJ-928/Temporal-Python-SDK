import type { ExportedWorkflowNode } from '../utils/exportWorkflow';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export interface CompilePayload {
  nodes: ExportedWorkflowNode[];
  edges: any[];
  workflow_id?: string;
  workflow_type?: string;
  task_queue?: string;
  version?: string;
  description?: string;
}

export interface CompileResponse {
  success: boolean;
  workflow_id: string;
  dsl: Record<string, any>;
  file_path: string;
  content_hash: string;
  generated_at?: string;
}

export const compilerApi = {
  /**
   * Send the exported workflow JSON to the backend API for DSL compilation.
   */
  async compileWorkflow(payload: CompilePayload): Promise<CompileResponse> {
    const url = `${API_BASE_URL}/api/v1/workflows/compile`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        nodes: payload.nodes,
        edges: payload.edges,
        workflow_id: payload.workflow_id || 'workflow-design',
        workflow_type: payload.workflow_type ?? import.meta.env.VITE_WORKFLOW_TYPE ?? 'workflow-builder',
        task_queue: payload.task_queue ?? import.meta.env.VITE_TASK_QUEUE ?? 'workflow-builder',
        version: payload.version || '1.0.0',
        description: payload.description || '',
      }),
    });

    if (!response.ok) {
      let errorMessage = `HTTP error ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {
        // Fallback if parsing fails
      }
      throw new Error(errorMessage);
    }

    return response.json();
  },

  /**
   * Trigger a workflow execution on Temporal using a specific compiled content hash.
   */
  async executeWorkflow(workflowId: string, dslHash: string, input: Record<string, any> = {}): Promise<any> {
    const url = `${API_BASE_URL}/api/v1/executions/${workflowId}/execute`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        dsl_hash: dslHash,
        input: input
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to execute: ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Retrieve historical executions for a workflow ID from Temporal.
   */
  async getHistory(workflowId: string): Promise<any> {
    const url = `${API_BASE_URL}/api/v1/executions/${workflowId}/history`;
    const response = await fetch(url);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch history: ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Fetch trace history details (step-by-step statuses) for a given run ID and workflow ID.
   */
  async getTrace(workflowId: string, runId: string): Promise<any> {
    const url = `${API_BASE_URL}/api/v1/executions/${workflowId}/${runId}/trace`;
    const response = await fetch(url);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to fetch trace: ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Request cancellation of a running workflow execution.
   */
  async cancelWorkflow(workflowId: string, runId: string): Promise<any> {
    const url = `${API_BASE_URL}/api/v1/executions/${workflowId}/${runId}/cancel`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to cancel workflow: ${response.statusText}`);
    }
    return response.json();
  },

  /**
   * Forcefully terminate a running workflow execution.
   */
  async terminateWorkflow(workflowId: string, runId: string, reason = "Terminated by user"): Promise<any> {
    const url = `${API_BASE_URL}/api/v1/executions/${workflowId}/${runId}/terminate?reason=${encodeURIComponent(reason)}`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to terminate workflow: ${response.statusText}`);
    }
    return response.json();
  },
};
