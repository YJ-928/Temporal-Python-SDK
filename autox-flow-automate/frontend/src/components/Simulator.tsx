import React, { useRef, useEffect, useState, useMemo } from 'react';
import { Trash2, ChevronDown, ChevronUp, RefreshCw, Zap, History, Activity, ChevronRight, Gauge, ChevronLeft, Copy, Maximize } from 'lucide-react';
import { notify } from '../utils/notify';

const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
const EMAIL_WORKFLOW_IDS = new Set(['email-validation-sender', 'single-email-validator']);

interface StatusStyle { color: string; label: string }
const STATUS_CONFIG: Record<string, StatusStyle> = {
  COMPLETED:  { color: '#10b981', label: 'Completed' },
  RUNNING:    { color: '#3b82f6', label: 'Running' },
  FAILED:     { color: '#ef4444', label: 'Failed' },
  CANCELED:   { color: '#f59e0b', label: 'Canceled' },
  TERMINATED: { color: '#f97316', label: 'Terminated' },
  TIMED_OUT:  { color: '#f97316', label: 'Timed Out' },
};
const STEP_STATUS_CONFIG: Record<string, string> = {
  completed: '#10b981',
  running:   '#3b82f6',
  failed:    '#ef4444',
  skipped:   '#64748b',
};
function getStatusStyle(raw: string): StatusStyle {
  return STATUS_CONFIG[raw?.toUpperCase()] ?? { color: '#64748b', label: raw || 'Unknown' };
}
function getStepColor(status: string): string {
  return STEP_STATUS_CONFIG[status] ?? '#64748b';
}
import type { WorkflowMetadata, ExecutionRun, NodeTraceState } from '../types';

export interface LogEntry {
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'text';
  message: string;
}

export type TabType = 'execution' | 'trace' | 'compilation_log' | 'dsl' | 'metrics';

interface SimulatorProps {
  logs: LogEntry[];
  onClearLogs: () => void;

  // Compilation state
  isCompiled: boolean;
  compiledDsl: Record<string, unknown> | null;
  compiledHash: string;
  compiledAt: string;
  metadata: WorkflowMetadata;

  // Temporal runner
  executionHistory: ExecutionRun[];
  activeRunId: string | null;
  setActiveRunId: (runId: string | null) => void;
  onTriggerTemporalRun: (inputData: Record<string, unknown>) => void;
  onRefreshHistory: () => void;
  isTriggeringRun: boolean;
  onCancelRun?: (workflowId: string, runId: string) => void;
  onTerminateRun?: (workflowId: string, runId: string, reason: string) => void;
  nodeTraceStates?: Record<string, NodeTraceState>;
  activeRunStatus?: string;

  // Control tabs and visibility
  activeTab: TabType;
  setActiveTab: (tab: TabType) => void;
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  isSettingsOpen?: boolean;

  // Lifted state
  inputJson: string;
  setInputJson: (input: string) => void;
  panelHeight: number;
  setPanelHeight: (height: number) => void;
}

export const Simulator: React.FC<SimulatorProps> = ({
  logs,
  onClearLogs,
  isCompiled,
  compiledDsl,
  compiledHash,
  compiledAt,
  metadata,
  executionHistory,
  activeRunId,
  setActiveRunId,
  onTriggerTemporalRun,
  onRefreshHistory,
  isTriggeringRun,
  onCancelRun,
  onTerminateRun,
  nodeTraceStates = {},
  activeRunStatus,
  activeTab,
  setActiveTab,
  isOpen,
  setIsOpen,
  isSettingsOpen = false,
  inputJson,
  setInputJson,
  panelHeight,
  setPanelHeight,
}) => {
  const consoleEndRef = useRef<HTMLDivElement>(null);
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});

  // Layout resizing & collapse states
  const [isResizing, setIsResizing] = useState<boolean>(false);
  const [isHistoryCollapsed, setIsHistoryCollapsed] = useState<boolean>(false);
  const [isDslExpanded, setIsDslExpanded] = useState<boolean>(false);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newHeight = window.innerHeight - e.clientY;
      const clampedHeight = Math.max(48, Math.min(newHeight, window.innerHeight * 0.7));
      setPanelHeight(clampedHeight);
      
      if (clampedHeight <= 55) {
        setIsOpen(false);
      } else {
        setIsOpen(true);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      localStorage.setItem('workflow-runtime-height', panelHeight.toString());
    };

    globalThis.addEventListener('mousemove', handleMouseMove);
    globalThis.addEventListener('mouseup', handleMouseUp);

    return () => {
      globalThis.removeEventListener('mousemove', handleMouseMove);
      globalThis.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, panelHeight, setIsOpen, setPanelHeight]);

  useEffect(() => {
    if (consoleEndRef.current && activeTab === 'compilation_log') {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, activeTab]);

  // Set default JSON input based on selected workflow id/type
  useEffect(() => {
    const wfId = metadata.workflow_id;
    if (wfId === 'weather-assistant') {
      setInputJson('{\n  "city": "kolkata"\n}');
    } else if (wfId === 'email-validation-sender') {
      setInputJson('{\n  "email": "test@domain.com",\n  "subject": "Greetings",\n  "message": "Hello from FlowAutomate!"\n}');
    } else if (wfId === 'account-routing') {
      setInputJson('{\n  "account_id": "ACC-789"\n}');
    } else if (wfId === 'single-email-validator') {
      setInputJson('{\n  "email": "verify-me@test.com"\n}');
    } else {
      setInputJson('{\n  "city": "kolkata"\n}');
    }
  }, [metadata.workflow_id, setInputJson]);

  const activeRun = executionHistory.find((r) => r.run_id === activeRunId);
  const currentStatus = activeRunStatus || activeRun?.status || 'UNKNOWN';

  const runDuration = useMemo(() => {
    if (!activeRun?.start_time || !activeRun.close_time) return null;
    const start = new Date(activeRun.start_time).getTime();
    const end = new Date(activeRun.close_time).getTime();
    return `${((end - start) / 1000).toFixed(2)}s`;
  }, [activeRun]);

  const freshness = useMemo(() => {
    if (!compiledAt) return '';
    return new Date(compiledAt).toLocaleTimeString();
  }, [compiledAt]);

  const handleExecute = () => {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(inputJson) as Record<string, unknown>;
    } catch (e) {
      notify.error(`Invalid JSON format: ${(e as Error).message}`);
      return;
    }

    if (EMAIL_WORKFLOW_IDS.has(metadata.workflow_id)) {
      const email = parsed.email;
      if (!email || typeof email !== 'string' || !EMAIL_REGEX.test(email.trim())) {
        notify.error('Invalid email address. Please enter a valid email before executing.');
        return;
      }
    }

    onTriggerTemporalRun(parsed);
    setActiveTab('trace');
  };

  const toggleExpandNode = (nodeId: string) => {
    setExpandedNodes((prev) => ({
      ...prev,
      [nodeId]: !prev[nodeId],
    }));
  };

  const panelClasses = [
    'simulator-panel',
    !isResizing ? 'transition-height' : '',
    !isSettingsOpen ? 'drawer-collapsed' : ''
  ].filter(Boolean).join(' ');

  return (
    <div 
      className={panelClasses} 
      style={{ height: isOpen ? (isDslExpanded ? '88vh' : `${panelHeight}px`) : '48px' }}
    >
      {/* Draggable splitter handle */}
      {isOpen && !isDslExpanded && (
        <div 
          className="runtime-resize-handle"
          onMouseDown={handleMouseDown}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '4px',
            cursor: 'ns-resize',
            zIndex: 100,
            background: isResizing ? 'var(--accent)' : 'transparent',
            transition: 'background 0.2s'
          }}
        />
      )}

      <div className="simulator-header" style={{ background: '#0f172a' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div className="simulator-title" style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>
            <Activity size={14} style={{ color: 'var(--accent)' }} />
            <span>Workflow Runtime</span>
          </div>
        </div>

        <div className="simulator-controls">
          <button className="close-btn" onClick={() => {
            setIsOpen(!isOpen);
            if (isOpen) setIsDslExpanded(false); // Restore if closing
          }}>
            {isOpen ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </button>
        </div>
      </div>

      {isOpen && (
        <div style={{ display: 'flex', height: isDslExpanded ? 'calc(88vh - 40px)' : `${panelHeight - 40}px`, overflow: 'hidden' }}>
          {/* Run History Sidebar */}
          <div style={{
            width: isHistoryCollapsed ? '0px' : '220px',
            borderRight: isHistoryCollapsed ? 'none' : '1px solid var(--border-color)',
            background: 'rgba(15, 23, 42, 0.4)',
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            overflow: 'hidden',
            transition: 'width 0.25s cubic-bezier(0.4, 0, 0.2, 1), border-right 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
            position: 'relative'
          }}>
            <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border-color)', fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontWeight: 'bold', whiteSpace: 'nowrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <History size={12} />
                <span>Execution History</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <button 
                  onClick={onRefreshHistory} 
                  style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0 }}
                  title="Refresh History"
                >
                  <RefreshCw size={11} />
                </button>
                <button 
                  onClick={() => setIsHistoryCollapsed(true)} 
                  style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0 }}
                  title="Collapse History"
                >
                  <ChevronLeft size={12} />
                </button>
              </div>
            </div>
            <div style={{ overflowY: 'auto', flex: 1, padding: '4px' }}>
              {executionHistory.length === 0 ? (
                <div style={{ padding: '24px 16px', fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '6px', alignItems: 'center', justifyContent: 'center', whiteSpace: 'pre-line' }}>
                  {"No executions yet.\n\nCompile and execute a workflow."}
                </div>
              ) : (
                executionHistory.map((run) => {
                  const isSelected = run.run_id === activeRunId;
                  const { color: statusColor, label: statusLabel } = getStatusStyle(run.status);
                  
                  return (
                    <div
                      key={run.run_id}
                      onClick={() => {
                        setActiveRunId(run.run_id);
                        setActiveTab('trace');
                      }}
                      style={{
                        padding: '8px',
                        margin: '2px 0',
                        borderRadius: '6px',
                        background: isSelected ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                        border: isSelected ? '1px solid var(--accent)' : '1px solid transparent',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '2px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '11px', fontWeight: '600', color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '130px' }} title={run.workflow_id}>
                          {run.workflow_id}
                        </span>
                        <span style={{
                          fontSize: '8px',
                          color: statusColor,
                          fontWeight: 'bold',
                          border: `1px solid ${statusColor}40`,
                          borderRadius: '4px',
                          padding: '1px 4px',
                          background: `${statusColor}10`
                        }}>
                          {statusLabel}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: 'var(--text-muted)' }}>
                        <span>{run.run_id.slice(0, 8)}...</span>
                        <span>{run.start_time ? new Date(run.start_time).toLocaleTimeString() : ''}</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Main Workspace Area with Tabs */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', background: '#0b0f19' }}>
            {/* Tabs Bar */}
            <div className="modal-tabs" style={{ marginBottom: 0, padding: '0 16px', background: '#0a0d16', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center' }}>
              {isHistoryCollapsed && (
                <button
                  className="modal-tab-btn"
                  style={{
                    padding: '12px 16px',
                    fontSize: '11px',
                    color: 'var(--text-secondary)',
                    borderRight: '1px solid var(--border-color)',
                    marginRight: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    background: 'rgba(255, 255, 255, 0.02)'
                  }}
                  onClick={() => setIsHistoryCollapsed(false)}
                  title="Expand Execution History"
                >
                  <History size={11} />
                  <span>History &nbsp;▶</span>
                </button>
              )}
              <button
                className={`modal-tab-btn ${activeTab === 'execution' ? 'active' : ''}`}
                style={{ padding: '12px 16px', fontSize: '12px' }}
                onClick={() => setActiveTab('execution')}
              >
                Execution
              </button>
              <button
                className={`modal-tab-btn ${activeTab === 'trace' ? 'active' : ''}`}
                style={{ padding: '12px 16px', fontSize: '12px' }}
                onClick={() => setActiveTab('trace')}
              >
                Trace
              </button>
              <button
                className={`modal-tab-btn ${activeTab === 'compilation_log' ? 'active' : ''}`}
                style={{ padding: '12px 16px', fontSize: '12px' }}
                onClick={() => setActiveTab('compilation_log')}
              >
                Compilation Log
              </button>
              <button
                className={`modal-tab-btn ${activeTab === 'dsl' ? 'active' : ''}`}
                style={{ padding: '12px 16px', fontSize: '12px' }}
                onClick={() => setActiveTab('dsl')}
              >
                DSL
              </button>
              <button
                className={`modal-tab-btn ${activeTab === 'metrics' ? 'active' : ''}`}
                style={{ padding: '12px 16px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                onClick={() => setActiveTab('metrics')}
              >
                <Gauge size={12} /> Metrics
              </button>
            </div>

            {/* Tab Contents */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
              
              {/* TAB 1: EXECUTION */}
              {activeTab === 'execution' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: '600' }}>Workflow Input Payload (JSON)</span>
                    <button
                      className="btn btn-success"
                      style={{ 
                        padding: '6px 16px', 
                        fontSize: '11px', 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '6px',
                        opacity: isCompiled && !isTriggeringRun ? 1 : 0.5,
                        cursor: isCompiled && !isTriggeringRun ? 'pointer' : 'not-allowed'
                      }}
                      onClick={handleExecute}
                      disabled={!isCompiled || isTriggeringRun}
                    >
                      <Zap size={12} />
                      {isTriggeringRun ? 'Executing...' : 'Execute Workflow'}
                    </button>
                  </div>

                  <textarea
                    className="form-textarea"
                    style={{
                      fontFamily: 'monospace',
                      fontSize: '11px',
                      background: 'rgba(15, 23, 42, 0.6)',
                      color: '#38bdf8',
                      flex: 1,
                      minHeight: '120px',
                      resize: 'none',
                      border: '1px solid var(--border-color)',
                      borderRadius: '6px',
                      padding: '10px'
                    }}
                    value={inputJson}
                    onChange={(e) => setInputJson(e.target.value)}
                  />

                  {!isCompiled && (
                    <div style={{ padding: '8px 12px', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '6px', fontSize: '11px', color: '#fbbf24' }}>
                      ⚠️ Please validate & compile the workflow design in the toolbar before execution.
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: TRACE */}
              {activeTab === 'trace' && (
                <div>
                  {!activeRunId ? (
                    <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 20px', fontSize: '12px' }}>
                      No active execution selected. Select a run from the history sidebar or execute a new workflow.
                    </div>
                  ) : (
                    <div>
                      {/* Summary Block */}
                      <div style={{
                        background: 'rgba(15, 23, 42, 0.6)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        padding: '12px 16px',
                        marginBottom: '16px',
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                        gap: '12px',
                        fontSize: '11px'
                      }}>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '2px' }}>Workflow</span>
                          <strong style={{ color: 'var(--text-primary)' }}>{activeRun?.workflow_id || 'Unknown'}</strong>
                        </div>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '2px' }}>Run ID</span>
                          <span style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{activeRunId}</span>
                        </div>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '2px' }}>Status</span>
                          <strong style={{ color: getStatusStyle(currentStatus).color }}>
                            {getStatusStyle(currentStatus).label}
                          </strong>
                        </div>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '2px' }}>Started</span>
                          <span style={{ color: 'var(--text-secondary)' }}>
                            {activeRun?.start_time ? new Date(activeRun.start_time).toLocaleString() : ''}
                          </span>
                        </div>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '2px' }}>Duration</span>
                          <span style={{ color: 'var(--text-secondary)' }}>{runDuration ?? '--'}</span>
                        </div>
                        {(currentStatus === 'RUNNING' || currentStatus === 'running') && (
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            <button
                              onClick={() => onCancelRun && onCancelRun(activeRun?.workflow_id || metadata.workflow_id, activeRunId!)}
                              style={{
                                padding: '4px 8px',
                                fontSize: '10px',
                                border: '1px solid #fbbf24',
                                borderRadius: '4px',
                                color: '#fbbf24',
                                background: 'transparent',
                                cursor: 'pointer'
                              }}
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => {
                                if (onTerminateRun) {
                                  onTerminateRun(activeRun?.workflow_id || metadata.workflow_id, activeRunId!, 'Terminated by user');
                                }
                              }}
                              style={{
                                padding: '4px 8px',
                                fontSize: '10px',
                                border: '1px solid #f87171',
                                borderRadius: '4px',
                                color: '#f87171',
                                background: 'transparent',
                                cursor: 'pointer'
                              }}
                            >
                              Terminate
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Trace Timeline Table */}
                      <div style={{ border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', textAlign: 'left' }}>
                          <thead>
                            <tr style={{ background: '#0a0d16', borderBottom: '1px solid var(--border-color)' }}>
                              <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: '600' }}>Node Name</th>
                              <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: '600' }}>Type</th>
                              <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: '600' }}>Status</th>
                              <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: '600' }}>Duration</th>
                              <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: '600' }}>Payloads</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.keys(nodeTraceStates).length === 0 ? (
                              <tr>
                                <td colSpan={5} style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)' }}>
                                  No execution trace events found for this run.
                                </td>
                              </tr>
                            ) : (
                              Object.keys(nodeTraceStates).map((nodeId) => {
                                const step = nodeTraceStates[nodeId];
                                const isExpanded = expandedNodes[nodeId];
                                const statColor = getStepColor(step.status);

                                return (
                                  <React.Fragment key={nodeId}>
                                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                                      <td style={{ padding: '8px 12px', fontWeight: '600', color: 'var(--text-primary)' }}>{nodeId}</td>
                                      <td style={{ padding: '8px 12px', color: 'var(--text-muted)', textTransform: 'uppercase', fontSize: '10px' }}>{step.status === 'skipped' ? 'skipped' : 'task'}</td>
                                      <td style={{ padding: '8px 12px' }}>
                                        <span style={{ 
                                          color: statColor, 
                                          fontWeight: 'bold',
                                          border: `1px solid ${statColor}30`,
                                          borderRadius: '4px',
                                          padding: '1px 6px',
                                          background: `${statColor}08`
                                        }}>
                                          {step.status}
                                        </span>
                                      </td>
                                      <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>
                                        {step.duration_seconds !== undefined && step.duration_seconds !== null ? `${step.duration_seconds}s` : '--'}
                                      </td>
                                      <td style={{ padding: '8px 12px' }}>
                                        {(step.input || step.output || step.error) ? (
                                          <button
                                            onClick={() => toggleExpandNode(nodeId)}
                                            style={{
                                              background: 'none',
                                              border: 'none',
                                              color: 'var(--accent)',
                                              cursor: 'pointer',
                                              display: 'flex',
                                              alignItems: 'center',
                                              gap: '2px',
                                              fontSize: '10px',
                                              padding: 0
                                            }}
                                          >
                                            <ChevronRight size={10} style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }} />
                                            <span>{isExpanded ? 'Hide' : 'Inspect'}</span>
                                          </button>
                                        ) : (
                                          <span style={{ color: 'var(--text-muted)' }}>--</span>
                                        )}
                                      </td>
                                    </tr>

                                    {/* Collapsible payloads info */}
                                    {isExpanded && (
                                      <tr>
                                        <td colSpan={5} style={{ background: 'rgba(0, 0, 0, 0.2)', padding: '12px' }}>
                                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                            <div>
                                              <span style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Input Data</span>
                                              <pre style={{ margin: 0, padding: '8px', background: '#020617', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '4px', color: '#a5b4fc', overflowX: 'auto', maxLines: 5 }}>
                                                {step.input ? JSON.stringify(step.input, null, 2) : '{}'}
                                              </pre>
                                            </div>
                                            <div>
                                              <span style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Result / Error</span>
                                              {step.error ? (
                                                <div style={{ padding: '8px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '4px', color: '#f87171' }}>
                                                  {step.error}
                                                </div>
                                              ) : (
                                                <pre style={{ margin: 0, padding: '8px', background: '#020617', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '4px', color: '#86efac', overflowX: 'auto', maxLines: 5 }}>
                                                  {step.output ? JSON.stringify(step.output, null, 2) : '{}'}
                                                </pre>
                                              )}
                                            </div>
                                          </div>
                                        </td>
                                      </tr>
                                    )}
                                  </React.Fragment>
                                );
                              })
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: COMPILATION LOG */}
              {activeTab === 'compilation_log' && (
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Build Logs & Dynamic Events</span>
                    <button 
                      onClick={onClearLogs} 
                      style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      <Trash2 size={12} />
                      Clear Logs
                    </button>
                  </div>
                  <div className="simulator-console" style={{ background: '#020617', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '12px', flex: 1, maxHeight: '200px' }}>
                    {logs.length === 0 ? (
                      <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px' }}>
                        No logs printed. Validate/Compile or Run a workflow to view output logs.
                      </div>
                    ) : (
                      logs.map((log, index) => (
                        <div key={index} className={`console-line ${log.type}`}>
                          <span className="console-line-timestamp">[{log.timestamp}]</span>
                          {log.message}
                        </div>
                      ))
                    )}
                    <div ref={consoleEndRef} />
                  </div>
                </div>
              )}

              {/* TAB 4: DSL */}
              {activeTab === 'dsl' && (
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '12px' }}>
                  {isCompiled ? (
                    <>
                      {/* DSL Metadata Summary */}
                      <div style={{
                        background: 'rgba(15, 23, 42, 0.6)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        padding: '8px 12px',
                        display: 'grid',
                        gridTemplateColumns: 'repeat(5, 1fr)',
                        gap: '12px',
                        fontSize: '11px'
                      }}>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block' }}>Workflow Name</span>
                          <strong style={{ color: 'var(--text-primary)' }}>{metadata.workflow_id}</strong>
                        </div>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block' }}>Workflow Type</span>
                          <span style={{ color: 'var(--text-secondary)' }}>{metadata.workflow_type}</span>
                        </div>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block' }}>Description</span>
                          <span style={{ color: 'var(--text-secondary)' }} title={metadata.description}>
                            {metadata.description ? (metadata.description.length > 25 ? metadata.description.slice(0, 22) + '...' : metadata.description) : '--'}
                          </span>
                        </div>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block' }}>Hash</span>
                          <span style={{ fontFamily: 'monospace', color: 'var(--accent)' }}>{compiledHash}</span>
                        </div>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block' }}>Freshness</span>
                          <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>{compiledAt ? freshness : '--'}</span>
                        </div>
                      </div>

                      {/* DSL Controls & Header */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 'bold' }}>Generated Backend DSL</span>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            className="btn btn-outline"
                            style={{ padding: '4px 8px', fontSize: '10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                            onClick={() => {
                              navigator.clipboard.writeText(JSON.stringify(compiledDsl, null, 2))
                                .then(() => notify.success('DSL copied to clipboard.'))
                                .catch(() => notify.error('Failed to copy DSL to clipboard.'));
                            }}
                          >
                            <Copy size={10} />
                            Copy DSL
                          </button>
                          <button
                            className="btn btn-outline"
                            style={{ padding: '4px 8px', fontSize: '10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                            onClick={() => setIsDslExpanded(!isDslExpanded)}
                          >
                            <Maximize size={10} />
                            {isDslExpanded ? 'Restore View' : 'Expand View'}
                          </button>
                        </div>
                      </div>

                      {/* DSL Code Display */}
                      <pre className="dsl-pre" style={{ margin: 0, flex: 1, minHeight: 0, overflow: 'auto' }}>
                        <code>{JSON.stringify(compiledDsl, null, 2)}</code>
                      </pre>
                    </>
                  ) : (
                    <div style={{ padding: '40px 24px', background: 'rgba(255,255,255,0.01)', border: '1px dashed var(--border-color)', borderRadius: '8px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'center', justifyContent: 'center', margin: 'auto 0' }}>
                      <span style={{ fontSize: '18px' }}>📝</span>
                      <strong>Compile a workflow to generate DSL.</strong>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 5: METRICS */}
              {activeTab === 'metrics' && (() => {
                const totalRuns = executionHistory.length;
                const completedRunsCount = executionHistory.filter(run => run.status === 'COMPLETED' || run.status === 'completed').length;
                const successRateStr = totalRuns > 0 ? `${Math.round((completedRunsCount / totalRuns) * 100)}%` : '--';
                
                const completedRunsWithDuration = executionHistory.filter(run => 
                  (run.status === 'COMPLETED' || run.status === 'completed') && 
                  run.start_time && 
                  run.close_time
                );
                
                let averageDurationStr = '--';
                if (completedRunsWithDuration.length > 0) {
                  const totalDurationMs = completedRunsWithDuration.reduce((acc, run) => {
                    const start = new Date(run.start_time).getTime();
                    const end = new Date(run.close_time).getTime();
                    return acc + (end - start);
                  }, 0);
                  const avgSeconds = (totalDurationMs / completedRunsWithDuration.length) / 1000;
                  averageDurationStr = `${avgSeconds.toFixed(2)}s`;
                }

                return (
                  <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '12px' }}>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(3, 1fr)',
                      gap: '12px',
                      height: '100%',
                      maxHeight: '180px'
                    }}>
                      {/* Card 1: Compile Metrics */}
                      <div style={{
                        background: 'rgba(15, 23, 42, 0.4)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        padding: '12px 16px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        gap: '4px'
                      }}>
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Compiled Status</span>
                        <strong style={{ color: isCompiled ? '#10b981' : '#f59e0b', fontSize: '16px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: isCompiled ? '#10b981' : '#f59e0b', display: 'inline-block' }} />
                          {isCompiled ? 'Active & Registered' : 'Not Compiled'}
                        </strong>
                        <span style={{ color: 'var(--text-secondary)', fontSize: '10px', marginTop: '4px' }}>
                          Last compiled: {compiledAt ? new Date(compiledAt).toLocaleString() : 'Never'}
                        </span>
                      </div>

                      {/* Card 2: Executions & Success Rate */}
                      <div style={{
                        background: 'rgba(15, 23, 42, 0.4)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        padding: '12px 16px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        gap: '4px'
                      }}>
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Executions & Success</span>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
                          <span style={{ color: 'var(--text-primary)', fontSize: '20px', fontWeight: 'bold' }}>
                            {executionHistory.length} <span style={{ fontSize: '11px', fontWeight: 'normal', color: 'var(--text-muted)' }}>runs</span>
                          </span>
                          {executionHistory.length > 0 && (
                            <span style={{ 
                              fontSize: '11px', 
                              color: completedRunsCount === totalRuns ? '#10b981' : '#3b82f6', 
                              fontWeight: 'bold',
                              background: completedRunsCount === totalRuns ? 'rgba(16, 185, 129, 0.1)' : 'rgba(59, 130, 246, 0.1)',
                              padding: '2px 8px',
                              borderRadius: '12px'
                            }}>
                              {successRateStr} Success
                            </span>
                          )}
                        </div>
                        <span style={{ color: 'var(--text-secondary)', fontSize: '10px', marginTop: '4px' }}>
                          Last Run: {executionHistory.length > 0 && executionHistory[0].start_time ? new Date(executionHistory[0].start_time).toLocaleTimeString() : '--'}
                        </span>
                      </div>

                      {/* Card 3: Performance */}
                      <div style={{
                        background: 'rgba(15, 23, 42, 0.4)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        padding: '12px 16px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        gap: '4px'
                      }}>
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Performance</span>
                        <span style={{ color: 'var(--text-primary)', fontSize: '20px', fontWeight: 'bold' }}>
                          {averageDurationStr} <span style={{ fontSize: '11px', fontWeight: 'normal', color: 'var(--text-muted)' }}>avg. duration</span>
                        </span>
                        <span style={{ color: 'var(--text-secondary)', fontSize: '10px', marginTop: '4px' }}>
                          Calculated from {completedRunsWithDuration.length} completed run{completedRunsWithDuration.length === 1 ? '' : 's'}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })()}

            </div>
          </div>
        </div>
      )}
    </div>
  );
};
