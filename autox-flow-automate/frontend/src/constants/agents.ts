export interface AgentOption {
  id: string;
  name: string;
  description?: string;
}

/** Agents available in the AGENT node dropdown */
export const AVAILABLE_AGENTS: AgentOption[] = [
  { id: 'agent-001', name: 'Triage Agent', description: 'Routes and classifies incoming requests' },
  { id: 'agent-002', name: 'Billing Agent', description: 'Handles billing and account questions' },
  { id: 'agent-003', name: 'Support Agent', description: 'General customer support' },
  { id: 'agent-004', name: 'Researcher Agent', description: 'Gathers context and facts' },
  { id: 'agent-005', name: 'Writer Agent', description: 'Generates long-form content' },
  { id: 'agent-006', name: 'Summarizer Agent', description: 'Condenses documents and logs' },
];

export function getAgentById(id: string | undefined): AgentOption | undefined {
  if (!id) return undefined;
  return AVAILABLE_AGENTS.find((a) => a.id === id);
}
