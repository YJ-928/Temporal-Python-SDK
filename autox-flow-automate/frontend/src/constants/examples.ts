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

// Layout constants — based on actual rendered node heights post v4 redesign
//   Circle nodes (START/END): 96×96px
//   IF wrapper: 180×110px
//   Rect nodes (INPUT/ACTION/AGENT/OUTPUT): width ~240px, heights vary by content:
//     1 field  ≈ 100px  |  2 fields ≈ 130px  |  3 fields ≈ 155px  |  4+ fields ≈ 175px
//
// Column centers: CX=420 (main), CX-260=160 (left branch), CX+260=680 (right branch)
//   circle x = CX - 48   = 372
//   rect   x = CX - 120  = 300
//   if     x = CX - 90   = 330
//   left branch rect  x  =  40  (center 160)
//   right branch rect x  = 560  (center 680)
//
// Vertical rule: each node starts 60px below the bottom of the previous node.

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
      // START circle (96px tall) — y:40, bottom:136
      { id: 'N1', type: 'start', position: { x: 372, y: 40 }, data: { label: 'START' } },
      // INPUT 1 field (~100px tall) — y:196, bottom:296
      {
        id: 'N2', type: 'input', position: { x: 300, y: 196 },
        data: {
          label: 'Location Input',
          inputFields: [{ id: 'f1', field: 'city', store_as: 'city', type: 'string' }],
        },
      },
      // AGENT (~130px tall) — y:356, bottom:486
      {
        id: 'N3', type: 'agent', position: { x: 300, y: 356 },
        data: {
          label: 'Weather Agent',
          selectedAgentId: 'weather-agent',
          agentInputs: '{\n  "city": "city"\n}',
          agentOutput: 'weather',
          agentOutputPath: 'condition',
        },
      },
      // IF wrapper (110px tall) — y:546, bottom:656
      {
        id: 'N4', type: 'if', position: { x: 330, y: 546 },
        data: {
          label: 'Is Rainy?',
          ifCondition: { left: 'weather', operator: '==', right: 'Rainy' },
        },
      },
      // True branch ACTION (~130px tall) — y:716
      {
        id: 'N5', type: 'action', position: { x: 40, y: 716 },
        data: {
          label: 'Send Rain Alert',
          actionOperation: 'send_rain_alert',
          actionInputs: '{\n  "city": "city"\n}',
          actionOutput: 'alert_status',
        },
      },
      // False branch ACTION (~130px tall) — y:716
      {
        id: 'N6', type: 'action', position: { x: 560, y: 716 },
        data: {
          label: 'Send Summary',
          actionOperation: 'send_weather_summary',
          actionInputs: '{\n  "city": "city"\n}',
          actionOutput: 'summary_status',
        },
      },
      // OUTPUT 2 fields (~130px tall) — y:906, bottom:1036
      {
        id: 'N7', type: 'output', position: { x: 300, y: 906 },
        data: {
          label: 'Output Results',
          outputFields: [
            { id: 'o1', field: 'alert_status', type: 'string' },
            { id: 'o2', field: 'summary_status', type: 'string' },
          ],
        },
      },
      // END circle (96px tall) — y:1096
      { id: 'N8', type: 'end', position: { x: 372, y: 1096 }, data: { label: 'END' } },
    ],
    edges: [
      { id: 'E1', source: 'N1', target: 'N2', animated: true },
      { id: 'E2', source: 'N2', target: 'N3', animated: true },
      { id: 'E3', source: 'N3', target: 'N4', animated: true },
      { id: 'E4', source: 'N4', target: 'N5', sourceHandle: 'branch1', label: 'true',  data: { branch: 'branch1', label: 'true'  }, animated: true },
      { id: 'E5', source: 'N4', target: 'N6', sourceHandle: 'branch2', label: 'false', data: { branch: 'branch2', label: 'false' }, animated: true },
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
      // START circle — y:40, bottom:136
      { id: 'N1', type: 'start', position: { x: 372, y: 40 }, data: { label: 'START' } },
      // INPUT 3 fields (~155px tall) — y:196, bottom:351
      {
        id: 'N2', type: 'input', position: { x: 300, y: 196 },
        data: {
          label: 'Email Input',
          inputFields: [
            { id: 'f1', field: 'email',   store_as: 'email',   type: 'string' },
            { id: 'f2', field: 'subject', store_as: 'subject', type: 'string' },
            { id: 'f3', field: 'message', store_as: 'message', type: 'string' },
          ],
        },
      },
      // AGENT (~130px tall) — y:411, bottom:541
      {
        id: 'N3', type: 'agent', position: { x: 300, y: 411 },
        data: {
          label: 'Email Validator',
          selectedAgentId: 'email-validator-agent',
          agentInputs: '{\n  "email": "email"\n}',
          agentOutput: 'email_validation',
        },
      },
      // IF wrapper (110px tall) — y:601, bottom:711
      {
        id: 'N4', type: 'if', position: { x: 330, y: 601 },
        data: {
          label: 'Valid?',
          ifCondition: { left: 'email_validation.is_valid', operator: '==', right: 'true' },
        },
      },
      // True branch ACTION (~130px) — y:771
      {
        id: 'N5', type: 'action', position: { x: 40, y: 771 },
        data: {
          label: 'Send Email',
          actionOperation: 'send_email',
          actionInputs: '{\n  "email": "email",\n  "subject": "subject",\n  "message": "message"\n}',
          actionOutput: 'email_result',
        },
      },
      // False branch ACTION (~130px) — y:771
      {
        id: 'N9', type: 'action', position: { x: 560, y: 771 },
        data: {
          label: 'No-op Branch',
          actionOperation: 'noop',
          actionInputs: '{}',
          actionOutput: 'noop_res',
        },
      },
      // True branch OUTPUT 3 fields (~155px) — y:961
      {
        id: 'N6', type: 'output', position: { x: 40, y: 961 },
        data: {
          label: 'Success Output',
          outputFields: [
            { id: 'o1', field: 'email',            type: 'string' },
            { id: 'o2', field: 'email_validation', type: 'object' },
            { id: 'o3', field: 'email_result',     type: 'object' },
          ],
        },
      },
      // False branch OUTPUT 2 fields (~130px) — y:961
      {
        id: 'N7', type: 'output', position: { x: 560, y: 961 },
        data: {
          label: 'Failure Output',
          outputFields: [
            { id: 'o4', field: 'email',            type: 'string' },
            { id: 'o5', field: 'email_validation', type: 'object' },
          ],
        },
      },
      // END — y:961+155+60=1176
      { id: 'N8', type: 'end', position: { x: 372, y: 1176 }, data: { label: 'END' } },
    ],
    edges: [
      { id: 'E1', source: 'N1', target: 'N2', animated: true },
      { id: 'E2', source: 'N2', target: 'N3', animated: true },
      { id: 'E3', source: 'N3', target: 'N4', animated: true },
      { id: 'E4', source: 'N4', target: 'N5', sourceHandle: 'branch1', label: 'true',  data: { branch: 'branch1', label: 'true'  }, animated: true },
      { id: 'E5', source: 'N4', target: 'N9', sourceHandle: 'branch2', label: 'false', data: { branch: 'branch2', label: 'false' }, animated: true },
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
      // START circle — y:40, bottom:136
      { id: 'N1', type: 'start', position: { x: 372, y: 40 }, data: { label: 'START' } },
      // INPUT 1 field (~100px) — y:196, bottom:296
      {
        id: 'N2', type: 'input', position: { x: 300, y: 196 },
        data: {
          label: 'Account ID Input',
          inputFields: [{ id: 'f1', field: 'account_id', store_as: 'account_id', type: 'string' }],
        },
      },
      // ACTION (~130px) — y:356, bottom:486
      {
        id: 'N3', type: 'action', position: { x: 300, y: 356 },
        data: {
          label: 'Lookup Account',
          actionOperation: 'account_lookup',
          actionInputs: '{\n  "account_id": "account_id"\n}',
          actionOutput: 'account',
        },
      },
      // IF wrapper (110px) — y:546, bottom:656
      {
        id: 'N4', type: 'if', position: { x: 330, y: 546 },
        data: {
          label: 'Is Active?',
          ifCondition: { left: 'account.active', operator: '==', right: 'true' },
        },
      },
      // True branch ACTION (~130px) — y:716
      {
        id: 'N5', type: 'action', position: { x: 40, y: 716 },
        data: {
          label: 'Support Case',
          actionOperation: 'assign_support_case',
          actionInputs: '{\n  "account_id": "account_id"\n}',
          actionOutput: 'support_case',
        },
      },
      // False branch ACTION (~130px) — y:716
      {
        id: 'N6', type: 'action', position: { x: 560, y: 716 },
        data: {
          label: 'Billing Case',
          actionOperation: 'assign_billing_case',
          actionInputs: '{\n  "account_id": "account_id"\n}',
          actionOutput: 'billing_case',
        },
      },
      // OUTPUT 4 fields (~175px) — y:906, bottom:1081
      {
        id: 'N7', type: 'output', position: { x: 300, y: 906 },
        data: {
          label: 'Output Case Details',
          outputFields: [
            { id: 'o1', field: 'account_id',   type: 'string' },
            { id: 'o2', field: 'account',       type: 'object' },
            { id: 'o3', field: 'support_case',  type: 'object' },
            { id: 'o4', field: 'billing_case',  type: 'object' },
          ],
        },
      },
      // END — y:906+175+60=1141
      { id: 'N8', type: 'end', position: { x: 372, y: 1141 }, data: { label: 'END' } },
    ],
    edges: [
      { id: 'E1', source: 'N1', target: 'N2', animated: true },
      { id: 'E2', source: 'N2', target: 'N3', animated: true },
      { id: 'E3', source: 'N3', target: 'N4', animated: true },
      { id: 'E4', source: 'N4', target: 'N5', sourceHandle: 'branch1', label: 'true',  data: { branch: 'branch1', label: 'true'  }, animated: true },
      { id: 'E5', source: 'N4', target: 'N6', sourceHandle: 'branch2', label: 'false', data: { branch: 'branch2', label: 'false' }, animated: true },
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
      description: 'Validates an email address using the Email Validator Agent, then branches: valid emails produce a success output, invalid emails produce a rejection output.',
    },
    nodes: [
      // START circle — y:40, bottom:136
      { id: 'N1', type: 'start', position: { x: 372, y: 40 }, data: { label: 'START' } },
      // INPUT 1 field (~100px) — y:196, bottom:296
      {
        id: 'N2', type: 'input', position: { x: 300, y: 196 },
        data: {
          label: 'Email Input',
          inputFields: [{ id: 'f1', field: 'email', store_as: 'email', type: 'string' }],
        },
      },
      // AGENT (~130px) — y:356, bottom:486
      {
        id: 'N3', type: 'agent', position: { x: 300, y: 356 },
        data: {
          label: 'Email Validator',
          selectedAgentId: 'email-validator-agent',
          agentInputs: '{\n  "email": "email"\n}',
          agentOutput: 'email_validation',
        },
      },
      // IF wrapper (110px) — y:546, bottom:656
      {
        id: 'N4', type: 'if', position: { x: 330, y: 546 },
        data: {
          label: 'Valid?',
          ifCondition: { left: 'email_validation.is_valid', operator: '==', right: 'true' },
        },
      },
      // True branch OUTPUT 2 fields (~130px) — y:716
      {
        id: 'N5', type: 'output', position: { x: 40, y: 716 },
        data: {
          label: 'Valid Email Output',
          outputFields: [
            { id: 'o1', field: 'email',            type: 'string' },
            { id: 'o2', field: 'email_validation', type: 'object' },
          ],
        },
      },
      // False branch OUTPUT 2 fields (~130px) — y:716
      {
        id: 'N6', type: 'output', position: { x: 560, y: 716 },
        data: {
          label: 'Invalid Email Output',
          outputFields: [
            { id: 'o3', field: 'email',            type: 'string' },
            { id: 'o4', field: 'email_validation', type: 'object' },
          ],
        },
      },
      // END — y:716+130+60=906
      { id: 'N7', type: 'end', position: { x: 372, y: 906 }, data: { label: 'END' } },
    ],
    edges: [
      { id: 'E1', source: 'N1', target: 'N2', animated: true },
      { id: 'E2', source: 'N2', target: 'N3', animated: true },
      { id: 'E3', source: 'N3', target: 'N4', animated: true },
      { id: 'E4', source: 'N4', target: 'N5', sourceHandle: 'branch1', label: 'true',  data: { branch: 'branch1', label: 'true'  }, animated: true },
      { id: 'E5', source: 'N4', target: 'N6', sourceHandle: 'branch2', label: 'false', data: { branch: 'branch2', label: 'false' }, animated: true },
      { id: 'E6', source: 'N5', target: 'N7', animated: true },
      { id: 'E7', source: 'N6', target: 'N7', animated: true },
    ],
  },
};
