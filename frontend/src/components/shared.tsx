import React from 'react';
import type { ConfidenceCategory, Severity, InvestigationStatus, ToolStatus } from '../types';

// ── Confidence Badge ───────────────────────────────────────────────────────────

const CONFIDENCE_MAP: Record<ConfidenceCategory, { label: string; className: string }> = {
  strongly_supported: { label: 'Strongly Supported', className: 'badge-success' },
  plausible: { label: 'Plausible', className: 'badge-info' },
  weakly_supported: { label: 'Weakly Supported', className: 'badge-warning' },
  insufficient_evidence: { label: 'Insufficient Evidence', className: 'badge-muted' },
};

export function ConfidenceBadge({ confidence }: { confidence: ConfidenceCategory }) {
  const cfg = CONFIDENCE_MAP[confidence] ?? { label: confidence, className: 'badge-muted' };
  return <span className={cfg.className}>{cfg.label}</span>;
}

// ── Severity Badge ─────────────────────────────────────────────────────────────

const SEVERITY_MAP: Record<string, string> = {
  critical: 'badge-critical',
  high: 'badge-warning',
  warning: 'badge-warning',
  info: 'badge-info',
  medium: 'badge-info',
  low: 'badge-muted',
};

export function SeverityBadge({ severity }: { severity: string }) {
  const cls = SEVERITY_MAP[severity?.toLowerCase()] ?? 'badge-muted';
  return <span className={cls}>{severity?.toUpperCase()}</span>;
}

// ── Status Badge ───────────────────────────────────────────────────────────────

const STATUS_MAP: Record<string, { label: string; dot: string; text: string }> = {
  pending: { label: 'Pending', dot: 'status-dot-muted', text: 'text-text-muted' },
  running: { label: 'Running', dot: 'status-dot-info', text: 'text-status-info' },
  collecting_evidence: { label: 'Collecting Evidence', dot: 'status-dot-info', text: 'text-status-info' },
  analyzing: { label: 'Analyzing', dot: 'status-dot-info', text: 'text-status-info' },
  awaiting_approval: { label: 'Awaiting Approval', dot: 'status-dot-warning', text: 'text-status-warning' },
  remediating: { label: 'Remediating', dot: 'status-dot-warning', text: 'text-status-warning' },
  verifying: { label: 'Verifying', dot: 'status-dot-info', text: 'text-status-info' },
  completed: { label: 'Completed', dot: 'status-dot-success', text: 'text-accent-primary' },
  failed: { label: 'Failed', dot: 'status-dot-critical', text: 'text-status-critical' },
  resolved: { label: 'Resolved', dot: 'status-dot-success', text: 'text-accent-primary' },
};

export function StatusIndicator({ status }: { status: string }) {
  const cfg = STATUS_MAP[status] ?? { label: status, dot: 'status-dot-muted', text: 'text-text-muted' };
  const isActive = ['running', 'collecting_evidence', 'analyzing', 'remediating', 'verifying'].includes(status);
  return (
    <div className="flex items-center gap-2">
      <div className={`${cfg.dot} ${isActive ? 'animate-pulse-soft' : ''}`} />
      <span className={`text-xs font-medium ${cfg.text}`}>{cfg.label}</span>
    </div>
  );
}

// ── Tool Status Icon ───────────────────────────────────────────────────────────

export function ToolStatusIcon({ status }: { status: ToolStatus }) {
  if (status === 'completed') return <span className="text-accent-primary text-sm">✓</span>;
  if (status === 'failed') return <span className="text-status-critical text-sm">✗</span>;
  if (status === 'running') return (
    <div className="w-3 h-3 border-2 border-status-info border-t-transparent rounded-full animate-spin" />
  );
  if (status === 'skipped') return <span className="text-text-muted text-sm">—</span>;
  return <div className="w-2 h-2 rounded-full bg-text-muted opacity-40" />;
}

// ── Progress Bar ───────────────────────────────────────────────────────────────

export function ProgressBar({ value }: { value: number }) {
  return (
    <div className="progress-bar">
      <div className="progress-bar-fill" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

// ── Empty State ────────────────────────────────────────────────────────────────

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <div className="text-text-muted mb-4">{icon}</div>}
      <h3 className="text-text-primary font-medium mb-1">{title}</h3>
      {description && <p className="text-text-muted text-sm max-w-sm mb-4">{description}</p>}
      {action}
    </div>
  );
}

// ── Loading Spinner ────────────────────────────────────────────────────────────

export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const s = size === 'sm' ? 'w-3 h-3' : size === 'lg' ? 'w-8 h-8' : 'w-5 h-5';
  return (
    <div className={`${s} border-2 border-border border-t-accent-primary rounded-full animate-spin`} />
  );
}

// ── Section Header ─────────────────────────────────────────────────────────────

export function SectionHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div>
        <h2 className="text-text-primary font-semibold text-sm">{title}</h2>
        {subtitle && <p className="text-text-muted text-xs mt-0.5">{subtitle}</p>}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  );
}

// ── Relevance Tag ──────────────────────────────────────────────────────────────

export function RelevanceTag({ relevance }: { relevance: string }) {
  if (relevance === 'supporting') return (
    <span className="text-xs text-accent-primary bg-accent-primary bg-opacity-10 px-1.5 py-0.5 rounded">Supporting</span>
  );
  if (relevance === 'contradictory') return (
    <span className="text-xs text-status-warning bg-status-warning bg-opacity-10 px-1.5 py-0.5 rounded">Contradictory</span>
  );
  return <span className="text-xs text-text-muted bg-bg-elevated px-1.5 py-0.5 rounded">Neutral</span>;
}

// ── Mono Timestamp ─────────────────────────────────────────────────────────────

export function MonoTime({ iso }: { iso: string }) {
  try {
    const d = new Date(iso);
    return (
      <span className="mono text-text-muted">
        {d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
      </span>
    );
  } catch {
    return <span className="mono text-text-muted">{iso}</span>;
  }
}
