import React, { useState, useCallback, useRef } from 'react';
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
import type { LogEntry } from './components/Simulator';
import { nodeTypes } from './components/CustomNodes';
import type { NodeType, RFNodeData, RFEdgeData } from './types';
import { getDefaultNodeData } from './utils/nodeDefaults';
import { getAgentById } from './constants/agents';

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

  // Pre-built Template Workflows
  const TEMPLATES: Record<string, { nodes: Node<RFNodeData>[]; edges: Edge<RFEdgeData>[] }> = {
    customer_support: {
      nodes: [
        {
          id: 'n-start',
          type: 'start',
          position: { x: 120, y: 0 },
          data: { label: 'START' },
        },
        {
          id: 'n-input',
          type: 'input',
          position: { x: 120, y: 100 },
          data: {
            label: 'User Request',
            inputFields: [
              { id: 'f1', field: 'message', store_as: 'ctx.message', type: 'string' },
              { id: 'f2', field: 'user_id', store_as: 'ctx.user_id', type: 'string' },
            ],
          },
        },
        {
          id: 'n-triage',
          type: 'agent',
          position: { x: 120, y: 230 },
          data: { label: 'Triage Agent', selectedAgentId: 'agent-001' },
        },
        {
          id: 'n-if',
          type: 'if',
          position: { x: 120, y: 360 },
          data: {
            label: 'Billing?',
            ifCondition: { left: 'ctx.intent', operator: '==', right: 'billing' },
          },
        },
        {
          id: 'n-billing',
          type: 'agent',
          position: { x: -60, y: 490 },
          data: { label: 'Billing Agent', selectedAgentId: 'agent-002' },
        },
        {
          id: 'n-support',
          type: 'agent',
          position: { x: 300, y: 490 },
          data: { label: 'Support Agent', selectedAgentId: 'agent-003' },
        },
        {
          id: 'n-action',
          type: 'action',
          position: { x: -60, y: 620 },
          data: {
            label: 'Account Lookup',
            actionOperation: 'http_get',
            actionInputs: '{"path": "/api/accounts/{id}"}',
            actionOutput: 'ctx.account',
          },
        },
        {
          id: 'n-output',
          type: 'output',
          position: { x: 120, y: 750 },
          data: {
            label: 'Response',
            outputFields: [
              { id: 'o1', field: 'reply', type: 'string' },
              { id: 'o2', field: 'status', type: 'string' },
            ],
          },
        },
        {
          id: 'n-end',
          type: 'end',
          position: { x: 120, y: 880 },
          data: { label: 'END' },
        },
      ],
      edges: [
        { id: 'e0', source: 'n-start', target: 'n-input', animated: true },
        { id: 'e1', source: 'n-input', target: 'n-triage', animated: true },
        { id: 'e2', source: 'n-triage', target: 'n-if', animated: true },
        { id: 'e3', source: 'n-if', target: 'n-billing', sourceHandle: 'branch1', label: 'true', data: { branch: 'branch1', label: 'true' }, animated: true },
        { id: 'e4', source: 'n-if', target: 'n-support', sourceHandle: 'branch2', label: 'false', data: { branch: 'branch2', label: 'false' }, animated: true },
        { id: 'e5', source: 'n-billing', target: 'n-action', animated: true },
        { id: 'e6', source: 'n-action', target: 'n-output', animated: true },
        { id: 'e7', source: 'n-support', target: 'n-output', animated: true },
        { id: 'e8', source: 'n-output', target: 'n-end', animated: true },
      ],
    },
    content_generation: {
      nodes: [
        {
          id: 'n-start',
          type: 'start',
          position: { x: 120, y: 0 },
          data: { label: 'START' },
        },
        {
          id: 'n-input',
          type: 'input',
          position: { x: 120, y: 100 },
          data: {
            label: 'Article Topic',
            inputFields: [
              { id: 'f1', field: 'topic', store_as: 'ctx.topic', type: 'string' },
            ],
          },
        },
        {
          id: 'n-researcher',
          type: 'agent',
          position: { x: 120, y: 230 },
          data: { label: 'Researcher', selectedAgentId: 'agent-004' },
        },
        {
          id: 'n-search',
          type: 'action',
          position: { x: 120, y: 360 },
          data: {
            label: 'Web Search',
            actionOperation: 'http_post',
            actionInputs: '{"url": "https://api.search.com/v1", "query": "{{ctx.topic}}"}',
            actionOutput: 'ctx.search_results',
          },
        },
        {
          id: 'n-writer',
          type: 'agent',
          position: { x: 120, y: 490 },
          data: { label: 'Writer', selectedAgentId: 'agent-005' },
        },
        {
          id: 'n-output',
          type: 'output',
          position: { x: 120, y: 620 },
          data: {
            label: 'Save Draft',
            outputFields: [
              { id: 'o1', field: 'article_body', type: 'string' },
              { id: 'o2', field: 'title', type: 'string' },
            ],
          },
        },
        {
          id: 'n-end',
          type: 'end',
          position: { x: 120, y: 750 },
          data: { label: 'END' },
        },
      ],
      edges: [
        { id: 'e0', source: 'n-start', target: 'n-input', animated: true },
        { id: 'e1', source: 'n-input', target: 'n-researcher', animated: true },
        { id: 'e2', source: 'n-researcher', target: 'n-search', animated: true },
        { id: 'e3', source: 'n-search', target: 'n-writer', animated: true },
        { id: 'e4', source: 'n-writer', target: 'n-output', animated: true },
        { id: 'e5', source: 'n-output', target: 'n-end', animated: true },
      ],
    },
  };

  // Inspector States
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  // Simulator States
  const [simStatus, setSimStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [simulatingNodeId, setSimulatingNodeId] = useState<string | null>(null);
  const [completedNodeIds, setCompletedNodeIds] = useState<string[]>([]);

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

  const onNodesChange = (changes: any) => {
    pushToUndo();
    onNodesChangeInternal(changes);
  };

  const onEdgesChange = (changes: any) => {
    pushToUndo();
    onEdgesChangeInternal(changes);
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
  }, [setNodes]);

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
  }, [setEdges]);

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
  }, [nodes, setEdges]);

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
    },
    [reactFlowInstance, setNodes]
  );

  // Click palette to add node directly to viewport center
  const onAddNodeDirectly = useCallback((type: NodeType) => {
    pushToUndo();
    if (!reactFlowInstance) return;

    // Position at center of screen viewport
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
  }, [reactFlowInstance, setNodes]);

  // Reset flow builder
  const handleReset = useCallback(() => {
    pushToUndo();
    setNodes([]);
    setEdges([]);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setSimStatus('idle');
    setLogs([]);
    setSimulatingNodeId(null);
    setCompletedNodeIds([]);
    if (simulationTimeoutRef.current) {
      clearTimeout(simulationTimeoutRef.current);
    }
  }, [setNodes, setEdges]);

  // Load workflow from browser local storage
  const handleLoadWorkflow = useCallback(
    (loadedNodes: Node<RFNodeData>[], loadedEdges: Edge<RFEdgeData>[]) => {
      pushToUndo();
      setNodes(JSON.parse(JSON.stringify(loadedNodes)));
      setEdges(JSON.parse(JSON.stringify(loadedEdges)));
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
      setSimStatus('idle');
      setLogs([]);
      setSimulatingNodeId(null);
      setCompletedNodeIds([]);
      if (simulationTimeoutRef.current) {
        clearTimeout(simulationTimeoutRef.current);
      }
    },
    [setNodes, setEdges]
  );

  // Load a preset template
  const handleLoadTemplate = useCallback((templateName: string) => {
    pushToUndo();
    handleReset();
    const template = TEMPLATES[templateName];
    if (template) {
      setNodes(JSON.parse(JSON.stringify(template.nodes)));
      setEdges(JSON.parse(JSON.stringify(template.edges)));
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
  };

  // Redo operation
  const redo = () => {
    if (redoStack.length === 0) return;
    const next = redoStack[redoStack.length - 1];
    setUndoStack((prev) => [...prev, { nodes, edges }]);
    setNodes(next.nodes);
    setEdges(next.edges);
    setRedoStack((prev) => prev.slice(0, -1));
  };

  // Simulator Logging Helper
  const addLog = (message: string, type: LogEntry['type'] = 'text') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, { timestamp, type, message }]);
  };

  // Run Simulation Engine
  const startSimulation = () => {
    if (nodes.length === 0) {
      alert("Canvas is empty! Drag some nodes or Load Demo first.");
      return;
    }

    if (simulationTimeoutRef.current) {
      clearTimeout(simulationTimeoutRef.current);
    }

    setSimStatus('running');
    setLogs([]);
    setCompletedNodeIds([]);
    setSimulatingNodeId(null);

    // Find entry points
    const sourceIds = new Set(edges.map((e) => e.target));
    const entryNodes = nodes.filter(
      (n) => n.type === 'start' || n.type === 'input' || !sourceIds.has(n.id)
    );

    if (entryNodes.length === 0) {
      addLog("Error: Could not find any entry points. Connect nodes and try again.", 'error');
      setSimStatus('failed');
      return;
    }

    addLog("Starting Workflow Simulation Runner...", 'info');

    // Start simulation queue with entry nodes
    const queue = entryNodes.map(n => n.id);
    runNextSimulationStep(queue, []);
  };

  // Recursive step executor
  const runNextSimulationStep = (queue: string[], completed: string[]) => {
    if (queue.length === 0) {
      addLog("Workflow execution completed successfully.", 'success');
      setSimStatus('completed');
      setSimulatingNodeId(null);
      return;
    }

    const currentNodeId = queue[0];
    const remainingQueue = queue.slice(1);
    const node = nodes.find((n) => n.id === currentNodeId);

    if (!node) {
      runNextSimulationStep(remainingQueue, completed);
      return;
    }

    setSimulatingNodeId(currentNodeId);

    // Print step initiation logs
    const agent = getAgentById(node.data.selectedAgentId);
    const label = node.data.label || agent?.name || node.id;
    const cond = node.data.ifCondition;

    if (node.type === 'start') {
      addLog(`[START: ${label}] Workflow execution started.`, 'info');
    } else if (node.type === 'input') {
      const count = node.data.inputFields?.length ?? 0;
      addLog(`[INPUT: ${label}] Mapping ${count} input field(s)...`, 'info');
    } else if (node.type === 'if') {
      addLog(
        `[IF: ${label}] Evaluating: ${cond?.left || '?'} ${cond?.operator || '=='} ${cond?.right || '?'}`,
        'info'
      );
    } else if (node.type === 'action') {
      addLog(
        `[ACTION: ${label}] Running operation "${node.data.actionOperation || 'unknown'}"...`,
        'info'
      );
    } else if (node.type === 'agent') {
      addLog(
        `[AGENT: ${label}] Invoking agent (${node.data.selectedAgentId || 'not set'})...`,
        'info'
      );
    } else if (node.type === 'output') {
      const count = node.data.outputFields?.length ?? 0;
      addLog(`[OUTPUT: ${label}] Emitting ${count} output field(s)...`, 'info');
    } else if (node.type === 'end') {
      addLog(`[END: ${label}] Reached workflow terminal.`, 'info');
    }

    // Set timeout to mock asynchronous execution delay
    simulationTimeoutRef.current = window.setTimeout(() => {
      // Print execution completion logs
      if (node.type === 'start') {
        addLog(`[START: ${label}] Entry point ready.`, 'success');
      } else if (node.type === 'input') {
        addLog(`[INPUT: ${label}] Fields mapped into context.`, 'success');
      } else if (node.type === 'if') {
        addLog(
          `[IF: ${label}] Condition result: ${cond?.left} ${cond?.operator} ${cond?.right}`,
          'success'
        );
      } else if (node.type === 'action') {
        addLog(`[ACTION: ${label}] Operation completed → ${node.data.actionOutput || 'ctx'}`, 'success');
      } else if (node.type === 'agent') {
        addLog(`[AGENT: ${label}] Agent run finished.`, 'success');
      } else if (node.type === 'output') {
        addLog(`[OUTPUT: ${label}] Output payload ready.`, 'success');
      } else if (node.type === 'end') {
        addLog(`[END: ${label}] Workflow complete.`, 'success');
      }

      const nextCompleted = [...completed, currentNodeId];
      setCompletedNodeIds(nextCompleted);

      // Find next targets
      const nextQueue = [...remainingQueue];
      const outgoingEdges = edges.filter((e) => e.source === currentNodeId);

      if (node.type === 'if') {
        const b1 = outgoingEdges.find((e) => e.data?.branch === 'branch1');
        const b2 = outgoingEdges.find((e) => e.data?.branch === 'branch2');
        const decision = Math.random() > 0.4 ? 'branch1' : 'branch2';
        const chosenEdge = decision === 'branch1' ? b1 : b2;

        if (chosenEdge) {
          addLog(
            `[IF: ${label}] Taking ${decision === 'branch1' ? 'true' : 'false'} branch → ${chosenEdge.target}`,
            'info'
          );
          if (!nextQueue.includes(chosenEdge.target) && !nextCompleted.includes(chosenEdge.target)) {
            nextQueue.push(chosenEdge.target);
          }
        } else {
          const fallback = b1 || b2;
          if (fallback) {
            addLog(`[IF: ${label}] Missing branch; using fallback edge.`, 'warning');
            if (!nextQueue.includes(fallback.target) && !nextCompleted.includes(fallback.target)) {
              nextQueue.push(fallback.target);
            }
          } else {
            addLog(`[IF: ${label}] No branch targets connected.`, 'error');
            setSimStatus('failed');
            return;
          }
        }
      } else if (node.type !== 'end') {
        // Plain connections
        outgoingEdges.forEach((edge) => {
          if (edge.data?.condition) {
            addLog(`[Routing: ${label}] Found edge condition: "${edge.data.condition}"`, 'text');
          }
          if (!nextQueue.includes(edge.target) && !nextCompleted.includes(edge.target)) {
            nextQueue.push(edge.target);
          }
        });
      }

      runNextSimulationStep(nextQueue, nextCompleted);
    }, 1500);
  };

  const stopSimulation = () => {
    if (simulationTimeoutRef.current) {
      clearTimeout(simulationTimeoutRef.current);
    }
    setSimStatus('idle');
    setSimulatingNodeId(null);
    addLog("Simulation terminated manually by user.", 'warning');
  };

  const clearLogs = () => {
    setLogs([]);
  };

  // Find selected elements
  const selectedNode = nodes.find((n) => n.id === selectedNodeId) || null;
  const selectedEdge = edges.find((e) => e.id === selectedEdgeId) || null;

  // Add styles for simulating states inside the nodes list dynamically
  const styledNodes = nodes.map((node) => {
    let className = '';
    if (node.id === simulatingNodeId) {
      className = 'node-simulating';
    } else if (completedNodeIds.includes(node.id)) {
      className = 'node-completed';
    }
    return {
      ...node,
      className: `${node.className || ''} ${className}`.trim(),
    };
  });

  return (
    <div className="app-container">
      <Header
        nodes={nodes}
        edges={edges}
        onReset={handleReset}
        onLoadTemplate={handleLoadTemplate}
        onUndo={undo}
        onRedo={redo}
        canUndo={undoStack.length > 0}
        canRedo={redoStack.length > 0}
        onLoadWorkflow={handleLoadWorkflow}
      />
      <div className="main-content">
        <Sidebar
          onLoadTemplate={handleLoadTemplate}
          onAddNode={onAddNodeDirectly}
        />

        <div className="canvas-container" ref={reactFlowWrapper}>
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
        />

        <Simulator
          logs={logs}
          status={simStatus}
          onStartSimulation={startSimulation}
          onStopSimulation={stopSimulation}
          onClearLogs={clearLogs}
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
