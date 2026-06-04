import React, { useRef, useEffect } from 'react';
import { Play, Square, Trash2, ChevronDown, ChevronUp } from 'lucide-react';

export interface LogEntry {
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'text';
  message: string;
}

interface SimulatorProps {
  logs: LogEntry[];
  status: 'idle' | 'running' | 'completed' | 'failed';
  onStartSimulation: () => void;
  onStopSimulation: () => void;
  onClearLogs: () => void;
}

export const Simulator: React.FC<SimulatorProps> = ({
  logs,
  status,
  onStartSimulation,
  onStopSimulation,
  onClearLogs,
}) => {
  const consoleEndRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = React.useState(true);

  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  return (
    <div 
      className="simulator-panel" 
      style={{ height: isOpen ? '220px' : '40px' }}
    >
      <div className="simulator-header">
        <div className={`simulator-title ${status === 'running' ? 'running' : status === 'completed' ? 'completed' : ''}`}>
          <div className="dot"></div>
          <span>Simulation Runner ({status})</span>
        </div>
        <div className="simulator-controls">
          {status === 'running' ? (
            <button className="btn btn-outline" style={{ padding: '4px 10px', fontSize: '11px', borderColor: '#f87171', color: '#f87171' }} onClick={onStopSimulation}>
              <Square size={12} /> Stop
            </button>
          ) : (
            <button className="btn btn-success" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={onStartSimulation}>
              <Play size={12} /> Run Simulation
            </button>
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
        <div className="simulator-console">
          {logs.length === 0 ? (
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
          )}
          <div ref={consoleEndRef} />
        </div>
      )}
    </div>
  );
};
