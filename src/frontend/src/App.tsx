import React, { useState, useCallback, useRef, useEffect } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
} from 'reactflow';
import type { Node, Edge, Connection } from 'reactflow';
import 'reactflow/dist/style.css';

import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { Inspector } from './components/Inspector';
import { Simulator } from './components/Simulator';
import type { LogEntry, TabType } from './components/Simulator';
import { nodeTypes } from './components/CustomNodes';
import type { NodeType, RFNodeData, RFEdgeData, WorkflowMetadata } from './types';
import { getDefaultNodeData } from './utils/nodeDefaults';
import { compilerApi } from './services/compilerApi';
import { buildExportPayload } from './utils/exportWorkflow';
import { EXAMPLES } from './constants/examples';

const FlowBuilder: React.FC = () => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChangeInternal] = useNodesState<RFNodeData>([]);
  const [edges, setEdges, onEdgesChangeInternal] = useEdgesState<RFEdgeData>([]);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

  // Undo/Redo history stacks
  const [undoStack, setUndoStack] = useState<Array<{ nodes: Node<RFNodeData>[]; edges: Edge<RFEdgeData>[] }>>([]);
  const [redoStack, setRedoStack] = useState<Array<{ nodes: Node<RFNodeData>[]; edges: Edge<RFEdgeData>[] }>>([]);

  // Helper to push current state onto undo stack and clear redo
  const pushToUndo = () => {
    setUndoStack((prev) => [...prev, { nodes, edges }]);
    setRedoStack([]);
  };

  // Helper to generate unique IDs
  const getId = (type: NodeType) => `${type}-${Math.random().toString(36).substr(2, 9)}`;

  // Inspector States
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  // Simulator / Execution States
  const [logs, setLogs] = useState<LogEntry[]>([]);

  // Unified Workflow Execution States
  const [executionHistory, setExecutionHistory] = useState<any[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [nodeTraceStates, setNodeTraceStates] = useState<Record<string, any>>({});
  const [isTriggeringRun, setIsTriggeringRun] = useState(false);

  // Compilation state machine cache
  const [isCompiled, setIsCompiled] = useState<boolean>(false);
  const [compiledDsl, setCompiledDsl] = useState<any>(null);
  const [compiledHash, setCompiledHash] = useState<string>('');
  const [compiledAt, setCompiledAt] = useState<string>('');
  const [showBanner, setShowBanner] = useState<boolean>(false);
  const [isCompiling, setIsCompiling] = useState<boolean>(false);

  // Global Metadata
  const [metadata, setMetadata] = useState<WorkflowMetadata>({
    workflow_id: 'weather-assistant',
    workflow_type: 'weather-assistant-type',
    task_queue: 'default',
    version: '1.0.0',
    description: 'Checks the weather using a Weather Agent, routes based on rain condition, and sends alerts or summary reports.',
  });

  // Simulator Tabs and panel visibility state
  const [isSimulatorOpen, setIsSimulatorOpen] = useState<boolean>(true);
  const [simulatorTab, setSimulatorTab] = useState<TabType>('execution');

  const simulationTimeoutRef = useRef<number | null>(null);

  // Sync selection with Inspector
  const onSelectionChange = useCallback(({ nodes, edges }: any) => {
    if (nodes.length > 0) {
      setSelectedNodeId(nodes[0].id);
      setSelectedEdgeId(null);
    } else if (edges.length > 0) {
      setSelectedEdgeId(edges[0].id);
      setSelectedNodeId(null);
    } else {
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
    }
  }, []);

  const invalidateCompilation = () => {
    if (isCompiled) {
      setIsCompiled(false);
      setCompiledDsl(null);
      setCompiledHash('');
      setCompiledAt('');
      setShowBanner(false);
      addLog("Graph design modified. Cache invalidated. Please Validate & Compile again.", 'warning');
    }
  };

  const onNodesChange = (changes: any) => {
    pushToUndo();
    onNodesChangeInternal(changes);
    invalidateCompilation();
  };

  const onEdgesChange = (changes: any) => {
    pushToUndo();
    onEdgesChangeInternal(changes);
    invalidateCompilation();
  };

  // Update selected Node fields
  const onUpdateNode = useCallback((nodeId: string, updatedData: Partial<RFNodeData>) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          return {
            ...node,
            data: {
              ...node.data,
              ...updatedData,
            },
          };
        }
        return node;
      })
    );
    invalidateCompilation();
  }, [setNodes, isCompiled]);

  // Update selected Edge fields
  const onUpdateEdge = useCallback((edgeId: string, updatedData: Partial<RFEdgeData>) => {
    setEdges((eds) =>
      eds.map((edge) => {
        if (edge.id === edgeId) {
          // Sync edge label with branch or standard labels
          let label = updatedData.label || edge.label || '';
          if (updatedData.branch) {
            label = updatedData.branch;
          }
          return {
            ...edge,
            label,
            data: {
              ...edge.data,
              ...updatedData,
            },
          };
        }
        return edge;
      })
    );
    invalidateCompilation();
  }, [setEdges, isCompiled]);

  // Connect Nodes
  const onConnect = useCallback((connection: Connection) => {
    pushToUndo();
    const sourceNode = nodes.find((n) => n.id === connection.source);
    let edgeData: RFEdgeData = {};
    let label = '';

    if (sourceNode?.type === 'if') {
      if (connection.sourceHandle === 'branch1') {
        edgeData = { branch: 'branch1', label: 'branch1' };
        label = 'branch1';
      } else if (connection.sourceHandle === 'branch2') {
        edgeData = { branch: 'branch2', label: 'branch2' };
        label = 'branch2';
      }
    }

    setEdges((eds) =>
      addEdge(
        {
          ...connection,
          label,
          data: edgeData,
          animated: true,
        },
        eds
      )
    );
    invalidateCompilation();
  }, [nodes, setEdges, isCompiled]);

  // Drag and drop mechanics
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      pushToUndo();
      event.preventDefault();

      if (!reactFlowWrapper.current || !reactFlowInstance) return;

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const type = event.dataTransfer.getData('application/reactflow') as NodeType;

      if (!type) return;

      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const newNode: Node<RFNodeData> = {
        id: getId(type),
        type,
        position,
        data: getDefaultNodeData(type),
      };

      setNodes((nds) => nds.concat(newNode));
      invalidateCompilation();
    },
    [reactFlowInstance, setNodes, isCompiled]
  );

  // Click palette to add node directly to viewport center
  const onAddNodeDirectly = useCallback((type: NodeType) => {
    pushToUndo();
    if (!reactFlowInstance) return;

    const position = reactFlowInstance.project({
      x: window.innerWidth / 2 - 200,
      y: window.innerHeight / 2 - 200,
    });

    const newNode: Node<RFNodeData> = {
      id: getId(type),
      type,
      position,
      data: getDefaultNodeData(type),
    };

    setNodes((nds) => nds.concat(newNode));
    invalidateCompilation();
  }, [reactFlowInstance, setNodes, isCompiled]);

  // Reset flow builder
  const handleReset = useCallback(() => {
    pushToUndo();
    setNodes([]);
    setEdges([]);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setLogs([]);
    setIsCompiled(false);
    setCompiledDsl(null);
    setCompiledHash('');
    setCompiledAt('');
    setShowBanner(false);
    if (simulationTimeoutRef.current) {
      clearTimeout(simulationTimeoutRef.current);
    }
  }, [setNodes, setEdges]);

  // Load a preset template
  const handleLoadExample = useCallback((key: string) => {
    pushToUndo();
    handleReset();
    const example = EXAMPLES[key];
    if (example) {
      setNodes(JSON.parse(JSON.stringify(example.nodes)));
      setEdges(JSON.parse(JSON.stringify(example.edges)));
      setMetadata(JSON.parse(JSON.stringify(example.metadata)));
      setIsCompiled(false);
      setCompiledDsl(null);
      setCompiledHash('');
      setCompiledAt('');
      setShowBanner(false);
      setLogs([]);
      addLog(`Loaded example workflow: "${example.name}"`, 'info');
    }
  }, [setNodes, setEdges, handleReset]);

  // Undo operation
  const undo = () => {
    if (undoStack.length === 0) return;
    const previous = undoStack[undoStack.length - 1];
    setRedoStack((prev) => [...prev, { nodes, edges }]);
    setNodes(previous.nodes);
    setEdges(previous.edges);
    setUndoStack((prev) => prev.slice(0, -1));
    invalidateCompilation();
  };

  // Redo operation
  const redo = () => {
    if (redoStack.length === 0) return;
    const next = redoStack[redoStack.length - 1];
    setUndoStack((prev) => [...prev, { nodes, edges }]);
    setNodes(next.nodes);
    setEdges(next.edges);
    setRedoStack((prev) => prev.slice(0, -1));
    invalidateCompilation();
  };

  // Simulator Logging Helper
  const addLog = (message: string, type: LogEntry['type'] = 'text') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { timestamp, type, message }]);
  };



  const clearLogs = () => {
    setLogs([]);
  };

  // Temporal live execution functions
  const refreshHistory = useCallback(async () => {
    try {
      const history = await compilerApi.getHistory(metadata.workflow_id);
      setExecutionHistory(history.executions || []);
    } catch (err: any) {
      console.error("Failed to load execution history:", err);
    }
  }, [metadata.workflow_id]);

  const triggerTemporalRun = async (inputData: Record<string, any>) => {
    setIsTriggeringRun(true);
    try {
      addLog(`Triggering execution for workflow "${metadata.workflow_id}" (hash: ${compiledHash})...`, 'info');
      const res = await compilerApi.executeWorkflow(metadata.workflow_id, compiledHash, inputData);
      addLog(`Workflow triggered successfully! Run ID: ${res.run_id}`, 'success');
      
      setActiveRunId(res.run_id);
      setSimulatorTab('trace');
      await refreshHistory();
    } catch (err: any) {
      addLog(`Failed to execute: ${err.message}`, 'error');
      alert(`Execution failed: ${err.message}`);
    } finally {
      setIsTriggeringRun(false);
    }
  };

  const validateAndCompile = async () => {
    setIsCompiling(true);
    try {
      addLog("Starting workflow validation and DSL compilation...", 'info');
      const payload = buildExportPayload(nodes, edges);
      const compileRes = await compilerApi.compileWorkflow({
        nodes: payload.nodes,
        edges: payload.edges,
        workflow_id: metadata.workflow_id,
        workflow_type: metadata.workflow_type,
        task_queue: metadata.task_queue,
        version: metadata.version,
        description: metadata.description,
      });

      setIsCompiled(true);
      setCompiledDsl(compileRes.dsl);
      setCompiledHash(compileRes.content_hash);
      setCompiledAt(compileRes.generated_at || new Date().toISOString());
      setShowBanner(true);

      // Print success logs in console
      addLog("✓ Validation Passed", 'success');
      addLog("✓ DSL Generated", 'success');
      addLog("✓ Registered", 'success');
      addLog("✓ Runtime Loaded", 'success');
      addLog(`Compilation validated successfully (hash: ${compileRes.content_hash}).`, 'success');
    } catch (err: any) {
      addLog(`Compilation failed: ${err.message || err}`, 'error');
      alert(`Compilation failed: ${err.message || err}`);
    } finally {
      setIsCompiling(false);
    }
  };

  const handleUpdateMetadata = (updated: Partial<WorkflowMetadata>) => {
    setMetadata((prev) => ({
      ...prev,
      ...updated,
    }));
    invalidateCompilation();
  };

  const handleImportJson = (importedNodes: Node<RFNodeData>[], importedEdges: Edge<RFEdgeData>[], importedMetadata: any) => {
    pushToUndo();
    handleReset();
    setNodes(importedNodes);
    setEdges(importedEdges);
    setMetadata(importedMetadata);
    invalidateCompilation();
    addLog(`Imported workflow design from JSON file.`, 'info');
  };

  const handleExportJson = () => {
    const payload = {
      nodes,
      edges,
      metadata,
    };
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(payload, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${metadata.workflow_id}-design.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    addLog("Exported workflow design JSON file.", 'info');
  };

  const handleViewDslClick = () => {
    setIsSimulatorOpen(true);
    setSimulatorTab('dsl');
  };

  const handleDownloadDsl = () => {
    if (!compiledDsl) return;
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(compiledDsl, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${metadata.workflow_id}.dsl.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleCopyDsl = () => {
    if (!compiledDsl) return;
    navigator.clipboard.writeText(JSON.stringify(compiledDsl, null, 2))
      .then(() => alert("DSL copied to clipboard!"))
      .catch((err) => console.error("Failed to copy DSL:", err));
  };

  const loggedStepsRef = useRef<Record<string, string>>({});

  useEffect(() => {
    if (activeRunId) {
      setLogs([]);
      loggedStepsRef.current = {};
      setNodeTraceStates({});
    }
  }, [activeRunId]);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  const handleCancelRun = async (workflowId: string, runId: string) => {
    try {
      addLog(`Requesting cancellation for workflow ${workflowId} (run: ${runId})...`, 'info');
      await compilerApi.cancelWorkflow(workflowId, runId);
      addLog("Cancellation request submitted successfully.", 'success');
      await refreshHistory();
    } catch (err: any) {
      addLog(`Failed to cancel: ${err.message}`, 'error');
    }
  };

  const handleTerminateRun = async (workflowId: string, runId: string, reason: string) => {
    try {
      addLog(`Terminating workflow ${workflowId} (run: ${runId})...`, 'info');
      await compilerApi.terminateWorkflow(workflowId, runId, reason);
      addLog("Workflow terminated successfully.", 'success');
      await refreshHistory();
    } catch (err: any) {
      addLog(`Failed to terminate: ${err.message}`, 'error');
    }
  };

  useEffect(() => {
    if (!activeRunId) return;

    let intervalId: any;

    const activeRun = executionHistory.find(r => r.run_id === activeRunId);
    const activeWorkflowId = activeRun?.workflow_id || metadata.workflow_id;

    const pollTrace = async () => {
      try {
        const trace = await compilerApi.getTrace(activeWorkflowId, activeRunId);
        if (trace && trace.steps) {
          setNodeTraceStates(trace.steps);
          
          Object.keys(trace.steps).forEach((nodeId) => {
            const step = trace.steps[nodeId];
            const prev = loggedStepsRef.current[nodeId];
            if (step.status !== prev) {
              loggedStepsRef.current[nodeId] = step.status;
              const node = nodes.find((n) => n.id === nodeId);
              const label = node?.data?.label || nodeId;
              if (step.status === 'running') {
                addLog(`[Temporal: ${label}] Running...`, 'info');
              } else if (step.status === 'completed') {
                addLog(`[Temporal: ${label}] Completed successfully. ${step.output ? 'Output: ' + JSON.stringify(step.output) : ''}`, 'success');
              } else if (step.status === 'failed') {
                addLog(`[Temporal: ${label}] Failed: ${step.error || 'Activity failed'}`, 'error');
              } else if (step.status === 'skipped') {
                addLog(`[Temporal: ${label}] Skipped.`, 'text');
              }
            }
          });
        }
      } catch (err) {
        console.error("Trace polling error:", err);
      }
    };

    pollTrace();
    
    const isCompleted = activeRun && (activeRun.status === 'COMPLETED' || activeRun.status === 'completed' || activeRun.status === 'FAILED' || activeRun.status === 'failed' || activeRun.status === 'CANCELED' || activeRun.status === 'canceled' || activeRun.status === 'TERMINATED' || activeRun.status === 'terminated');

    if (!isCompleted) {
      intervalId = setInterval(async () => {
        await pollTrace();
        await refreshHistory();
      }, 2000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [activeRunId, executionHistory, nodes, refreshHistory, metadata.workflow_id]);

  // Find selected elements
  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || null;
  const selectedEdge = edges.find((e) => e.id === selectedEdgeId) || null;

  // Add styles for simulating states inside the nodes list dynamically
  const styledNodes = nodes.map((node) => {
    let className = '';
    
    if (nodeTraceStates[node.id]) {
      const trace = nodeTraceStates[node.id];
      if (trace.status === 'completed') {
        className = 'node-completed';
      } else if (trace.status === 'running') {
        className = 'node-running';
      } else if (trace.status === 'failed') {
        className = 'node-failed';
      } else if (trace.status === 'skipped') {
        className = 'node-skipped';
      }
    }
    
    return {
      ...node,
      className: `${node.className || ''} ${className}`.trim(),
    };
  });

  return (
    <div className="app-container">
      <Header
        onReset={handleReset}
        onLoadExample={handleLoadExample}
        onUndo={undo}
        onRedo={redo}
        canUndo={undoStack.length > 0}
        canRedo={redoStack.length > 0}
        isCompiled={isCompiled}
        onValidateAndCompile={validateAndCompile}
        isCompiling={isCompiling}
        onViewDslClick={handleViewDslClick}
        onDownloadDsl={handleDownloadDsl}
        onCopyDsl={handleCopyDsl}
        onExportJson={handleExportJson}
        onImportJson={handleImportJson}
      />
      <div className="main-content">
        <Sidebar
          onAddNode={onAddNodeDirectly}
        />

        <div className="canvas-container" ref={reactFlowWrapper}>
          {showBanner && isCompiled && (
            <div style={{
              position: 'absolute',
              top: '20px',
              right: '20px',
              background: 'rgba(15, 23, 42, 0.95)',
              border: '1px solid #10b981',
              borderRadius: '8px',
              padding: '16px',
              zIndex: 100,
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
              minWidth: '240px',
              backdropFilter: 'blur(8px)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <span style={{ color: '#10b981', fontWeight: 'bold', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span>✓ Compiled Successfully</span>
                </span>
                <button 
                  onClick={() => setShowBanner(false)}
                  style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '16px', padding: 0 }}
                >
                  &times;
                </button>
              </div>
              <div style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '6px', color: 'var(--text-secondary)' }}>
                <div style={{ fontFamily: 'monospace', fontSize: '10px' }}>
                  Hash: {compiledHash.slice(0, 10)}...
                </div>
                <div>
                  Generated: {compiledAt ? (() => {
                    const d = new Date(compiledAt);
                    const pad = (n: number) => n.toString().padStart(2, '0');
                    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
                  })() : ''}
                </div>
                <button
                  onClick={() => {
                    setSimulatorTab('dsl');
                    setIsSimulatorOpen(true);
                    setShowBanner(false);
                  }}
                  style={{
                    marginTop: '6px',
                    background: 'rgba(16, 185, 129, 0.1)',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    color: '#10b981',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontWeight: '600',
                    transition: 'background 0.2s',
                    textAlign: 'center'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(16, 185, 129, 0.2)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(16, 185, 129, 0.1)'}
                >
                  Open DSL
                </button>
              </div>
            </div>
          )}

          <ReactFlow
            nodes={styledNodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            onSelectionChange={onSelectionChange}
            fitView
          >
            <Background color="#334155" gap={16} size={1} />
            <Controls />
            <MiniMap
              nodeColor={(node) => {
                switch (node.type) {
                  case 'start': return 'var(--color-start)';
                  case 'end': return 'var(--color-end)';
                  case 'input': return 'var(--color-input)';
                  case 'if': return 'var(--color-if)';
                  case 'action': return 'var(--color-action)';
                  case 'agent': return 'var(--color-agent)';
                  case 'output': return 'var(--color-output)';
                  default: return '#64748b';
                }
              }}
              maskColor="rgba(8, 12, 20, 0.7)"
            />
          </ReactFlow>
        </div>

        <Inspector
          selectedNode={selectedNode}
          selectedEdge={selectedEdge}
          onUpdateNode={onUpdateNode}
          onUpdateEdge={onUpdateEdge}
          nodeTraceStates={nodeTraceStates}
          metadata={metadata}
          onChangeMetadata={handleUpdateMetadata}
        />

        <Simulator
          logs={logs}
          onClearLogs={clearLogs}
          isCompiled={isCompiled}
          compiledDsl={compiledDsl}
          compiledHash={compiledHash}
          compiledAt={compiledAt}
          metadata={metadata}
          executionHistory={executionHistory}
          activeRunId={activeRunId}
          setActiveRunId={setActiveRunId}
          onTriggerTemporalRun={triggerTemporalRun}
          onRefreshHistory={refreshHistory}
          isTriggeringRun={isTriggeringRun}
          onCancelRun={handleCancelRun}
          onTerminateRun={handleTerminateRun}
          nodeTraceStates={nodeTraceStates}
          activeTab={simulatorTab}
          setActiveTab={setSimulatorTab}
          isOpen={isSimulatorOpen}
          setIsOpen={setIsSimulatorOpen}
        />
      </div>
    </div>
  );
};

export default function App() {
  return (
    <ReactFlowProvider>
      <FlowBuilder />
    </ReactFlowProvider>
  );
}

