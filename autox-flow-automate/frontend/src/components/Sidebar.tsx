import React from 'react';
import {
  Play,
  Square,
  Database,
  GitFork,
  Zap,
  FileOutput,
  Bot,
} from 'lucide-react';
import type { NodeType } from '../types';

interface SidebarProps {
  onAddNode: (type: NodeType) => void;
}

const PALETTE: {
  type: NodeType;
  title: string;
  desc: string;
  icon: React.ReactNode;
  className: string;
}[] = [
  { type: 'start',  title: 'START',  desc: 'Filled circle · Green',           icon: <Play size={20} />,       className: 'palette-node-start' },
  { type: 'input',  title: 'INPUT',  desc: 'Rect + thick top bar · Gray',      icon: <Database size={20} />,   className: 'palette-node-input' },
  { type: 'if',     title: 'IF',     desc: 'Diamond · Blue · condition',       icon: <GitFork size={20} />,    className: 'palette-node-if' },
  { type: 'action', title: 'ACTION', desc: 'Rect + left bar · Teal · API call', icon: <Zap size={20} />,      className: 'palette-node-action' },
  { type: 'agent',  title: 'AGENT',  desc: 'Dashed rect · Purple · AI agent',  icon: <Bot size={20} />,       className: 'palette-node-agent' },
  { type: 'output', title: 'OUTPUT', desc: 'Rect · Pink · result emitter',     icon: <FileOutput size={20} />, className: 'palette-node-output' },
  { type: 'end',    title: 'END',    desc: 'Filled circle · Red',              icon: <Square size={20} />,    className: 'palette-node-end' },
];

export const Sidebar: React.FC<SidebarProps> = ({ onAddNode }) => {
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
            <button
              key={item.type}
              type="button"
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
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
};
