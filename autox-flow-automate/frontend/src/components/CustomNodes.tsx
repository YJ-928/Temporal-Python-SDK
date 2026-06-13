import React from 'react';
import { Handle, Position } from 'reactflow';
import {
  Play,
  Bot,
  GitFork,
  Zap,
  LogOut,
  CirclePlay,
  CircleStop,
} from 'lucide-react';
import type { RFNodeData } from '../types';
import { getAgentById } from '../constants/agents';

interface NodeProps {
  id: string;
  data: RFNodeData;
  selected?: boolean;
}

const nodeClass = (base: string, selected?: boolean) =>
  `custom-node ${base} ${selected ? 'selected-node' : ''}`;

export const StartNode: React.FC<NodeProps> = ({ data, selected }) => (
  <div className={nodeClass('start-node', selected)}>
    <div className="custom-node-header">
      <CirclePlay size={18} />
      <div className="custom-node-header-info">
        <span className="custom-node-type">START</span>
        <span className="custom-node-title">{data.label || 'Start'}</span>
      </div>
    </div>
    <div className="custom-node-body">
      <span className="custom-node-muted">Workflow entry — no configuration</span>
    </div>
    <Handle type="source" position={Position.Bottom} id="source" />
  </div>
);

export const EndNode: React.FC<NodeProps> = ({ data, selected }) => (
  <div className={nodeClass('end-node', selected)}>
    <Handle type="target" position={Position.Top} id="target" />
    <div className="custom-node-header">
      <CircleStop size={18} />
      <div className="custom-node-header-info">
        <span className="custom-node-type">END</span>
        <span className="custom-node-title">{data.label || 'End'}</span>
      </div>
    </div>
    <div className="custom-node-body">
      <span className="custom-node-muted">Workflow exit — no configuration</span>
    </div>
  </div>
);

export const InputNode: React.FC<NodeProps> = ({ data, selected }) => {
  const fields = data.inputFields ?? [];
  return (
    <div className={nodeClass('input-node', selected)}>
      <Handle type="target" position={Position.Top} id="target" />
      <div className="custom-node-header">
        <Play size={18} />
        <div className="custom-node-header-info">
          <span className="custom-node-type">INPUT</span>
          <span className="custom-node-title">{data.label || 'Input'}</span>
        </div>
      </div>
      <div className="custom-node-body">
        {fields.length === 0 ? (
          <span className="custom-node-muted">No input fields configured</span>
        ) : (
          fields.slice(0, 3).map((row) => (
            <div key={row.id} className="custom-node-field">
              <span className="custom-node-field-label">{row.field || '—'}</span>
              <span className="custom-node-field-value">
                → {row.store_as || '—'} ({row.type})
              </span>
            </div>
          ))
        )}
        {fields.length > 3 && (
          <span className="custom-node-muted">+{fields.length - 3} more…</span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} id="source" />
    </div>
  );
};

export const IfNode: React.FC<NodeProps> = ({ data, selected }) => {
  const cond = data.ifCondition;
  const expr = cond
    ? `${cond.left || '?'} ${cond.operator || '=='} ${cond.right || '?'}`
    : 'Not configured';

  return (
    <div className={nodeClass('if-node', selected)}>
      <Handle type="target" position={Position.Top} id="target" />
      <div className="custom-node-header">
        <GitFork size={18} />
        <div className="custom-node-header-info">
          <span className="custom-node-type">IF</span>
          <span className="custom-node-title">{data.label || 'If'}</span>
        </div>
      </div>
      <div className="custom-node-body">
        <div className="custom-node-field">
          <span className="custom-node-field-label">Condition</span>
          <span className="custom-node-field-value" title={expr}>
            {expr}
          </span>
        </div>
      </div>
      <div className="if-node-branches">
        <div className="if-branch">
          <Handle type="source" position={Position.Bottom} id="branch1" style={{ left: '25%' }} />
          <span className="handle-label">true</span>
        </div>
        <div className="if-branch">
          <Handle type="source" position={Position.Bottom} id="branch2" style={{ left: '75%' }} />
          <span className="handle-label">false</span>
        </div>
      </div>
    </div>
  );
};

export const ActionNode: React.FC<NodeProps> = ({ data, selected }) => (
  <div className={nodeClass('action-node', selected)}>
    <Handle type="target" position={Position.Top} id="target" />
    <div className="custom-node-header">
      <Zap size={18} />
      <div className="custom-node-header-info">
        <span className="custom-node-type">ACTION</span>
        <span className="custom-node-title">{data.label || 'Action'}</span>
      </div>
    </div>
    <div className="custom-node-body">
      <div className="custom-node-field">
        <span className="custom-node-field-label">Operation</span>
        <span className="custom-node-field-value">{data.actionOperation || '—'}</span>
      </div>
      <div className="custom-node-field">
        <span className="custom-node-field-label">Output</span>
        <span className="custom-node-field-value">{data.actionOutput || '—'}</span>
      </div>
    </div>
    <Handle type="source" position={Position.Bottom} id="source" />
  </div>
);

export const OutputNode: React.FC<NodeProps> = ({ data, selected }) => {
  const fields = data.outputFields ?? [];
  return (
    <div className={nodeClass('output-node', selected)}>
      <Handle type="target" position={Position.Top} id="target" />
      <div className="custom-node-header">
        <LogOut size={18} />
        <div className="custom-node-header-info">
          <span className="custom-node-type">OUTPUT</span>
          <span className="custom-node-title">{data.label || 'Output'}</span>
        </div>
      </div>
      <div className="custom-node-body">
        {fields.length === 0 ? (
          <span className="custom-node-muted">No output fields configured</span>
        ) : (
          fields.slice(0, 3).map((row) => (
            <div key={row.id} className="custom-node-field">
              <span className="custom-node-field-label">{row.field || '—'}</span>
              <span className="custom-node-field-value">{row.type}</span>
            </div>
          ))
        )}
        {fields.length > 3 && (
          <span className="custom-node-muted">+{fields.length - 3} more…</span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} id="source" />
    </div>
  );
};

export const AgentNode: React.FC<NodeProps> = ({ data, selected }) => {
  const agent = getAgentById(data.selectedAgentId);
  return (
    <div className={nodeClass('agent-node', selected)}>
      <Handle type="target" position={Position.Top} id="target" />
      <div className="custom-node-header">
        <Bot size={18} />
        <div className="custom-node-header-info">
          <span className="custom-node-type">AGENT</span>
          <span className="custom-node-title">{agent?.name || data.label || 'Agent'}</span>
        </div>
      </div>
      <div className="custom-node-body">
        <div className="custom-node-field">
          <span className="custom-node-field-label">Agent</span>
          <span className="custom-node-field-value">
            {agent ? agent.id : 'Not selected'}
          </span>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} id="source" />
    </div>
  );
};

