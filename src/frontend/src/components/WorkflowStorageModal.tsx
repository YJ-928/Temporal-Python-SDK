import React, { useState } from 'react';
import type { Node, Edge } from 'reactflow';
import { Save, FolderOpen, Trash2 } from 'lucide-react';
import type { RFNodeData, RFEdgeData } from '../types';
import {
  listSavedWorkflows,
  saveWorkflowLocally,
  getSavedWorkflow,
  deleteSavedWorkflow,
  type StoredWorkflowSummary,
} from '../utils/localWorkflowStorage';

type ModalMode = 'save' | 'load';

interface WorkflowStorageModalProps {
  mode: ModalMode;
  nodes: Node<RFNodeData>[];
  edges: Edge<RFEdgeData>[];
  onClose: () => void;
  onLoad: (nodes: Node<RFNodeData>[], edges: Edge<RFEdgeData>[]) => void;
}

export const WorkflowStorageModal: React.FC<WorkflowStorageModalProps> = ({
  mode,
  nodes,
  edges,
  onClose,
  onLoad,
}) => {
  const [workflowName, setWorkflowName] = useState('');
  const [savedList, setSavedList] = useState<StoredWorkflowSummary[]>(() => listSavedWorkflows());
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(
    null
  );
  const [overwriteId, setOverwriteId] = useState<string | null>(null);

  const refreshList = () => setSavedList(listSavedWorkflows());

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  const handleSave = () => {
    if (nodes.length === 0) {
      setMessage({ type: 'error', text: 'Canvas is empty. Add nodes before saving.' });
      return;
    }
    const saved = saveWorkflowLocally(workflowName, nodes, edges, overwriteId ?? undefined);
    setMessage({ type: 'success', text: `Saved "${saved.name}" to this browser.` });
    setWorkflowName('');
    setOverwriteId(null);
    refreshList();
  };

  const handleLoad = (id: string) => {
    const workflow = getSavedWorkflow(id);
    if (!workflow) {
      setMessage({ type: 'error', text: 'Workflow not found. It may have been deleted.' });
      refreshList();
      return;
    }
    onLoad(workflow.nodes, workflow.edges);
    onClose();
  };

  const handleDelete = (id: string, name: string) => {
    if (!window.confirm(`Delete "${name}" from local storage?`)) return;
    deleteSavedWorkflow(id);
    if (overwriteId === id) {
      setOverwriteId(null);
      setWorkflowName('');
    }
    refreshList();
    setMessage({ type: 'success', text: `Deleted "${name}".` });
  };

  const startOverwrite = (item: StoredWorkflowSummary) => {
    setOverwriteId(item.id);
    setWorkflowName(item.name);
    setMessage(null);
  };

  const isSave = mode === 'save';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content workflow-storage-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 style={{ margin: 0, fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: 8 }}>
            {isSave ? <Save size={18} /> : <FolderOpen size={18} />}
            {isSave ? 'Save workflow locally' : 'Open saved workflow'}
          </h3>
          <button className="close-btn" type="button" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="modal-body">
          {isSave && (
            <>
              <p className="workflow-storage-hint">
                Workflows are stored in this browser&apos;s local storage and stay on this device.
              </p>
              <label className="workflow-storage-label" htmlFor="workflow-save-name">
                Workflow name
              </label>
              <input
                id="workflow-save-name"
                className="workflow-storage-input"
                type="text"
                placeholder="e.g. Customer support v2"
                value={workflowName}
                onChange={(e) => {
                  setWorkflowName(e.target.value);
                  setOverwriteId(null);
                  setMessage(null);
                }}
                onKeyDown={(e) => e.key === 'Enter' && handleSave()}
              />
              {overwriteId && (
                <p className="workflow-storage-overwrite-note">
                  Updating existing save — choose another name to save as new.
                </p>
              )}
            </>
          )}

          {!isSave && (
            <p className="workflow-storage-hint">
              Select a workflow saved on this device to load it onto the canvas.
            </p>
          )}

          {message && (
            <p
              className={`workflow-storage-message workflow-storage-message--${message.type}`}
            >
              {message.text}
            </p>
          )}

          <div className="workflow-storage-list-header">
            <span>Saved workflows ({savedList.length})</span>
          </div>

          {savedList.length === 0 ? (
            <p className="workflow-storage-empty">No workflows saved yet.</p>
          ) : (
            <ul className="workflow-storage-list">
              {savedList.map((item) => (
                <li key={item.id} className="workflow-storage-item">
                  <div className="workflow-storage-item-main">
                    <span className="workflow-storage-item-name">{item.name}</span>
                    <span className="workflow-storage-item-meta">
                      {item.nodeCount} nodes · {item.edgeCount} edges · {formatDate(item.updatedAt)}
                    </span>
                  </div>
                  <div className="workflow-storage-item-actions">
                    {!isSave && (
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={() => handleLoad(item.id)}
                      >
                        Load
                      </button>
                    )}
                    {isSave && (
                      <button
                        type="button"
                        className="btn btn-outline btn-sm"
                        onClick={() => startOverwrite(item)}
                      >
                        Overwrite
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn btn-outline btn-sm workflow-storage-delete"
                      onClick={() => handleDelete(item.id, item.name)}
                      title="Delete"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-outline" onClick={onClose}>
            Cancel
          </button>
          {isSave && (
            <button type="button" className="btn btn-primary" onClick={handleSave}>
              <Save size={14} /> {overwriteId ? 'Update' : 'Save'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
