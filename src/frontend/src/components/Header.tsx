import React, { useState } from 'react';
import type { Node, Edge } from 'reactflow';
import { Undo, Redo, GitMerge, Download, Code, RotateCcw, Copy, Check, Save, FolderOpen } from 'lucide-react';
import { WorkflowStorageModal } from './WorkflowStorageModal';
import type { RFNodeData, RFEdgeData } from '../types';
import { buildExportPayload } from '../utils/exportWorkflow';
import { compilerApi } from '../services/compilerApi';

interface HeaderProps {
  nodes: Node<RFNodeData>[];
  edges: Edge<RFEdgeData>[];
  onReset: () => void;
  onLoadTemplate: (name: string) => void;
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  onLoadWorkflow: (nodes: Node<RFNodeData>[], edges: Edge<RFEdgeData>[]) => void;
}

export const Header: React.FC<HeaderProps> = ({
  nodes,
  edges,
  onReset,
  onLoadTemplate,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  onLoadWorkflow,
}) => {
  const [storageModal, setStorageModal] = useState<'save' | 'load' | null>(null);
  const [dslModalOpen, setDslModalOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  // Compilation States
  const [compiledDsl, setCompiledDsl] = useState<any>(null);
  const [compiledAt, setCompiledAt] = useState<string | null>(null);
  const [compilationError, setCompilationError] = useState<string | null>(null);
  const [isCompiling, setIsCompiling] = useState(false);
  const [activeTab, setActiveTab] = useState<'dsl' | 'payload'>('dsl');
  const [sourcePayload, setSourcePayload] = useState<any>(null);

  const compileCurrentWorkflow = async () => {
    setIsCompiling(true);
    setCompilationError(null);
    try {
      const payload = buildExportPayload(nodes, edges);
      setSourcePayload(payload);

      const res = await compilerApi.compileWorkflow({
        nodes: payload.nodes,
        edges: payload.edges,
        workflow_id: 'workflow-builder-id',
      });

      setCompiledDsl(res.dsl);
      setCompiledAt(
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
          ' ' +
          new Date().toLocaleDateString()
      );
      return res.dsl;
    } catch (err: any) {
      const errMsg = err.message || 'Failed to compile workflow';
      setCompilationError(errMsg);
      setCompiledDsl(null);
      setCompiledAt(null);
      throw err;
    } finally {
      setIsCompiling(false);
    }
  };

  const openDslModal = async () => {
    setDslModalOpen(true);
    try {
      await compileCurrentWorkflow();
    } catch (err) {
      // Error is stored in compilationError state and rendered in modal
    }
  };

  const downloadDsl = () => {
    if (!compiledDsl) return;
    const dataStr =
      'data:text/json;charset=utf-8,' +
      encodeURIComponent(JSON.stringify(compiledDsl, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', 'workflow.dsl.json');
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleHeaderDownloadDsl = async () => {
    if (compiledDsl) {
      downloadDsl();
      return;
    }
    try {
      const dsl = await compileCurrentWorkflow();
      if (dsl) {
        const dataStr =
          'data:text/json;charset=utf-8,' +
          encodeURIComponent(JSON.stringify(dsl, null, 2));
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute('href', dataStr);
        downloadAnchor.setAttribute('download', 'workflow.dsl.json');
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
      }
    } catch (err) {
      // If compile fails, open modal to display failure explanation
      setDslModalOpen(true);
    }
  };

  const exportJson = () => {
    const payload = buildExportPayload(nodes, edges);
    const dataStr =
      'data:text/json;charset=utf-8,' +
      encodeURIComponent(JSON.stringify(payload, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', 'workflow.json');
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const copyToClipboard = () => {
    const textToCopy = activeTab === 'dsl' ? JSON.stringify(compiledDsl, null, 2) : JSON.stringify(sourcePayload, null, 2);
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      <header className="header">
        <div className="header-logo">
          <GitMerge size={26} />
          <h1 className="header-title">Workflow Builder Canvas</h1>
        </div>

        <div className="header-actions">
          <button className="btn btn-outline" onClick={onUndo} disabled={!canUndo}>
            <Undo size={14} style={{ opacity: canUndo ? 1 : 0.5 }} /> Undo
          </button>
          <button
            className="btn btn-outline"
            onClick={onRedo}
            disabled={!canRedo}
            style={{ marginLeft: '6px' }}
          >
            <Redo size={14} style={{ opacity: canRedo ? 1 : 0.5 }} /> Redo
          </button>
          <button className="btn" onClick={() => onLoadTemplate('customer_support')}>
            Load Demo
          </button>

          <button className="btn" onClick={onReset}>
            <RotateCcw size={14} /> Reset
          </button>

          <button className="btn btn-outline" onClick={() => setStorageModal('save')}>
            <Save size={14} /> Save
          </button>
          <button className="btn btn-outline" onClick={() => setStorageModal('load')}>
            <FolderOpen size={14} /> Open
          </button>

          <button className="btn btn-outline" onClick={openDslModal}>
            <Code size={14} /> View DSL
          </button>

          <button className="btn btn-outline" onClick={handleHeaderDownloadDsl}>
            <Download size={14} /> Download DSL
          </button>

          <button className="btn btn-primary" onClick={exportJson}>
            Export JSON
          </button>
        </div>
      </header>

      {storageModal && (
        <WorkflowStorageModal
          mode={storageModal}
          nodes={nodes}
          edges={edges}
          onClose={() => setStorageModal(null)}
          onLoad={onLoadWorkflow}
        />
      )}

      {dslModalOpen && (
        <div className="modal-overlay" onClick={() => setDslModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Workflow Compilation</h3>
                {isCompiling && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Compiling...</span>
                )}
                {!isCompiling && compilationError && (
                  <span className="compiler-status-badge error">✗ Compilation Failed</span>
                )}
                {!isCompiling && compiledDsl && (
                  <span className="compiler-status-badge success">✓ Compiler Passed</span>
                )}
              </div>
              <button className="close-btn" onClick={() => setDslModalOpen(false)}>
                &times;
              </button>
            </div>
            <div className="modal-body">
              {isCompiling ? (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Compiling graph...</div>
                </div>
              ) : compilationError ? (
                <div style={{ padding: '16px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', borderRadius: '8px', color: '#f87171', fontSize: '0.875rem', marginBottom: '12px', whiteSpace: 'pre-wrap' }}>
                  <strong>Compilation Error:</strong>
                  <div style={{ marginTop: '8px', fontFamily: 'monospace' }}>{compilationError}</div>
                </div>
              ) : (
                <>
                  <div className="modal-tabs">
                    <button
                      className={`modal-tab-btn ${activeTab === 'dsl' ? 'active' : ''}`}
                      onClick={() => setActiveTab('dsl')}
                    >
                      Generated DSL
                    </button>
                    <button
                      className={`modal-tab-btn ${activeTab === 'payload' ? 'active' : ''}`}
                      onClick={() => setActiveTab('payload')}
                    >
                      Workflow JSON
                    </button>
                    {compiledAt && (
                      <span className="compiler-timestamp">Generated At: {compiledAt}</span>
                    )}
                  </div>
                  {activeTab === 'dsl' ? (
                    <pre className="dsl-pre">{JSON.stringify(compiledDsl, null, 2)}</pre>
                  ) : (
                    <pre className="dsl-pre" style={{ color: '#a5b4fc' }}>{JSON.stringify(sourcePayload, null, 2)}</pre>
                  )}
                </>
              )}
            </div>
            <div className="modal-footer">
              {!isCompiling && compiledDsl && (
                <>
                  <button className="btn btn-outline" onClick={copyToClipboard}>
                    {copied ? (
                      <Check size={14} style={{ color: '#10b981' }} />
                    ) : (
                      <Copy size={14} />
                    )}
                    {copied ? 'Copied!' : 'Copy to Clipboard'}
                  </button>
                  <button className="btn btn-primary" onClick={downloadDsl}>
                    <Download size={14} /> Download DSL
                  </button>
                </>
              )}
              <button className="btn btn-outline" onClick={() => setDslModalOpen(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
