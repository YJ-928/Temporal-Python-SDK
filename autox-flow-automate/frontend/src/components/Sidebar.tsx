import React from 'react';
import {
  Play,
  Square,
  Database,
  GitFork,
  Zap,
  FileOutput,
  Bot,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import type { NodeType } from '../types';

interface SidebarProps {
  onAddNode: (type: NodeType) => void;
  collapsed: boolean;
  onToggle: () => void;
}

const PALETTE: {
  type: NodeType;
  title: string;
  icon: React.ReactNode;
  className: string;
}[] = [
  { type: 'start',  title: 'START',  icon: <Play size={20} />,       className: 'palette-node-start' },
  { type: 'input',  title: 'INPUT',  icon: <Database size={20} />,   className: 'palette-node-input' },
  { type: 'if',     title: 'IF',     icon: <GitFork size={20} />,    className: 'palette-node-if' },
  { type: 'action', title: 'ACTION', icon: <Zap size={20} />,        className: 'palette-node-action' },
  { type: 'agent',  title: 'AGENT',  icon: <Bot size={20} />,        className: 'palette-node-agent' },
  { type: 'output', title: 'OUTPUT', icon: <FileOutput size={20} />, className: 'palette-node-output' },
  { type: 'end',    title: 'END',    icon: <Square size={20} />,     className: 'palette-node-end' },
];

export const Sidebar: React.FC<SidebarProps> = ({ onAddNode, collapsed, onToggle }) => {
  const onDragStart = (event: React.DragEvent, nodeType: NodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <aside className={`sidebar${collapsed ? ' sidebar--collapsed' : ''}`}>
      <div className="sidebar-header-row">
        {!collapsed && <span className="sidebar-section-title" style={{ margin: 0 }}>Node Types</span>}
        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={onToggle}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      <div className="node-palette">
        {PALETTE.map((item) => (
          <button
            key={item.type}
            type="button"
            className={`palette-node ${item.className}`}
            draggable
            onDragStart={(e) => onDragStart(e, item.type)}
            onClick={() => onAddNode(item.type)}
            title={item.title}
          >
            {item.icon}
            {!collapsed && <span className="palette-node-title">{item.title}</span>}
          </button>
        ))}
      </div>
    </aside>
  );
};
