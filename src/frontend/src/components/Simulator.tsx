import React, { useRef, useEffect } from 'react';
import { Play, Square, Trash2, ChevronDown, ChevronUp, RefreshCw, Zap, History } from 'lucide-react';

export interface LogEntry {
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'text';
  message: string;
}

interface SimulatorProps {
  // Local simulation
  logs: LogEntry[];
  status: 'idle' | 'running' | 'completed' | 'failed';
  onStartSimulation: () => void;
  onStopSimulation: () => void;
  onClearLogs: () => void;

  // Temporal runner
  mode: 'simulation' | 'temporal';
  setMode: (mode: 'simulation' | 'temporal') => void;
  executionHistory: any[];
  activeRunId: string | null;
  setActiveRunId: (runId: string | null) => void;
  onTriggerTemporalRun: () => void;
  onRefreshHistory: () => void;
  isTriggeringRun: boolean;
  onCancelRun?: (workflowId: string, runId: string) => void;
  onTerminateRun?: (workflowId: string, runId: string, reason: string) => void;
}

export const Simulator: React.FC<SimulatorProps> = ({
  logs,
  status,
  onStartSimulation,
  onStopSimulation,
  onClearLogs,
  mode,
  setMode,
  executionHistory,
  activeRunId,
  setActiveRunId,
  onTriggerTemporalRun,
  onRefreshHistory,
  isTriggeringRun,
  onCancelRun,
  onTerminateRun,
}) => {
  const consoleEndRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = React.useState(true);

  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const activeRun = executionHistory.find((r) => r.run_id === activeRunId);

  return (
    <div 
      className="simulator-panel" 
      style={{ height: isOpen ? '280px' : '40px' }}
    >
      <div className="simulator-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div className={`simulator-title ${mode === 'temporal' ? 'completed' : status === 'running' ? 'running' : ''}`}>
            <div className="dot"></div>
            <span>{mode === 'simulation' ? `Simulation Runner (${status})` : 'Temporal Live Execution'}</span>
          </div>

          {/* Mode switcher tabs */}
          <div className="modal-tabs" style={{ marginBottom: 0, padding: '2px', background: 'rgba(15, 23, 42, 0.4)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            <button
              className={`modal-tab-btn ${mode === 'simulation' ? 'active' : ''}`}
              style={{ fontSize: '11px', padding: '4px 10px', minWidth: 'auto', borderRadius: '4px' }}
              onClick={() => setMode('simulation')}
            >
              Local Sim
            </button>
            <button
              className={`modal-tab-btn ${mode === 'temporal' ? 'active' : ''}`}
              style={{ fontSize: '11px', padding: '4px 10px', minWidth: 'auto', borderRadius: '4px' }}
              onClick={() => setMode('temporal')}
            >
              Temporal Runner
            </button>
          </div>
        </div>

        <div className="simulator-controls">
          {mode === 'simulation' ? (
            status === 'running' ? (
              <button className="btn btn-outline" style={{ padding: '4px 10px', fontSize: '11px', borderColor: '#f87171', color: '#f87171' }} onClick={onStopSimulation}>
                <Square size={12} /> Stop
              </button>
            ) : (
              <button className="btn btn-success" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={onStartSimulation}>
                <Play size={12} /> Run Simulation
              </button>
            )
          ) : (
            <>
              <button 
                className="btn btn-primary" 
                style={{ padding: '4px 10px', fontSize: '11px', background: 'var(--accent)' }} 
                onClick={onTriggerTemporalRun}
                disabled={isTriggeringRun}
              >
                <Zap size={12} /> {isTriggeringRun ? 'Starting...' : 'Trigger Temporal Run'}
              </button>
              <button className="btn" style={{ padding: '4px 10px', fontSize: '11px', background: 'transparent' }} onClick={onRefreshHistory} title="Refresh History">
                <RefreshCw size={12} />
              </button>
            </>
          )}
          
          <button className="btn" style={{ padding: '4px 10px', fontSize: '11px', background: 'transparent' }} onClick={onClearLogs} title="Clear Logs">
            <Trash2 size={12} />
          </button>
          
          <button className="close-btn" onClick={() => setIsOpen(!isOpen)}>
            {isOpen ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </button>
        </div>
      </div>

      {isOpen && (
        <div style={{ display: 'flex', height: '240px', overflow: 'hidden' }}>
          {/* Temporal Execution History Sidebar */}
          {mode === 'temporal' && (
            <div style={{
              width: '240px',
              borderRight: '1px solid var(--border-color)',
              background: 'rgba(15, 23, 42, 0.2)',
              display: 'flex',
              flexDirection: 'column',
              height: '100%'
            }}>
              <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-color)', fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 'bold' }}>
                <History size={12} />
                <span>Execution History</span>
              </div>
              <div style={{ overflowY: 'auto', flex: 1, padding: '4px' }}>
                {executionHistory.length === 0 ? (
                  <div style={{ padding: '16px', fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center' }}>
                    No executions found. Trigger a run above.
                  </div>
                ) : (
                  executionHistory.map((run) => {
                    const isSelected = run.run_id === activeRunId;
                    const statusColor = 
                      run.status === 'COMPLETED' || run.status === 'completed' ? '#10b981' :
                      run.status === 'RUNNING' || run.status === 'running' ? '#3b82f6' : '#ef4444';
                    
                    return (
                      <div
                        key={run.run_id}
                        onClick={() => setActiveRunId(run.run_id)}
                        style={{
                          padding: '8px',
                          margin: '2px 0',
                          borderRadius: '4px',
                          background: isSelected ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                          border: isSelected ? '1px solid var(--accent)' : '1px solid transparent',
                          cursor: 'pointer',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '2px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '11px', fontWeight: '500', color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px' }} title={run.workflow_id}>
                            {run.workflow_id}
                          </span>
                          <span style={{ 
                            fontSize: '9px', 
                            color: statusColor, 
                            fontWeight: 'bold',
                            border: `1px solid ${statusColor}`,
                            borderRadius: '3px',
                            padding: '1px 4px',
                            background: `${statusColor}15`
                          }}>
                            {run.status.toLowerCase()}
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
          )}

          {/* Console Output Area */}
          <div className="simulator-console" style={{ flex: 1, height: '100%', overflowY: 'auto' }}>
            {mode === 'simulation' ? (
              logs.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px' }}>
                  Click "Run Simulation" to trace the execution of your React Flow graph step-by-step.
                </div>
              ) : (
                logs.map((log, index) => (
                  <div key={index} className={`console-line ${log.type}`}>
                    <span className="console-line-timestamp">[{log.timestamp}]</span>
                    {log.message}
                  </div>
                ))
              )
            ) : (
              // Temporal execution logs or status
              !activeRunId ? (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px' }}>
                  Select an execution from the history list to replay and trace its active nodes on the canvas.
                </div>
              ) : (
                <>
                  <div style={{ padding: '8px 12px', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)', marginBottom: '8px' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                      Viewing Run: <span style={{ color: 'var(--text-primary)', fontFamily: 'monospace' }}>{activeRunId}</span>
                    </div>
                    {activeRun && (activeRun.status === 'RUNNING' || activeRun.status === 'running') && (
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button
                          onClick={() => onCancelRun && onCancelRun(activeRun.workflow_id, activeRun.run_id)}
                          style={{
                            padding: '2px 8px',
                            fontSize: '10px',
                            border: '1px solid #fbbf24',
                            borderRadius: '3px',
                            color: '#fbbf24',
                            background: 'transparent',
                            cursor: 'pointer'
                          }}
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => {
                            const reason = prompt("Enter termination reason:", "Terminated by user");
                            if (reason !== null && onTerminateRun) {
                              onTerminateRun(activeRun.workflow_id, activeRun.run_id, reason);
                            }
                          }}
                          style={{
                            padding: '2px 8px',
                            fontSize: '10px',
                            border: '1px solid #f87171',
                            borderRadius: '3px',
                            color: '#f87171',
                            background: 'transparent',
                            cursor: 'pointer'
                          }}
                        >
                          Terminate
                        </button>
                        <span style={{ fontSize: '10px', color: '#3b82f6', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <RefreshCw size={10} className="spin" />
                          Polling...
                        </span>
                      </div>
                    )}
                  </div>
                  {logs.length === 0 ? (
                    <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px', fontSize: '12px' }}>
                      Retrieving step details for this run...
                    </div>
                  ) : (
                    logs.map((log, index) => (
                      <div key={index} className={`console-line ${log.type}`}>
                        <span className="console-line-timestamp">[{log.timestamp}]</span>
                        {log.message}
                      </div>
                    ))
                  )}
                </>
              )
            )}
            <div ref={consoleEndRef} />
          </div>
        </div>
      )}
    </div>
  );
};
