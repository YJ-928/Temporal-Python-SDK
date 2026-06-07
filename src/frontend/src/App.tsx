import React, { useState, useCallback, useRef, useEffect } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
} from 'reactflow';
import type { Node, Edge, Connection, NodeChange, EdgeChange, ReactFlowInstance } from 'reactflow';
import 'reactflow/dist/style.css';

import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { Inspector } from './components/Inspector';
import { Simulator } from './components/Simulator';
import type { LogEntry, TabType } from './components/Simulator';
import { nodeTypes } from './constants/nodeTypes';
import type { NodeType, RFNodeData, RFEdgeData, WorkflowMetadata, ExecutionRun, NodeTraceState } from './types';
import { getDefaultNodeData } from './utils/nodeDefaults';
import { compilerApi } from './services/compilerApi';
import type { TraceResponse } from './services/compilerApi';
import { buildExportPayload } from './utils/exportWorkflow';
import { EXAMPLES } from './constants/examples';
import { notify } from './utils/notify';
import { getFriendlyMessage } from './utils/errorHandler';

const BLANK_METADATA: WorkflowMetadata = {
  workflow_id: 'workflow-design',
  workflow_type: 'workflow-builder',
  task_queue: 'workflow-builder',
  version: '1.0.0',
  description: '',
};

interface GraphError {
  message: string;
  nodeIds?: string[];
}

function validateGraphTopology(nodes: Node<RFNodeData>[], edges: Edge<RFEdgeData>[]): GraphError[] {
  const errors: GraphError[] = [];

  if (nodes.length === 0) {
    errors.push({ message: 'Canvas is empty. Add nodes to build a workflow.' });
    return errors;
  }

  const startNodes = nodes.filter(n => n.type === 'start');
  if (startNodes.length === 0) {
    errors.push({ message: 'Workflow must have a START node.' });
  } else if (startNodes.length > 1) {
    errors.push({
      message: `Workflow has ${startNodes.length} START nodes — only one is allowed.`,
      nodeIds: startNodes.map(n => n.id),
    });
  }

  if (nodes.filter(n => n.type === 'end').length === 0) {
    errors.push({ message: 'Workflow must have at least one END node.' });
  }

  // BFS reachability from the single START — only meaningful when START is unambiguous
  if (startNodes.length === 1) {
    const adj = new Map<string, string[]>();
    for (const n of nodes) adj.set(n.id, []);
    for (const e of edges) adj.get(e.source)?.push(e.target);

    const visited = new Set<string>();
    const queue = [startNodes[0].id];
    while (queue.length) {
      const id = queue.shift()!;
      if (visited.has(id)) continue;
      visited.add(id);
      for (const nb of (adj.get(id) ?? [])) queue.push(nb);
    }

    const unreachable = nodes.filter(n => !visited.has(n.id));
    if (unreachable.length > 0) {
      const labels = unreachable.map(n => n.data.label || n.type || n.id).join(', ');
      errors.push({
        message: `Disconnected node${unreachable.length > 1 ? 's' : ''}: ${labels}. Every node must be reachable from START.`,
        nodeIds: unreachable.map(n => n.id),
      });
    }
  }

  return errors;
}

function getDefaultInputJson(workflowId: string): string {
  if (workflowId === 'weather-assistant') return '{\n  "city": "kolkata"\n}';
  if (workflowId === 'email-validation-sender') return '{\n  "email": "test@domain.com",\n  "subject": "Greetings",\n  "message": "Hello from Workflow Builder!"\n}';
  if (workflowId === 'account-routing') return '{\n  "account_id": "ACC-789"\n}';
  if (workflowId === 'single-email-validator') return '{\n  "email": "verify-me@test.com"\n}';
  return '{}';
}

// jq identifier: must start with a letter/underscore, then only word chars (\w = [a-zA-Z0-9_])
const FIELD_NAME_RE = /^[a-zA-Z_]\w*$/;

function validateFieldName(label: string, nodeKind: string, field: string): string | null {
  if (!field?.trim()) return `${nodeKind} node "${label}" has a blank field name.`;
  if (!FIELD_NAME_RE.test(field.trim()))
    return `${nodeKind} node "${label}": field name "${field}" must start with a letter and contain only letters, numbers, and underscores (no spaces or special characters).`;
  return null;
}

function validateInputNode(d: RFNodeData): string | null {
  if (!d.inputFields || d.inputFields.length === 0)
    return `INPUT node "${d.label}" has no fields defined.`;
  for (const f of d.inputFields) {
    const err = validateFieldName(d.label, 'INPUT', f.field);
    if (err) return err;
  }
  return null;
}

function validateActionNode(d: RFNodeData): string | null {
  if (!d.actionOperation?.trim())
    return `ACTION node "${d.label}" is missing an operation. Select one from the dropdown.`;
  if (!d.actionOutput?.trim())
    return `ACTION node "${d.label}" is missing an output field name.`;
  return null;
}

function validateAgentNode(d: RFNodeData): string | null {
  if (!d.selectedAgentId?.trim())
    return `AGENT node "${d.label}" has no agent selected.`;
  if (!d.agentOutput?.trim())
    return `AGENT node "${d.label}" is missing an output field name.`;
  return null;
}

function validateOutputNode(d: RFNodeData): string | null {
  if (!d.outputFields || d.outputFields.length === 0)
    return `OUTPUT node "${d.label}" has no fields defined.`;
  for (const f of d.outputFields) {
    const err = validateFieldName(d.label, 'OUTPUT', f.field);
    if (err) return err;
  }
  return null;
}

function validateNodeConfig(node: Node<RFNodeData>): string | null {
  const { data: d, type } = node;
  if (type === 'input') return validateInputNode(d);
  if (type === 'action') return validateActionNode(d);
  if (type === 'agent') return validateAgentNode(d);
  if (type === 'output') return validateOutputNode(d);
  return null;
}

const FlowBuilder: React.FC = () => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChangeInternal] = useNodesState<RFNodeData>([]);
  const [edges, setEdges, onEdgesChangeInternal] = useEdgesState<RFEdgeData>([]);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

  // Undo/Redo history stacks
  const [undoStack, setUndoStack] = useState<Array<{ nodes: Node<RFNodeData>[]; edges: Edge<RFEdgeData>[] }>>([]);
  const [redoStack, setRedoStack] = useState<Array<{ nodes: Node<RFNodeData>[]; edges: Edge<RFEdgeData>[] }>>([]);

  // Refs track latest nodes/edges so pushToUndo stays stable (never recreated on every node/edge change)
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);
  useEffect(() => { nodesRef.current = nodes; }, [nodes]);
  useEffect(() => { edgesRef.current = edges; }, [edges]);

  // Helper to push current state onto undo stack and clear redo
  const pushToUndo = useCallback(() => {
    setUndoStack((prev) => [...prev, { nodes: nodesRef.current, edges: edgesRef.current }]);
    setRedoStack([]);
  }, []);

  // Helper to generate unique IDs
  const getId = (type: NodeType) => `${type}-${Math.random().toString(36).slice(2, 11)}`;

  // Inspector States
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  // Simulator / Execution States
  const [logs, setLogs] = useState<LogEntry[]>([]);

  const addLog = useCallback((message: string, type: LogEntry['type'] = 'text') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { timestamp, type, message }]);
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  // Unified Workflow Execution States
  const [executionHistory, setExecutionHistory] = useState<ExecutionRun[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeRunStatus, setActiveRunStatus] = useState<string>('');
  const [nodeTraceStates, setNodeTraceStates] = useState<Record<string, NodeTraceState>>({});
  const [isTriggeringRun, setIsTriggeringRun] = useState(false);

  // Ref kept in sync with executionHistory so the polling effect can read the
  // Temporal workflow ID (rf-xxx-xxxx) without listing executionHistory in its deps.
  const executionHistoryRef = useRef<ExecutionRun[]>([]);
  useEffect(() => { executionHistoryRef.current = executionHistory; }, [executionHistory]);

  // Compilation state machine cache
  const [isCompiled, setIsCompiled] = useState<boolean>(false);
  const [compiledDsl, setCompiledDsl] = useState<Record<string, unknown> | null>(null);
  const [compiledHash, setCompiledHash] = useState<string>('');
  const [compiledAt, setCompiledAt] = useState<string>('');
  const [showBanner, setShowBanner] = useState<boolean>(false);
  const [isCompiling, setIsCompiling] = useState<boolean>(false);

  // Global Metadata
  const [metadata, setMetadata] = useState<WorkflowMetadata>({ ...BLANK_METADATA });

  // Invalid node IDs for pre-compile highlighting
  const [invalidNodeIds, setInvalidNodeIds] = useState<Set<string>>(new Set());

  // Simulator Tabs and panel visibility state (starts in peek status by default)
  const [isSimulatorOpen, setIsSimulatorOpen] = useState<boolean>(false);
  const [simulatorTab, setSimulatorTab] = useState<TabType>('execution');
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [inputJson, setInputJson] = useState<string>('{}');
  const [panelHeight, setPanelHeight] = useState<number>(() => {
    return Number.parseInt(localStorage.getItem('workflow-runtime-height') ?? '300', 10);
  });

  const toggleSettings = () => {
    setIsSettingsOpen(!isSettingsOpen);
  };

  const simulationTimeoutRef = useRef<number | null>(null);

  // Sync selection with Inspector
  const onSelectionChange = useCallback(({ nodes: selNodes, edges: selEdges }: { nodes: Node<RFNodeData>[]; edges: Edge<RFEdgeData>[] }) => {
    if (selNodes.length > 0) {
      setSelectedNodeId(selNodes[0].id);
      setSelectedEdgeId(null);
    } else if (selEdges.length > 0) {
      setSelectedEdgeId(selEdges[0].id);
      setSelectedNodeId(null);
    } else {
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
    }
  }, []);

  const invalidateCompilation = useCallback(() => {
    setInvalidNodeIds(new Set());
    if (isCompiled) {
      setIsCompiled(false);
      setCompiledDsl(null);
      setCompiledHash('');
      setCompiledAt('');
      setShowBanner(false);
      addLog("Graph design modified. Cache invalidated. Please Validate & Compile again.", 'warning');
    }
  }, [isCompiled, addLog]);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    pushToUndo();
    onNodesChangeInternal(changes);
    invalidateCompilation();
  }, [pushToUndo, onNodesChangeInternal, invalidateCompilation]);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    pushToUndo();
    onEdgesChangeInternal(changes);
    invalidateCompilation();
  }, [pushToUndo, onEdgesChangeInternal, invalidateCompilation]);

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
  }, [setNodes, invalidateCompilation]);

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
  }, [setEdges, invalidateCompilation]);

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
  }, [nodes, setEdges, invalidateCompilation]);

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
    [reactFlowInstance, setNodes, invalidateCompilation]
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
  }, [reactFlowInstance, setNodes, invalidateCompilation]);

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
    setMetadata({ ...BLANK_METADATA });
    setInputJson('{}');
    setInvalidNodeIds(new Set());
    // Clear all run state — prevents stale activeRunId from re-triggering
    // the polling effect when nodes/metadata change during reset or example load
    setActiveRunId(null);
    setActiveRunStatus('');
    setExecutionHistory([]);
    setNodeTraceStates({});
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
      setNodes(structuredClone(example.nodes));
      setEdges(structuredClone(example.edges));
      const clonedMeta = structuredClone(example.metadata);
      setMetadata(clonedMeta);
      setInputJson(getDefaultInputJson(clonedMeta.workflow_id));
      setIsCompiled(false);
      setCompiledDsl(null);
      setCompiledHash('');
      setCompiledAt('');
      setShowBanner(false);
      setLogs([]);
      addLog(`Loaded example workflow: "${example.name}"`, 'info');
      
      // Auto fit view after nodes render
      setTimeout(() => {
        reactFlowInstance?.fitView({ duration: 400 });
      }, 100);
    }
  }, [setNodes, setEdges, handleReset, reactFlowInstance, addLog]);

  // Undo operation
  const undo = () => {
    if (undoStack.length === 0) return;
    const previous = undoStack.at(-1)!;
    setRedoStack((prev) => [...prev, { nodes, edges }]);
    setNodes(previous.nodes);
    setEdges(previous.edges);
    setUndoStack((prev) => prev.slice(0, -1));
    invalidateCompilation();
  };

  // Redo operation
  const redo = () => {
    if (redoStack.length === 0) return;
    const next = redoStack.at(-1)!;
    setUndoStack((prev) => [...prev, { nodes, edges }]);
    setNodes(next.nodes);
    setEdges(next.edges);
    setRedoStack((prev) => prev.slice(0, -1));
    invalidateCompilation();
  };

  // Temporal live execution functions
  const refreshHistory = useCallback(async () => {
    try {
      const history = await compilerApi.getHistory(metadata.workflow_id);
      setExecutionHistory(history.executions ?? []);
    } catch (err) {
      console.error("Failed to load execution history:", err);
      notify.warn('Could not refresh execution history.');
    }
  }, [metadata.workflow_id]);

  const triggerTemporalRun = async (inputData: Record<string, unknown>) => {
    setIsTriggeringRun(true);
    try {
      addLog(`Triggering execution for workflow "${metadata.workflow_id}" (hash: ${compiledHash})...`, 'info');
      const res = await compilerApi.executeWorkflow(metadata.workflow_id, compiledHash, inputData);
      addLog(`Workflow triggered successfully! Run ID: ${res.run_id}`, 'success');
      notify.success('Workflow execution started.');

      // Optimistically add the run with its Temporal workflow ID before setting activeRunId
      // so executionHistoryRef already holds the correct Temporal ID when the polling effect starts
      setExecutionHistory(prev => [{
        workflow_id: res.workflow_id,
        run_id: res.run_id,
        status: 'RUNNING',
        start_time: new Date().toISOString(),
        close_time: null,
        workflow_type: '',
      }, ...prev]);

      setActiveRunId(res.run_id);
      setActiveRunStatus('RUNNING');
      setSimulatorTab('trace');
      await refreshHistory();
    } catch (err) {
      const error = err as Error & { statusCode?: number };
      addLog(`Failed to execute: ${error.message}`, 'error');
      notify.error(getFriendlyMessage(error, error.statusCode));
    } finally {
      setIsTriggeringRun(false);
    }
  };

  const handleHeaderExecute = () => {
    setIsSimulatorOpen(true);
    setSimulatorTab('trace');
    const minHeight = Math.round(window.innerHeight * 0.55);
    if (panelHeight < minHeight) {
      setPanelHeight(minHeight);
      localStorage.setItem('workflow-runtime-height', minHeight.toString());
    }
    try {
      triggerTemporalRun(JSON.parse(inputJson) as Record<string, unknown>);
    } catch (e) {
      notify.error(`Invalid JSON format: ${(e as Error).message}`);
    }
  };

  const validateAndCompile = async () => {
    // Graph topology checks (no API call for structural errors)
    const graphErrors = validateGraphTopology(nodes, edges);

    // Node configuration checks
    const nodeErrors = nodes
      .map(n => ({ id: n.id, message: validateNodeConfig(n) }))
      .filter((e): e is { id: string; message: string } => e.message !== null);

    if (graphErrors.length > 0 || nodeErrors.length > 0) {
      const highlightIds = new Set([
        ...graphErrors.flatMap(e => e.nodeIds ?? []),
        ...nodeErrors.map(e => e.id),
      ]);
      setInvalidNodeIds(highlightIds);
      graphErrors.forEach(e => addLog(e.message, 'error'));
      nodeErrors.forEach(e => addLog(e.message, 'error'));
      const total = graphErrors.length + nodeErrors.length;
      const firstMessage = graphErrors[0]?.message ?? nodeErrors[0]?.message;
      notify.error(
        total === 1
          ? firstMessage
          : `${total} issues found. See Compilation Log for details.`
      );
      return;
    }
    setInvalidNodeIds(new Set());

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
      setCompiledAt(compileRes.generated_at ?? new Date().toISOString());
      setShowBanner(true);

      addLog("✓ Validation Passed", 'success');
      addLog("✓ DSL Generated", 'success');
      addLog("✓ Registered", 'success');
      addLog("✓ Runtime Loaded", 'success');
      addLog(`Compilation validated successfully (hash: ${compileRes.content_hash}).`, 'success');
    } catch (err) {
      const error = err as Error & { statusCode?: number };
      addLog(`Compilation failed: ${error.message ?? String(error)}`, 'error');
      notify.error(getFriendlyMessage(error, error.statusCode));
    } finally {
      setIsCompiling(false);
    }
  };

  const handleUpdateMetadata = (updated: Partial<WorkflowMetadata>) => {
    setMetadata((prev) => ({
      ...prev,
      ...updated,
    }));
    if (updated.workflow_id !== undefined) {
      setInputJson(getDefaultInputJson(updated.workflow_id));
    }
    invalidateCompilation();
  };

  const handleImportJson = (importedNodes: Node<RFNodeData>[], importedEdges: Edge<RFEdgeData>[], importedMetadata: WorkflowMetadata) => {
    pushToUndo();
    handleReset();
    setNodes(importedNodes);
    setEdges(importedEdges);
    setMetadata(importedMetadata);
    setInputJson(getDefaultInputJson(importedMetadata.workflow_id));
    invalidateCompilation();
    addLog(`Imported workflow design from JSON file.`, 'info');
    
    // Auto fit view after nodes render
    setTimeout(() => {
      reactFlowInstance?.fitView({ duration: 400 });
    }, 100);
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
      .then(() => notify.success('DSL copied to clipboard.'))
      .catch(() => notify.error('Failed to copy DSL to clipboard.'));
  };

  const loggedStepsRef = useRef<Record<string, string>>({});

  useEffect(() => {
    if (activeRunId) {
      setLogs([]);
      loggedStepsRef.current = {};
      setNodeTraceStates({});
      const run = executionHistory.find(r => r.run_id === activeRunId);
      setActiveRunStatus(run?.status || 'RUNNING');
    } else {
      setActiveRunStatus('');
    }
  }, [activeRunId, executionHistory]);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  const handleCancelRun = async (workflowId: string, runId: string) => {
    try {
      addLog(`Requesting cancellation for workflow ${workflowId} (run: ${runId})...`, 'info');
      await compilerApi.cancelWorkflow(workflowId, runId);
      addLog("Cancellation request submitted successfully.", 'success');
      notify.info('Cancellation request submitted.');
      await refreshHistory();
    } catch (err) {
      const error = err as Error & { statusCode?: number };
      addLog(`Failed to cancel: ${error.message}`, 'error');
      notify.error(getFriendlyMessage(error, error.statusCode));
    }
  };

  const handleTerminateRun = async (workflowId: string, runId: string, reason: string) => {
    try {
      addLog(`Terminating workflow ${workflowId} (run: ${runId})...`, 'info');
      await compilerApi.terminateWorkflow(workflowId, runId, reason);
      addLog("Workflow terminated successfully.", 'success');
      notify.info('Workflow terminated.');
      await refreshHistory();
    } catch (err) {
      const error = err as Error & { statusCode?: number };
      addLog(`Failed to terminate: ${error.message}`, 'error');
      notify.error(getFriendlyMessage(error, error.statusCode));
    }
  };

  useEffect(() => {
    if (!activeRunId) return;

    const TERMINAL = new Set([
      'COMPLETED', 'FAILED', 'CANCELED', 'TERMINATED', 'TIMED_OUT',
      'completed', 'failed', 'canceled', 'terminated', 'timed_out',
    ]);

    if (TERMINAL.has(activeRunStatus)) return;

    let intervalId: ReturnType<typeof setInterval> | undefined;
    let warnShown = false;
    let polling = false;

    const logStepChange = (nodeId: string, step: NodeTraceState) => {
      const prev = loggedStepsRef.current[nodeId];
      if (step.status === prev) return;
      loggedStepsRef.current[nodeId] = step.status;
      const label = nodes.find((n) => n.id === nodeId)?.data?.label || nodeId;
      if (step.status === 'running') addLog(`[Temporal: ${label}] Running...`, 'info');
      else if (step.status === 'completed') addLog(`[Temporal: ${label}] Completed. ${step.output ? 'Output: ' + JSON.stringify(step.output) : ''}`, 'success');
      else if (step.status === 'failed') addLog(`[Temporal: ${label}] Failed: ${step.error || 'Activity failed'}`, 'error');
      else if (step.status === 'skipped') addLog(`[Temporal: ${label}] Skipped.`, 'text');
    };

    const applyTrace = (trace: TraceResponse) => {
      if (!trace.steps) return;
      setNodeTraceStates(trace.steps);
      if (trace.status && trace.status !== activeRunStatus) {
        setActiveRunStatus(trace.status);
        setExecutionHistory(
          executionHistoryRef.current.map(r => r.run_id === activeRunId ? { ...r, status: trace.status } : r)
        );
        const normalized = trace.status.toUpperCase();
        if (normalized === 'COMPLETED') notify.success('Workflow completed successfully.');
        else if (normalized === 'FAILED') notify.error('Workflow execution failed.');
      }
      if (TERMINAL.has(trace.status) && intervalId !== undefined) {
        clearInterval(intervalId);
        intervalId = undefined;
      }
      Object.keys(trace.steps).forEach((nodeId) => logStepChange(nodeId, trace.steps[nodeId]));
    };

    const pollTrace = async () => {
      if (polling) return;
      polling = true;

      // Resolve the Temporal workflow ID (rf-xxx-xxxx) from the ref on every poll.
      // metadata.workflow_id is the visual ID and will 404 on the Temporal handle lookup.
      const activeRun = executionHistoryRef.current.find(r => r.run_id === activeRunId);
      const temporalWorkflowId = activeRun?.workflow_id ?? metadata.workflow_id;

      try {
        const trace = await compilerApi.getTrace(temporalWorkflowId, activeRunId);
        warnShown = false;
        applyTrace(trace);
      } catch (err) {
        console.error('Trace polling error:', err);
        const statusCode = (err as { statusCode?: number }).statusCode;
        // 404 = workflow not found in Temporal — stop polling, no point retrying
        if (statusCode === 404) {
          if (intervalId !== undefined) {
            clearInterval(intervalId);
            intervalId = undefined;
          }
        } else if (!warnShown) {
          notify.warn('Lost connection to execution trace. Retrying...');
          warnShown = true;
        }
      } finally {
        polling = false;
      }
    };

    pollTrace();
    intervalId = setInterval(async () => {
      await pollTrace();
      await refreshHistory();
    }, 2000);

    return () => {
      if (intervalId !== undefined) clearInterval(intervalId);
    };
  }, [activeRunId, nodes, refreshHistory, metadata.workflow_id, activeRunStatus]);

  // Keyboard shortcuts listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      if (
        activeEl &&
        (activeEl.tagName === 'INPUT' ||
          activeEl.tagName === 'TEXTAREA' ||
          activeEl.getAttribute('contenteditable') === 'true')
      ) {
        return;
      }

      // Ctrl + Enter or Cmd + Enter -> Validate & Compile
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        validateAndCompile();
      }

      // Ctrl + Z or Cmd + Z -> Undo
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        undo();
      }

      // Ctrl + Y or Cmd + Y -> Redo
      if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault();
        redo();
      }

      // Ctrl + Shift + E -> Export JSON
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'e') {
        e.preventDefault();
        handleExportJson();
      }

      // Delete -> Delete selected node or edge
      if (e.key === 'Delete') {
        if (selectedNodeId) {
          e.preventDefault();
          pushToUndo();
          setNodes(nodes.filter((n) => n.id !== selectedNodeId));
          setEdges(edges.filter((edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId));
          setSelectedNodeId(null);
        } else if (selectedEdgeId) {
          e.preventDefault();
          pushToUndo();
          setEdges(edges.filter((edge) => edge.id !== selectedEdgeId));
          setSelectedEdgeId(null);
        }
      }
    };

    globalThis.addEventListener('keydown', handleKeyDown);
    return () => {
      globalThis.removeEventListener('keydown', handleKeyDown);
    };
  }, [nodes, edges, selectedNodeId, selectedEdgeId, validateAndCompile, undo, redo, handleExportJson]);

  // Find selected elements
  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null;
  const selectedEdge = edges.find((e) => e.id === selectedEdgeId) ?? null;

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
    } else if (invalidNodeIds.has(node.id)) {
      className = 'node-invalid';
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
        hasNodes={nodes.length > 0}
        onExecute={handleHeaderExecute}
        isExecuting={isTriggeringRun}
        onZoomIn={() => reactFlowInstance?.zoomIn()}
        onZoomOut={() => reactFlowInstance?.zoomOut()}
        onFitView={() => reactFlowInstance?.fitView({ duration: 400 })}
        isSettingsOpen={isSettingsOpen}
        onSettingsToggle={toggleSettings}
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

          {nodes.length === 0 && (
            <div style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              pointerEvents: 'none',
              zIndex: 10,
              color: 'var(--text-muted)',
              userSelect: 'none',
            }}>
              <span style={{ fontSize: '32px', opacity: 0.35 }}>⬡</span>
              <span style={{ fontSize: '13px', opacity: 0.5, fontWeight: 600 }}>Drag a node from the sidebar to start building</span>
              <span style={{ fontSize: '11px', opacity: 0.35 }}>or load an example from the header</span>
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
            deleteKeyCode={null}
          >
            <Background color="#334155" gap={16} size={1} />
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
          isSettingsOpen={isSettingsOpen}
          onSettingsToggle={toggleSettings}
          onViewDslClick={handleViewDslClick}
          onDownloadDsl={handleDownloadDsl}
          onCopyDsl={handleCopyDsl}
          onExportJson={handleExportJson}
          onImportJson={handleImportJson}
          isCompiled={isCompiled}
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
          activeRunStatus={activeRunStatus}
          activeTab={simulatorTab}
          setActiveTab={setSimulatorTab}
          isOpen={isSimulatorOpen}
          setIsOpen={setIsSimulatorOpen}
          isSettingsOpen={isSettingsOpen}
          inputJson={inputJson}
          setInputJson={setInputJson}
          panelHeight={panelHeight}
          setPanelHeight={setPanelHeight}
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

