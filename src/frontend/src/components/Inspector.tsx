import React from 'react';
import type { Node, Edge } from 'reactflow';
import { MousePointerClick, Settings, Plus, Trash2 } from 'lucide-react';
import type {
  RFNodeData,
  RFEdgeData,
  InputFieldRow,
  OutputFieldRow,
  FieldDataType,
  IfCondition,
} from '../types';
import { FIELD_TYPE_OPTIONS, IF_OPERATOR_OPTIONS } from '../types';
import { AVAILABLE_AGENTS } from '../constants/agents';

interface InspectorProps {
  selectedNode: Node<RFNodeData> | null;
  selectedEdge: Edge<RFEdgeData> | null;
  onUpdateNode: (nodeId: string, updatedData: Partial<RFNodeData>) => void;
  onUpdateEdge: (edgeId: string, updatedData: Partial<RFEdgeData>) => void;
  nodeTraceStates?: Record<string, { status: string; input?: any; output?: any; error?: string }>;
}

const newRowId = () => `row-${Math.random().toString(36).slice(2, 9)}`;

export const Inspector: React.FC<InspectorProps> = ({
  selectedNode,
  selectedEdge,
  onUpdateNode,
  onUpdateEdge,
  nodeTraceStates = {},
}) => {
  if (selectedNode) {
    const { id, type, data } = selectedNode;

    const patch = (updated: Partial<RFNodeData>) => onUpdateNode(id, updated);

    const handleLabelChange = (value: string) => patch({ label: value });
    
    // Check if there is trace state for this node
    const trace = nodeTraceStates[id];

    return (
      <aside className="inspector">
        <div className="inspector-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings size={18} style={{ color: 'var(--accent)' }} />
            <h3 className="inspector-title">Node Inspector</h3>
          </div>
          <span className="inspector-subtitle">
            {String(type).toUpperCase()} · {id}
          </span>
        </div>

        <div className="inspector-form">
          {trace && (
            <div style={{
              background: 'rgba(30, 41, 59, 0.7)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '16px',
              fontSize: '0.8rem'
            }}>
              <h4 style={{ margin: '0 0 8px 0', fontSize: '0.85rem', color: 'var(--text-primary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Execution Trace</span>
                <span className={`compiler-status-badge ${trace.status}`} style={{ fontSize: '0.7rem', padding: '2px 6px' }}>
                  {trace.status.toUpperCase()}
                </span>
              </h4>
              
              {trace.input && (
                <div style={{ marginTop: '8px' }}>
                  <span style={{ color: 'var(--text-secondary)', display: 'block', marginBottom: '2px' }}>Input:</span>
                  <pre style={{ margin: 0, padding: '6px', background: 'rgba(15, 23, 42, 0.6)', borderRadius: '4px', overflowX: 'auto', maxHeight: '100px', color: '#a5b4fc' }}>
                    {JSON.stringify(trace.input, null, 2)}
                  </pre>
                </div>
              )}

              {trace.output && (
                <div style={{ marginTop: '8px' }}>
                  <span style={{ color: 'var(--text-secondary)', display: 'block', marginBottom: '2px' }}>Output:</span>
                  <pre style={{ margin: 0, padding: '6px', background: 'rgba(15, 23, 42, 0.6)', borderRadius: '4px', overflowX: 'auto', maxHeight: '100px', color: '#86efac' }}>
                    {JSON.stringify(trace.output, null, 2)}
                  </pre>
                </div>
              )}

              {trace.error && (
                <div style={{ marginTop: '8px', color: '#f87171' }}>
                  <span style={{ display: 'block', marginBottom: '2px', fontWeight: 'bold' }}>Error:</span>
                  <div style={{ padding: '6px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '4px', whiteSpace: 'pre-wrap' }}>
                    {trace.error}
                  </div>
                </div>
              )}
            </div>
          )}
          {type !== 'start' && type !== 'end' && (
            <div className="form-group">
              <label>Display Label</label>
              <input
                type="text"
                className="form-input"
                value={data.label || ''}
                onChange={(e) => handleLabelChange(e.target.value)}
                placeholder="Node label"
              />
            </div>
          )}

          {type === 'input' && (
            <InputFieldsEditor
              fields={data.inputFields ?? []}
              onChange={(inputFields) => patch({ inputFields })}
            />
          )}

          {type === 'if' && (
            <IfConditionEditor
              condition={data.ifCondition ?? { left: '', operator: '==', right: '' }}
              onChange={(ifCondition) => patch({ ifCondition })}
            />
          )}

          {type === 'output' && (
            <OutputFieldsEditor
              fields={data.outputFields ?? []}
              onChange={(outputFields) => patch({ outputFields })}
            />
          )}

          {type === 'action' && (
            <>
              <div className="form-group">
                <label>Operation</label>
                <input
                  type="text"
                  className="form-input"
                  value={data.actionOperation || ''}
                  onChange={(e) => patch({ actionOperation: e.target.value })}
                  placeholder="e.g. transform, http_call, script"
                />
              </div>
              <div className="form-group">
                <label>Inputs</label>
                <textarea
                  className="form-textarea"
                  value={data.actionInputs || ''}
                  onChange={(e) => patch({ actionInputs: e.target.value })}
                  placeholder='e.g. {"user_id": "{{ctx.id}}"}'
                  rows={3}
                />
              </div>
              <div className="form-group">
                <label>Output</label>
                <input
                  type="text"
                  className="form-input"
                  value={data.actionOutput || ''}
                  onChange={(e) => patch({ actionOutput: e.target.value })}
                  placeholder="e.g. result.payload"
                />
              </div>
            </>
          )}

          {type === 'agent' && (
            <div className="form-group">
              <label>Agent</label>
              <select
                className="form-select"
                value={data.selectedAgentId || ''}
                onChange={(e) => {
                  const selectedAgentId = e.target.value;
                  const agent = AVAILABLE_AGENTS.find((a) => a.id === selectedAgentId);
                  patch({
                    selectedAgentId,
                    label: agent?.name ?? data.label,
                  });
                }}
              >
                <option value="">Select an agent…</option>
                {AVAILABLE_AGENTS.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
              {data.selectedAgentId && (
                <p className="form-hint">
                  {AVAILABLE_AGENTS.find((a) => a.id === data.selectedAgentId)?.description}
                </p>
              )}
            </div>
          )}

          {(type === 'start' || type === 'end') && (
            <p className="inspector-empty-hint">
              This node has no configuration. Connect it in the flow using edges on the canvas.
            </p>
          )}
        </div>
      </aside>
    );
  }

  if (selectedEdge) {
    const { id, source, target, data = {} } = selectedEdge;

    const handleEdgeChange = (key: keyof RFEdgeData, value: string) => {
      onUpdateEdge(id, { [key]: value });
    };

    return (
      <aside className="inspector">
        <div className="inspector-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings size={18} style={{ color: 'var(--accent)' }} />
            <h3 className="inspector-title">Edge Inspector</h3>
          </div>
          <span className="inspector-subtitle">ID: {id}</span>
        </div>

        <div className="inspector-form">
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Connection from <strong>{source}</strong> to <strong>{target}</strong>
          </div>

          <div className="form-group">
            <label>Edge Label</label>
            <input
              type="text"
              className="form-input"
              value={data.label || ''}
              onChange={(e) => handleEdgeChange('label', e.target.value)}
              placeholder="Optional label"
            />
          </div>

          <div className="form-group">
            <label>Branch (IF node targets)</label>
            <select
              className="form-select"
              value={data.branch || ''}
              onChange={(e) => handleEdgeChange('branch', e.target.value)}
            >
              <option value="">None</option>
              <option value="branch1">true (branch1)</option>
              <option value="branch2">false (branch2)</option>
            </select>
          </div>

          <div className="form-group">
            <label>Routing Condition</label>
            <input
              type="text"
              className="form-input"
              value={data.condition || ''}
              onChange={(e) => handleEdgeChange('condition', e.target.value)}
              placeholder="Optional edge condition"
            />
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside className="inspector">
      <div className="inspector-placeholder">
        <MousePointerClick size={48} />
        <p>Select a node or edge on the canvas to configure its parameters.</p>
      </div>
    </aside>
  );
};

function InputFieldsEditor({
  fields,
  onChange,
}: {
  fields: InputFieldRow[];
  onChange: (fields: InputFieldRow[]) => void;
}) {
  const updateRow = (rowId: string, patch: Partial<InputFieldRow>) => {
    onChange(fields.map((r) => (r.id === rowId ? { ...r, ...patch } : r)));
  };

  const addRow = () => {
    onChange([
      ...fields,
      { id: newRowId(), field: '', store_as: '', type: 'string' },
    ]);
  };

  const removeRow = (rowId: string) => {
    onChange(fields.filter((r) => r.id !== rowId));
  };

  return (
    <ArraySection title="Input Fields" onAdd={addRow}>
      {fields.length === 0 && (
        <p className="form-hint">Add fields to map incoming data (field → store_as).</p>
      )}
      {fields.map((row, index) => (
        <div key={row.id} className="array-item-card">
          <div className="array-item-header">
            <span>Field {index + 1}</span>
            <button type="button" className="btn-icon-danger" onClick={() => removeRow(row.id)} title="Remove">
              <Trash2 size={14} />
            </button>
          </div>
          <div className="form-group">
            <label>Field</label>
            <input
              className="form-input"
              value={row.field}
              onChange={(e) => updateRow(row.id, { field: e.target.value })}
              placeholder="e.g. user_message"
            />
          </div>
          <div className="form-group">
            <label>Store As</label>
            <input
              className="form-input"
              value={row.store_as}
              onChange={(e) => updateRow(row.id, { store_as: e.target.value })}
              placeholder="e.g. ctx.message"
            />
          </div>
          <TypeSelect
            value={row.type}
            onChange={(type) => updateRow(row.id, { type })}
          />
        </div>
      ))}
    </ArraySection>
  );
}

function OutputFieldsEditor({
  fields,
  onChange,
}: {
  fields: OutputFieldRow[];
  onChange: (fields: OutputFieldRow[]) => void;
}) {
  const updateRow = (rowId: string, patch: Partial<OutputFieldRow>) => {
    onChange(fields.map((r) => (r.id === rowId ? { ...r, ...patch } : r)));
  };

  const addRow = () => {
    onChange([...fields, { id: newRowId(), field: '', type: 'string' }]);
  };

  const removeRow = (rowId: string) => {
    onChange(fields.filter((r) => r.id !== rowId));
  };

  return (
    <ArraySection title="Output Fields" onAdd={addRow}>
      {fields.length === 0 && (
        <p className="form-hint">Add fields to define the workflow output shape.</p>
      )}
      {fields.map((row, index) => (
        <div key={row.id} className="array-item-card">
          <div className="array-item-header">
            <span>Field {index + 1}</span>
            <button type="button" className="btn-icon-danger" onClick={() => removeRow(row.id)} title="Remove">
              <Trash2 size={14} />
            </button>
          </div>
          <div className="form-group">
            <label>Field</label>
            <input
              className="form-input"
              value={row.field}
              onChange={(e) => updateRow(row.id, { field: e.target.value })}
              placeholder="e.g. response_text"
            />
          </div>
          <TypeSelect
            value={row.type}
            onChange={(type) => updateRow(row.id, { type })}
          />
        </div>
      ))}
    </ArraySection>
  );
}

function IfConditionEditor({
  condition,
  onChange,
}: {
  condition: IfCondition;
  onChange: (condition: IfCondition) => void;
}) {
  const set = (key: keyof IfCondition, value: string) => {
    onChange({ ...condition, [key]: value });
  };

  return (
    <>
      <div className="form-group">
        <label>Left</label>
        <input
          className="form-input"
          value={condition.left}
          onChange={(e) => set('left', e.target.value)}
          placeholder="e.g. ctx.intent"
        />
      </div>
      <div className="form-group">
        <label>Operator</label>
        <select
          className="form-select"
          value={condition.operator}
          onChange={(e) => set('operator', e.target.value)}
        >
          {IF_OPERATOR_OPTIONS.map((op) => (
            <option key={op.value} value={op.value}>
              {op.label}
            </option>
          ))}
        </select>
      </div>
      <div className="form-group">
        <label>Right</label>
        <input
          className="form-input"
          value={condition.right}
          onChange={(e) => set('right', e.target.value)}
          placeholder="e.g. billing"
        />
      </div>
    </>
  );
}

function TypeSelect({
  value,
  onChange,
}: {
  value: FieldDataType;
  onChange: (type: FieldDataType) => void;
}) {
  return (
    <div className="form-group">
      <label>Type</label>
      <select
        className="form-select"
        value={value}
        onChange={(e) => onChange(e.target.value as FieldDataType)}
      >
        {FIELD_TYPE_OPTIONS.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
    </div>
  );
}

function ArraySection({
  title,
  onAdd,
  children,
}: {
  title: string;
  onAdd: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="array-section">
      <div className="array-section-header">
        <label>{title}</label>
        <button type="button" className="btn btn-outline btn-sm" onClick={onAdd}>
          <Plus size={12} /> Add
        </button>
      </div>
      {children}
    </div>
  );
}
