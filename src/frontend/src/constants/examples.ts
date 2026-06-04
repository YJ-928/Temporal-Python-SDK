import type { Node, Edge } from 'reactflow';
import type { RFNodeData, RFEdgeData } from '../types';

export interface ExampleWorkflow {
  name: string;
  metadata: {
    workflow_id: string;
    workflow_type: string;
    task_queue: string;
    version: string;
    description: string;
  };
  nodes: Node<RFNodeData>[];
  edges: Edge<RFEdgeData>[];
}

export const EXAMPLES: Record<string, ExampleWorkflow> = {
  weather_assistant: {
    name: 'Weather Assistant',
    metadata: {
      workflow_id: 'weather-assistant',
      workflow_type: 'weather-assistant-type',
      task_queue: 'default',
      version: '1.0.0',
      description: 'Checks the weather using a Weather Agent, routes based on rain condition, and sends alerts or summary reports.',
    },
    nodes: [
      {
        id: 'N1',
        type: 'start',
        position: { x: 250, y: 0 },
        data: { label: 'START' },
      },
      {
        id: 'N2',
        type: 'input',
        position: { x: 250, y: 100 },
        data: {
          label: 'Location Input',
          inputFields: [
            { id: 'f1', field: 'city', store_as: 'city', type: 'string' },
          ],
        },
      },
      {
        id: 'N3',
        type: 'agent',
        position: { x: 250, y: 220 },
        data: {
          label: 'Weather Agent',
          selectedAgentId: 'weather-agent',
          agentInputs: '{\n  "city": "city"\n}',
          agentOutput: 'weather',
          agentOutputPath: 'condition',
        },
      },
      {
        id: 'N4',
        type: 'if',
        position: { x: 250, y: 340 },
        data: {
          label: 'Is Rainy?',
          ifCondition: { left: 'weather', operator: '==', right: 'Rainy' },
        },
      },
      {
        id: 'N5',
        type: 'action',
        position: { x: 80, y: 480 },
        data: {
          label: 'Send Rain Alert',
          actionOperation: 'send_rain_alert',
          actionInputs: '{\n  "city": "city"\n}',
          actionOutput: 'alert_status',
        },
      },
      {
        id: 'N6',
        type: 'action',
        position: { x: 420, y: 480 },
        data: {
          label: 'Send Summary',
          actionOperation: 'send_weather_summary',
          actionInputs: '{\n  "city": "city"\n}',
          actionOutput: 'summary_status',
        },
      },
      {
        id: 'N7',
        type: 'output',
        position: { x: 250, y: 620 },
        data: {
          label: 'Output Results',
          outputFields: [
            { id: 'o1', field: 'alert_status', type: 'string' },
            { id: 'o2', field: 'summary_status', type: 'string' },
          ],
        },
      },
      {
        id: 'N8',
        type: 'end',
        position: { x: 250, y: 740 },
        data: { label: 'END' },
      },
    ],
    edges: [
      { id: 'E1', source: 'N1', target: 'N2', animated: true },
      { id: 'E2', source: 'N2', target: 'N3', animated: true },
      { id: 'E3', source: 'N3', target: 'N4', animated: true },
      {
        id: 'E4',
        source: 'N4',
        target: 'N5',
        sourceHandle: 'branch1',
        label: 'true',
        data: { branch: 'branch1', label: 'true' },
        animated: true,
      },
      {
        id: 'E5',
        source: 'N4',
        target: 'N6',
        sourceHandle: 'branch2',
        label: 'false',
        data: { branch: 'branch2', label: 'false' },
        animated: true,
      },
      { id: 'E6', source: 'N5', target: 'N7', animated: true },
      { id: 'E7', source: 'N6', target: 'N7', animated: true },
      { id: 'E8', source: 'N7', target: 'N8', animated: true },
    ],
  },
  email_validation_sender: {
    name: 'Email Validation Sender',
    metadata: {
      workflow_id: 'email-validation-sender',
      workflow_type: 'email-validation-sender-type',
      task_queue: 'default',
      version: '1.0.0',
      description: 'Checks validity of email addresses using Email Validator Agent, then routes valid emails to the sender service or triggers a noop branch.',
    },
    nodes: [
      {
        id: 'N1',
        type: 'start',
        position: { x: 250, y: 0 },
        data: { label: 'START' },
      },
      {
        id: 'N2',
        type: 'input',
        position: { x: 250, y: 100 },
        data: {
          label: 'Email Input',
          inputFields: [
            { id: 'f1', field: 'email', store_as: 'email', type: 'string' },
            { id: 'f2', field: 'subject', store_as: 'subject', type: 'string' },
            { id: 'f3', field: 'message', store_as: 'message', type: 'string' },
          ],
        },
      },
      {
        id: 'N3',
        type: 'agent',
        position: { x: 250, y: 220 },
        data: {
          label: 'Email Validator',
          selectedAgentId: 'email-validator-agent',
          agentInputs: '{\n  "email": "email"\n}',
          agentOutput: 'email_validation',
        },
      },
      {
        id: 'N4',
        type: 'if',
        position: { x: 250, y: 340 },
        data: {
          label: 'Valid?',
          ifCondition: { left: 'email_validation.is_valid', operator: '==', right: 'true' },
        },
      },
      {
        id: 'N5',
        type: 'action',
        position: { x: 80, y: 480 },
        data: {
          label: 'Send Email',
          actionOperation: 'send_email',
          actionInputs: '{\n  "email": "email",\n  "subject": "subject",\n  "message": "message"\n}',
          actionOutput: 'email_result',
        },
      },
      {
        id: 'N9',
        type: 'action',
        position: { x: 420, y: 480 },
        data: {
          label: 'No-op Branch',
          actionOperation: 'noop',
          actionInputs: '{}',
          actionOutput: 'noop_res',
        },
      },
      {
        id: 'N6',
        type: 'output',
        position: { x: 80, y: 620 },
        data: {
          label: 'Success Output',
          outputFields: [
            { id: 'o1', field: 'email', type: 'string' },
            { id: 'o2', field: 'email_validation', type: 'object' },
            { id: 'o3', field: 'email_result', type: 'object' },
          ],
        },
      },
      {
        id: 'N7',
        type: 'output',
        position: { x: 420, y: 620 },
        data: {
          label: 'Failure Output',
          outputFields: [
            { id: 'o4', field: 'email', type: 'string' },
            { id: 'o5', field: 'email_validation', type: 'object' },
          ],
        },
      },
      {
        id: 'N8',
        type: 'end',
        position: { x: 250, y: 760 },
        data: { label: 'END' },
      },
    ],
    edges: [
      { id: 'E1', source: 'N1', target: 'N2', animated: true },
      { id: 'E2', source: 'N2', target: 'N3', animated: true },
      { id: 'E3', source: 'N3', target: 'N4', animated: true },
      {
        id: 'E4',
        source: 'N4',
        target: 'N5',
        sourceHandle: 'branch1',
        label: 'true',
        data: { branch: 'branch1', label: 'true' },
        animated: true,
      },
      {
        id: 'E5',
        source: 'N4',
        target: 'N9',
        sourceHandle: 'branch2',
        label: 'false',
        data: { branch: 'branch2', label: 'false' },
        animated: true,
      },
      { id: 'E6', source: 'N5', target: 'N6', animated: true },
      { id: 'E7', source: 'N9', target: 'N7', animated: true },
      { id: 'E8', source: 'N6', target: 'N8', animated: true },
      { id: 'E9', source: 'N7', target: 'N8', animated: true },
    ],
  },
  account_routing: {
    name: 'Account Routing',
    metadata: {
      workflow_id: 'account-routing',
      workflow_type: 'account-routing-type',
      task_queue: 'default',
      version: '1.0.0',
      description: 'Resolves account details via a database lookup, then splits execution depending on account type parameters.',
    },
    nodes: [
      {
        id: 'N1',
        type: 'start',
        position: { x: 250, y: 0 },
        data: { label: 'START' },
      },
      {
        id: 'N2',
        type: 'input',
        position: { x: 250, y: 100 },
        data: {
          label: 'Account ID Input',
          inputFields: [
            { id: 'f1', field: 'account_id', store_as: 'account_id', type: 'string' },
          ],
        },
      },
      {
        id: 'N3',
        type: 'action',
        position: { x: 250, y: 220 },
        data: {
          label: 'Lookup Account',
          actionOperation: 'account_lookup',
          actionInputs: '{\n  "account_id": "account_id"\n}',
          actionOutput: 'account',
        },
      },
      {
        id: 'N4',
        type: 'if',
        position: { x: 250, y: 340 },
        data: {
          label: 'Is Active?',
          ifCondition: { left: 'account.active', operator: '==', right: 'true' },
        },
      },
      {
        id: 'N5',
        type: 'action',
        position: { x: 80, y: 480 },
        data: {
          label: 'Support Case',
          actionOperation: 'assign_support_case',
          actionInputs: '{\n  "account_id": "account_id"\n}',
          actionOutput: 'support_case',
        },
      },
      {
        id: 'N6',
        type: 'action',
        position: { x: 420, y: 480 },
        data: {
          label: 'Billing Case',
          actionOperation: 'assign_billing_case',
          actionInputs: '{\n  "account_id": "account_id"\n}',
          actionOutput: 'billing_case',
        },
      },
      {
        id: 'N7',
        type: 'output',
        position: { x: 250, y: 620 },
        data: {
          label: 'Output Case Details',
          outputFields: [
            { id: 'o1', field: 'account_id', type: 'string' },
            { id: 'o2', field: 'account', type: 'object' },
            { id: 'o3', field: 'support_case', type: 'object' },
            { id: 'o4', field: 'billing_case', type: 'object' },
          ],
        },
      },
      {
        id: 'N8',
        type: 'end',
        position: { x: 250, y: 740 },
        data: { label: 'END' },
      },
    ],
    edges: [
      { id: 'E1', source: 'N1', target: 'N2', animated: true },
      { id: 'E2', source: 'N2', target: 'N3', animated: true },
      { id: 'E3', source: 'N3', target: 'N4', animated: true },
      {
        id: 'E4',
        source: 'N4',
        target: 'N5',
        sourceHandle: 'branch1',
        label: 'true',
        data: { branch: 'branch1', label: 'true' },
        animated: true,
      },
      {
        id: 'E5',
        source: 'N4',
        target: 'N6',
        sourceHandle: 'branch2',
        label: 'false',
        data: { branch: 'branch2', label: 'false' },
        animated: true,
      },
      { id: 'E6', source: 'N5', target: 'N7', animated: true },
      { id: 'E7', source: 'N6', target: 'N7', animated: true },
      { id: 'E8', source: 'N7', target: 'N8', animated: true },
    ],
  },
  single_email_validator: {
    name: 'Single Email Validator',
    metadata: {
      workflow_id: 'single-email-validator',
      workflow_type: 'single-email-validator-type',
      task_queue: 'default',
      version: '1.0.0',
      description: 'A simple linear validation pipe that accepts an email address and evaluates it via validation agent model rules.',
    },
    nodes: [
      {
        id: 'N1',
        type: 'start',
        position: { x: 250, y: 0 },
        data: { label: 'START' },
      },
      {
        id: 'N2',
        type: 'input',
        position: { x: 250, y: 100 },
        data: {
          label: 'Email Input',
          inputFields: [
            { id: 'f1', field: 'email', store_as: 'email', type: 'string' },
          ],
        },
      },
      {
        id: 'N3',
        type: 'agent',
        position: { x: 250, y: 220 },
        data: {
          label: 'Email Validator',
          selectedAgentId: 'email-validator-agent',
          agentInputs: '{\n  "email": "email"\n}',
          agentOutput: 'email_validation',
        },
      },
      {
        id: 'N4',
        type: 'output',
        position: { x: 250, y: 340 },
        data: {
          label: 'Email Verification Output',
          outputFields: [
            { id: 'o1', field: 'email_validation', type: 'object' },
          ],
        },
      },
      {
        id: 'N5',
        type: 'end',
        position: { x: 250, y: 460 },
        data: { label: 'END' },
      },
    ],
    edges: [
      { id: 'E1', source: 'N1', target: 'N2', animated: true },
      { id: 'E2', source: 'N2', target: 'N3', animated: true },
      { id: 'E3', source: 'N3', target: 'N4', animated: true },
      { id: 'E4', source: 'N4', target: 'N5', animated: true },
    ],
  },
  workflow_builder_demo: {
    name: 'Workflow Builder Demo',
    metadata: {
      workflow_id: 'mixed-pipeline',
      workflow_type: 'mixed',
      task_queue: 'default',
      version: '1.0.0',
      description: 'A rich demonstrative workflow showcasing various actions, inputs, data mappings, agent calls, outputs, and terminals.',
    },
    nodes: [
      {
        id: 'N1',
        type: 'start',
        position: { x: 250, y: 0 },
        data: { label: 'START' },
      },
      {
        id: 'N2',
        type: 'input',
        position: { x: 250, y: 100 },
        data: {
          label: 'Topic Input',
          inputFields: [
            { id: 'f1', field: 'city', store_as: 'city', type: 'string' },
          ],
        },
      },
      {
        id: 'N3',
        type: 'action',
        position: { x: 250, y: 220 },
        data: {
          label: 'Fetch Info',
          actionOperation: 'fetch_info',
          actionInputs: '{\n  "city": "city"\n}',
          actionOutput: 'info',
        },
      },
      {
        id: 'N4',
        type: 'agent',
        position: { x: 250, y: 340 },
        data: {
          label: 'Summarizer Agent',
          selectedAgentId: 'summarizer-agent',
          agentInputs: '{\n  "text": "info"\n}',
          agentOutput: 'summary',
        },
      },
      {
        id: 'N5',
        type: 'output',
        position: { x: 250, y: 460 },
        data: {
          label: 'Summary Output',
          outputFields: [
            { id: 'o1', field: 'summary', type: 'string' },
          ],
        },
      },
      {
        id: 'N6',
        type: 'end',
        position: { x: 250, y: 580 },
        data: { label: 'END' },
      },
    ],
    edges: [
      { id: 'E1', source: 'N1', target: 'N2', animated: true },
      { id: 'E2', source: 'N2', target: 'N3', animated: true },
      { id: 'E3', source: 'N3', target: 'N4', animated: true },
      { id: 'E4', source: 'N4', target: 'N5', animated: true },
      { id: 'E5', source: 'N5', target: 'N6', animated: true },
    ],
  },
};
