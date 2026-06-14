import React, { useState } from 'react';
import { Undo, Redo, GitMerge, RotateCcw, ZoomIn, ZoomOut, Maximize, Settings, Play } from 'lucide-react';

const AutoXLogo: React.FC<{ size?: number }> = ({ size = 32 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-label="AutoX"
  >
    <path d="M28.4 7.04H21.04L3.2 24.96H10.56L28.4 7.04Z" fill="#F3702A" />
    <path d="M3.2 7.04H10.56L28.4 24.96H21.04L3.2 7.04Z" fill="#F3702A" />
  </svg>
);
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
  hasNodes: boolean;
  onExecute: () => void;
  isExecuting: boolean;
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onFitView?: () => void;
  isSettingsOpen: boolean;
  onSettingsToggle: () => void;
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
  hasNodes,
  onExecute,
  isExecuting,
  onZoomIn,
  onZoomOut,
  onFitView,
  isSettingsOpen,
  onSettingsToggle,
}) => {
  const [exampleOpen, setExampleOpen] = useState(false);

  const toggleExample = () => {
    setExampleOpen(!exampleOpen);
  };

  return (
    <header className="header">
      <div className="header-logo">
        <div className="brand-logo-slot">
          <AutoXLogo size={36} />
        </div>
        <div>
          <h1 className="header-title" style={{ margin: 0, lineHeight: 1.1 }}>FlowAutomate</h1>
          <span className="header-subtitle">Visual Workflow Automation Platform</span>
        </div>
      </div>

      <div className="header-actions" style={{ gap: '12px', alignItems: 'center' }}>
        {/* Group 1 — Workflow Loader */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
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
        </div>

        <div style={{ width: '1px', height: '24px', background: 'var(--border-color)', margin: '0 4px' }} />

        {/* Group 2 — Editing & Canvas Controls */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button className="btn btn-outline btn-icon" onClick={onUndo} disabled={!canUndo} title="Undo (Ctrl+Z)">
            <Undo size={15} style={{ opacity: canUndo ? 1 : 0.4 }} />
          </button>
          <button className="btn btn-outline btn-icon" onClick={onRedo} disabled={!canRedo} title="Redo (Ctrl+Y)">
            <Redo size={15} style={{ opacity: canRedo ? 1 : 0.4 }} />
          </button>
          <button className="btn btn-outline btn-icon" onClick={onReset} title="Reset Canvas">
            <RotateCcw size={15} />
          </button>
          
          <div style={{ width: '1px', height: '24px', background: 'var(--border-color)', margin: '0 4px', alignSelf: 'center' }} />
          
          <button className="btn btn-outline btn-icon" onClick={onZoomOut} title="Zoom Out">
            <ZoomOut size={15} />
          </button>
          <button className="btn btn-outline btn-icon" onClick={onZoomIn} title="Zoom In">
            <ZoomIn size={15} />
          </button>
          <button className="btn btn-outline btn-icon" onClick={onFitView} title="Fit View">
            <Maximize size={15} />
          </button>
        </div>

        <div style={{ width: '1px', height: '24px', background: 'var(--border-color)', margin: '0 4px' }} />

        {/* Group 3 — Compiler & Runner */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button 
            className="btn" 
            style={{ 
              borderColor: 'var(--accent)', 
              color: '#ffffff',
              background: 'var(--accent)',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }} 
            onClick={onValidateAndCompile}
            disabled={isCompiling || !hasNodes}
            title={hasNodes ? 'Validate & Compile (Ctrl+Enter)' : 'Add nodes to begin building a workflow'}
          >
            <GitMerge size={15} className={isCompiling ? 'spin' : ''} />
            {isCompiling ? 'Compiling...' : 'Validate & Compile'}
          </button>

          <button 
            className="btn" 
            style={{ 
              borderColor: '#10b981', 
              color: '#ffffff',
              background: '#10b981',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              opacity: isCompiled ? 1 : 0.5,
              cursor: isCompiled ? 'pointer' : 'not-allowed'
            }} 
            onClick={onExecute}
            disabled={!isCompiled || isExecuting}
            title={isCompiled ? "Execute Workflow" : "Compile workflow first to execute"}
          >
            <Play size={15} />
            {isExecuting ? 'Running...' : 'Execute'}
          </button>
        </div>

        <div style={{ width: '1px', height: '24px', background: 'var(--border-color)', margin: '0 4px' }} />

        {/* Group 4 — Settings Drawer Toggle */}
        <button 
          className={`btn btn-outline btn-icon ${isSettingsOpen ? 'active' : ''}`} 
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            borderColor: isSettingsOpen ? 'var(--accent)' : 'var(--border-color)',
            background: isSettingsOpen ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
            color: isSettingsOpen ? 'var(--accent)' : 'var(--text-primary)'
          }}
          onClick={onSettingsToggle}
          title="Workflow Settings, DSL Actions, Import / Export"
        >
          <Settings size={15} />
        </button>
      </div>
    </header>
  );
};

// Simple ChevronDown helper component for Loader dropdown since we removed other icon imports
const ChevronDown: React.FC<{ size?: number; style?: React.CSSProperties }> = ({ size = 14, style }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2" 
    strokeLinecap="round" 
    strokeLinejoin="round" 
    style={style}
  >
    <path d="m6 9 6 6 6-6"/>
  </svg>
);
