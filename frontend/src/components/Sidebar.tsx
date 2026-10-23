import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Search, Server, Database,
  FileText, Settings, Zap, ChevronRight
} from 'lucide-react';

const navItems = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/investigations', label: 'Investigations', icon: Search },
  { to: '/services', label: 'Services', icon: Server },
  { to: '/evidence', label: 'Evidence', icon: Database },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="w-[200px] flex-shrink-0 bg-bg-sidebar border-r border-border flex flex-col h-screen sticky top-0">
      {/* Branding */}
      <div className="px-4 py-5 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-accent-primary bg-opacity-20 flex items-center justify-center flex-shrink-0">
            <Zap className="w-4 h-4 text-accent-primary" />
          </div>
          <div>
            <div className="text-text-primary font-semibold text-sm leading-tight">IncidentLens</div>
            <div className="text-text-muted text-xs">AI Investigator</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-all duration-150 group ${
                isActive
                  ? 'text-accent-primary bg-accent-primary bg-opacity-10 font-medium'
                  : 'text-text-muted hover:text-text-secondary hover:bg-bg-elevated'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-accent-primary' : ''}`} />
                <span className="flex-1">{label}</span>
                {isActive && <ChevronRight className="w-3 h-3 opacity-50" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Bottom info */}
      <div className="px-4 py-3 border-t border-border">
        <div className="text-text-muted text-xs">v1.0.0 · Demo Mode</div>
      </div>
    </aside>
  );
}
