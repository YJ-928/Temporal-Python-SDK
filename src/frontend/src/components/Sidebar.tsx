import React from 'react';
import {
  CirclePlay,
  CircleStop,
  Play,
  GitFork,
  Zap,
  LogOut,
  Bot,
  Sparkles,
} from 'lucide-react';
import type { NodeType } from '../types';

interface SidebarProps {
  onLoadTemplate: (templateName: string) => void;
  onAddNode: (type: NodeType) => void;
}

const PALETTE: {
  type: NodeType;
  title: string;
  desc: string;
  icon: React.ReactNode;
  className: string;
}[] = [
  { type: 'start', title: 'START', desc: 'Workflow entry', icon: <CirclePlay size={20} />, className: 'palette-node-start' },
  { type: 'input', title: 'INPUT', desc: 'Map incoming fields', icon: <Play size={20} />, className: 'palette-node-input' },
  { type: 'if', title: 'IF', desc: 'Conditional branch', icon: <GitFork size={20} />, className: 'palette-node-if' },
  { type: 'action', title: 'ACTION', desc: 'Run an operation', icon: <Zap size={20} />, className: 'palette-node-action' },
  { type: 'agent', title: 'AGENT', desc: 'Select an LLM agent', icon: <Bot size={20} />, className: 'palette-node-agent' },
  { type: 'output', title: 'OUTPUT', desc: 'Define output fields', icon: <LogOut size={20} />, className: 'palette-node-output' },
  { type: 'end', title: 'END', desc: 'Workflow exit', icon: <CircleStop size={20} />, className: 'palette-node-end' },
];

export const Sidebar: React.FC<SidebarProps> = ({ onLoadTemplate, onAddNode }) => {
  const onDragStart = (event: React.DragEvent, nodeType: NodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <aside className="sidebar">
      <div>
        <h3 className="sidebar-section-title">Drag Node to Canvas</h3>
        <div className="node-palette">
          {PALETTE.map((item) => (
            <div
              key={item.type}
              className={`palette-node ${item.className}`}
              draggable
              onDragStart={(e) => onDragStart(e, item.type)}
              onClick={() => onAddNode(item.type)}
              title="Click or drag to add"
            >
              {item.icon}
              <div className="palette-node-info">
                <span className="palette-node-title">{item.title}</span>
                <span className="palette-node-desc">{item.desc}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginTop: 'auto' }}>
        <h3
          className="sidebar-section-title"
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Sparkles size={14} style={{ color: 'var(--accent)' }} /> Pre-built Templates
        </h3>
        <div className="template-list">
          <button
            className="template-card"
            onClick={() => onLoadTemplate('customer_support')}
          >
            <div className="template-card-title">Customer Support Triage</div>
            <div className="template-card-desc">
              START → INPUT → AGENT → IF → branches → OUTPUT → END
            </div>
          </button>

          <button
            className="template-card"
            onClick={() => onLoadTemplate('content_generation')}
          >
            <div className="template-card-title">Topic Researcher & Writer</div>
            <div className="template-card-desc">
              START → INPUT → AGENT → ACTION → OUTPUT → END
            </div>
          </button>
        </div>
      </div>
    </aside>
  );
};
