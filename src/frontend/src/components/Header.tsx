import React, { useState, useRef } from 'react';
import type { Node, Edge } from 'reactflow';
import { Undo, Redo, GitMerge, Download, Code, RotateCcw, Upload, FileJson, Copy, ChevronDown } from 'lucide-react';
import type { RFNodeData, RFEdgeData } from '../types';
import { EXAMPLES } from '../constants/examples';

interface HeaderProps {
  onReset: () => void;
  onLoadExample: (key: string) => void;
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  isCompiled: boolean;
  onValidateAndCompile: () => void;
  isCompiling: boolean;
  onViewDslClick: () => void;
  onDownloadDsl: () => void;
  onCopyDsl: () => void;
  onExportJson: () => void;
  onImportJson: (nodes: Node<RFNodeData>[], edges: Edge<RFEdgeData>[], metadata: any) => void;
}

export const Header: React.FC<HeaderProps> = ({
  onReset,
  onLoadExample,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  isCompiled,
  onValidateAndCompile,
  isCompiling,
  onViewDslClick,
  onDownloadDsl,
  onCopyDsl,
  onExportJson,
  onImportJson,
}) => {
  const [exampleOpen, setExampleOpen] = useState(false);
  const [dslOpen, setDslOpen] = useState(false);
  const [jsonOpen, setJsonOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const toggleExample = () => {
    setExampleOpen(!exampleOpen);
    setDslOpen(false);
    setJsonOpen(false);
  };
  const toggleDsl = () => {
    if (!isCompiled) return;
    setDslOpen(!dslOpen);
    setExampleOpen(false);
    setJsonOpen(false);
  };
  const toggleJson = () => {
    setJsonOpen(!jsonOpen);
    setExampleOpen(false);
    setDslOpen(false);
  };

  const handleImportJson = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target?.result as string);
        if (data.nodes && data.edges) {
          onImportJson(data.nodes, data.edges, data.metadata || {
            workflow_id: data.workflow_id || 'imported-workflow',
            workflow_type: data.workflow_type || 'imported-type',
            task_queue: data.task_queue || 'default',
            version: data.version || '1.0.0',
            description: data.description || '',
          });
        } else {
          alert('Invalid JSON: nodes or edges are missing.');
        }
      } catch (err: any) {
        alert(`Failed to parse file: ${err.message}`);
      }
    };
    reader.readAsText(file);
    e.target.value = ''; // Reset file input
  };

  return (
    <header className="header">
      <div className="header-logo">
        <GitMerge size={26} />
        <div>
          <h1 className="header-title" style={{ margin: 0, lineHeight: 1.1 }}>Workflow Builder</h1>
          <span style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'block', marginTop: '2px', fontWeight: '500', letterSpacing: '0.5px' }}>Visual DSL Compiler</span>
        </div>
      </div>

      <div className="header-actions" style={{ gap: '12px', alignItems: 'center' }}>
        {/* Group 1 — Workflow */}
        <div style={{ position: 'relative' }}>
          <button 
            className="btn" 
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            onClick={toggleExample}
          >
            Load Example <ChevronDown size={14} />
          </button>
          {exampleOpen && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              background: '#1e293b',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              marginTop: '4px',
              zIndex: 1000,
              display: 'flex',
              flexDirection: 'column',
              minWidth: '200px',
              boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)',
              overflow: 'hidden'
            }}>
              {Object.entries(EXAMPLES).map(([key, item]) => (
                <button
                  key={key}
                  onClick={() => {
                    onLoadExample(key);
                    setExampleOpen(false);
                  }}
                  style={{
                    padding: '10px 16px',
                    textAlign: 'left',
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    width: '100%',
                    transition: 'background 0.2s',
                    borderBottom: '1px solid rgba(255,255,255,0.03)'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
                >
                  {item.name}
                </button>
              ))}
            </div>
          )}
        </div>

        <div style={{ width: '1px', height: '24px', background: 'var(--border-color)', margin: '0 4px' }} />

        {/* Group 2 — Editing */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button className="btn btn-outline btn-icon" onClick={onUndo} disabled={!canUndo} title="Undo">
            <Undo size={15} style={{ opacity: canUndo ? 1 : 0.4 }} />
          </button>
          <button className="btn btn-outline btn-icon" onClick={onRedo} disabled={!canRedo} title="Redo">
            <Redo size={15} style={{ opacity: canRedo ? 1 : 0.4 }} />
          </button>
          <button className="btn btn-outline btn-icon" onClick={onReset} title="Reset Canvas">
            <RotateCcw size={15} />
          </button>
        </div>

        <div style={{ width: '1px', height: '24px', background: 'var(--border-color)', margin: '0 4px' }} />

        {/* Group 3 — Compiler */}
        <button 
          className="btn" 
          style={{ 
            borderColor: isCompiled ? '#10b981' : 'var(--accent)', 
            color: '#ffffff',
            background: isCompiled ? '#10b981' : 'var(--accent)',
            fontWeight: '600',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }} 
          onClick={onValidateAndCompile}
          disabled={isCompiling}
        >
          <GitMerge size={15} className={isCompiling ? 'spin' : ''} />
          {isCompiling ? 'Compiling...' : 'Validate & Compile'}
        </button>

        <div style={{ width: '1px', height: '24px', background: 'var(--border-color)', margin: '0 4px' }} />

        {/* Group 4 — DSL */}
        <div style={{ position: 'relative' }}>
          <button 
            className="btn btn-outline" 
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            onClick={toggleDsl}
            disabled={!isCompiled}
            title={isCompiled ? "DSL Operations" : "Compile workflow first to use DSL"}
          >
            DSL <ChevronDown size={14} style={{ opacity: isCompiled ? 1 : 0.5 }} />
          </button>
          {dslOpen && (
            <div style={{
              position: 'absolute',
              top: '100%',
              right: 0,
              background: '#1e293b',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              marginTop: '4px',
              zIndex: 1000,
              display: 'flex',
              flexDirection: 'column',
              minWidth: '160px',
              boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)',
              overflow: 'hidden'
            }}>
              <button
                onClick={() => {
                  onViewDslClick();
                  setDslOpen(false);
                }}
                style={{
                  padding: '10px 16px',
                  textAlign: 'left',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  transition: 'background 0.2s',
                  borderBottom: '1px solid rgba(255,255,255,0.03)'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
              >
                <Code size={12} /> View DSL
              </button>
              <button
                onClick={() => {
                  onDownloadDsl();
                  setDslOpen(false);
                }}
                style={{
                  padding: '10px 16px',
                  textAlign: 'left',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  transition: 'background 0.2s',
                  borderBottom: '1px solid rgba(255,255,255,0.03)'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
              >
                <Download size={12} /> Download DSL
              </button>
              <button
                onClick={() => {
                  onCopyDsl();
                  setDslOpen(false);
                }}
                style={{
                  padding: '10px 16px',
                  textAlign: 'left',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
              >
                <Copy size={12} /> Copy DSL
              </button>
            </div>
          )}
        </div>

        <div style={{ width: '1px', height: '24px', background: 'var(--border-color)', margin: '0 4px' }} />

        {/* Group 5 — JSON */}
        <div style={{ position: 'relative' }}>
          <button 
            className="btn btn-outline" 
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            onClick={toggleJson}
          >
            JSON <ChevronDown size={14} />
          </button>
          {jsonOpen && (
            <div style={{
              position: 'absolute',
              top: '100%',
              right: 0,
              background: '#1e293b',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              marginTop: '4px',
              zIndex: 1000,
              display: 'flex',
              flexDirection: 'column',
              minWidth: '180px',
              boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)',
              overflow: 'hidden'
            }}>
              <button
                onClick={() => {
                  fileInputRef.current?.click();
                  setJsonOpen(false);
                }}
                style={{
                  padding: '10px 16px',
                  textAlign: 'left',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  transition: 'background 0.2s',
                  borderBottom: '1px solid rgba(255,255,255,0.03)'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
              >
                <Upload size={12} /> Import Workflow JSON
              </button>
              <button
                onClick={() => {
                  onExportJson();
                  setJsonOpen(false);
                }}
                style={{
                  padding: '10px 16px',
                  textAlign: 'left',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
                onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
              >
                <FileJson size={12} /> Export Workflow JSON
              </button>
            </div>
          )}
        </div>
        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          accept=".json" 
          onChange={handleImportJson} 
        />
      </div>
    </header>
  );
};
