import type { Node, Edge } from 'reactflow';
import type { RFNodeData, RFEdgeData } from '../types';

const STORAGE_KEY = 'flowautomate-saved-workflows';
const LEGACY_STORAGE_KEY = 'workflow-builder-saved-workflows';

export interface StoredWorkflow {
  id: string;
  name: string;
  updatedAt: string;
  nodes: Node<RFNodeData>[];
  edges: Edge<RFEdgeData>[];
}

export interface StoredWorkflowSummary {
  id: string;
  name: string;
  updatedAt: string;
  nodeCount: number;
  edgeCount: number;
}

function readAll(): StoredWorkflow[] {
  try {
    let raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      // One-time migration from old key — copy forward, leave old key as backup
      const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
      if (legacy) {
        localStorage.setItem(STORAGE_KEY, legacy);
        raw = legacy;
      }
    }
    if (!raw) return [];
    const parsed = JSON.parse(raw) as StoredWorkflow[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeAll(workflows: StoredWorkflow[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(workflows));
}

export function listSavedWorkflows(): StoredWorkflowSummary[] {
  return readAll()
    .map(({ id, name, updatedAt, nodes, edges }) => ({
      id,
      name,
      updatedAt,
      nodeCount: nodes.length,
      edgeCount: edges.length,
    }))
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
}

export function getSavedWorkflow(id: string): StoredWorkflow | null {
  return readAll().find((w) => w.id === id) ?? null;
}

export function saveWorkflowLocally(
  name: string,
  nodes: Node<RFNodeData>[],
  edges: Edge<RFEdgeData>[],
  existingId?: string
): StoredWorkflow {
  const trimmed = name.trim() || 'Untitled workflow';
  const now = new Date().toISOString();
  const snapshot: StoredWorkflow = {
    id: existingId ?? crypto.randomUUID(),
    name: trimmed,
    updatedAt: now,
    nodes: JSON.parse(JSON.stringify(nodes)),
    edges: JSON.parse(JSON.stringify(edges)),
  };

  const workflows = readAll();
  const index = workflows.findIndex((w) => w.id === snapshot.id);
  if (index >= 0) {
    workflows[index] = snapshot;
  } else {
    workflows.push(snapshot);
  }
  writeAll(workflows);
  return snapshot;
}

export function deleteSavedWorkflow(id: string): boolean {
  const workflows = readAll();
  const next = workflows.filter((w) => w.id !== id);
  if (next.length === workflows.length) return false;
  writeAll(next);
  return true;
}
