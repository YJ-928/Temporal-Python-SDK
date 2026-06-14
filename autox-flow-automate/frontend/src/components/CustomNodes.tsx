import React from 'react';
import { Handle, Position } from 'reactflow';
import {
  Play,
  Square,
  Bot,
  GitFork,
  Zap,
  FileOutput,
  Database,
} from 'lucide-react';
import type { RFNodeData } from '../types';
import { getAgentById } from '../constants/agents';

interface NodeProps {
  data: RFNodeData;
  selected?: boolean;
}

// START node — filled green circle (spec: Filled circle · Green, 0 in · 1 out)
export const StartNode: React.FC<NodeProps> = ({ data, selected }) => (
  <div className={`start-node-circle${selected ? ' start-node-selected' : ''}`}>
    <div className="circle-node-icon">
      <Play size={28} fill="white" color="white" />
    </div>
    <span className="circle-node-label">{data.label || 'Start'}</span>
    <Handle type="source" position={Position.Bottom} id="source" />
  </div>
);

// END node — filled red circle (spec: Filled circle · Red, 1 in · 0 out)
export const EndNode: React.FC<NodeProps> = ({ data, selected }) => (
  <div className={`end-node-circle${selected ? ' end-node-selected' : ''}`}>
    <Handle type="target" position={Position.Top} id="target" />
    <div className="circle-node-icon">
      <Square size={22} fill="white" color="white" />
    </div>
    <span className="circle-node-label">{data.label || 'End'}</span>
  </div>
);

// INPUT node — rect + thick top bar · Gray (spec: Default inputs · Rect + thick top bar · Gray)
export const InputNode: React.FC<NodeProps> = ({ data, selected }) => {
  const fields = data.inputFields ?? [];
  return (
    <div className={`custom-node input-node${selected ? ' selected-node' : ''}`}>
      <div className="node-top-bar input-top-bar" />
      <Handle type="target" position={Position.Top} id="target" />
      <div className="custom-node-header">
        <Database size={18} />
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

// IF / CONDITIONAL node — diamond · Blue (spec: Diamond · Blue, 1 in · True + False out)
export const IfNode: React.FC<NodeProps> = ({ data, selected }) => {
  const cond = data.ifCondition;
  const expr = cond
    ? `${cond.left || '?'} ${cond.operator || '=='} ${cond.right || '?'}`
    : 'condition?';

  return (
    <div className={`if-node-wrapper${selected ? ' if-node-selected' : ''}`}>
      <Handle type="target" position={Position.Top} id="target" />

      <div className="if-diamond-shape">
        <div className="if-diamond-content">
          <GitFork size={12} color="rgba(255,255,255,0.7)" />
          <span className="if-type-label">IF</span>
          <span className="if-expr" title={expr}>{expr}</span>
        </div>
      </div>

      {/* True branch — left side */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="branch1"
        style={{ left: '28%', bottom: '-1px' }}
      />
      {/* False branch — right side */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="branch2"
        style={{ left: '72%', bottom: '-1px' }}
      />

      <div className="if-branch-labels">
        <span className="if-label-true">true</span>
        <span className="if-label-false">false</span>
      </div>
    </div>
  );
};

// ACTION node — rect + thick left bar · Teal (spec: Connector/API call · Rect + thick left bar · Teal)
export const ActionNode: React.FC<NodeProps> = ({ data, selected }) => (
  <div className={`custom-node action-node${selected ? ' selected-node' : ''}`}>
    <div className="node-left-bar action-left-bar" />
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

// OUTPUT node — rect · Pink (no exact doc match — kept as result emitter)
export const OutputNode: React.FC<NodeProps> = ({ data, selected }) => {
  const fields = data.outputFields ?? [];
  return (
    <div className={`custom-node output-node${selected ? ' selected-node' : ''}`}>
      <Handle type="target" position={Position.Top} id="target" />
      <div className="custom-node-header">
        <FileOutput size={18} />
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

// AGENT node — dashed rounded rect · Purple (spec: Agent block · Dashed rounded rect · Purple)
export const AgentNode: React.FC<NodeProps> = ({ data, selected }) => {
  const agent = getAgentById(data.selectedAgentId);
  return (
    <div className={`custom-node agent-node${selected ? ' selected-node' : ''}`}>
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
        {data.agentOutput && (
          <div className="custom-node-field">
            <span className="custom-node-field-label">Output key</span>
            <span className="custom-node-field-value">{data.agentOutput}</span>
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} id="source" />
    </div>
  );
};
