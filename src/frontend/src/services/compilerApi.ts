import type { ExportedWorkflowNode } from '../utils/exportWorkflow';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export interface CompilePayload {
  nodes: ExportedWorkflowNode[];
  edges: any[];
  workflow_id?: string;
  workflow_type?: string;
  task_queue?: string;
}

export interface CompileResponse {
  success: boolean;
  workflow_id: string;
  dsl: Record<string, any>;
  file_path: string;
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
};
