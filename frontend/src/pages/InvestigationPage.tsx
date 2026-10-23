import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronDown, ChevronRight, AlertTriangle, CheckCircle,
  AlertCircle, Clock, MessageSquare, X, Send, Shield,
  BarChart2, Download, RefreshCw, ChevronUp
} from 'lucide-react';
import {
  getInvestigation, approveRemediation, sendChatMessage, downloadReport, getReport
} from '../services/api';
import type { Investigation, Hypothesis, EvidenceItem, ChatMessage } from '../types';
import {
  StatusIndicator, ProgressBar, ToolStatusIcon, ConfidenceBadge,
  SeverityBadge, RelevanceTag, MonoTime, Spinner, EmptyState
} from '../components/shared';
import { formatDistanceToNow } from 'date-fns';

// ── Tool Progress Panel ────────────────────────────────────────────────────────

function ToolPanel({ inv }: { inv: Investigation }) {
  return (
    <div className="space-y-1">
      {inv.tool_history.map((tool, i) => (
        <div key={i} className="flex items-start gap-3 py-2">
          <div className="flex-shrink-0 mt-0.5">
            <ToolStatusIcon status={tool.status} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between">
              <span className={`text-xs font-medium ${
                tool.status === 'completed' ? 'text-text-secondary' :
                tool.status === 'running' ? 'text-status-info' :
                tool.status === 'failed' ? 'text-status-critical' :
                'text-text-muted'
              }`}>{tool.display_name}</span>
              {tool.completed_at && (
                <MonoTime iso={tool.completed_at} />
              )}
            </div>
            {tool.result_summary && tool.status === 'completed' && (
              <p className="text-text-muted text-xs mt-0.5 truncate">{tool.result_summary}</p>
            )}
            {tool.error && (
              <p className="text-status-critical text-xs mt-0.5 truncate">{tool.error}</p>
            )}
            {tool.status === 'pending' && (
              <p className="text-text-muted text-xs mt-0.5 opacity-50">{tool.description}</p>
            )}
          </div>
          {tool.evidence_count > 0 && (
            <span className="text-xs text-text-muted flex-shrink-0">+{tool.evidence_count}</span>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Hypothesis Card ────────────────────────────────────────────────────────────

function HypothesisCard({ hyp, expanded, onToggle }: {
  hyp: Hypothesis;
  expanded: boolean;
  onToggle: () => void;
}) {
  const isTop = hyp.rank === 1;
  return (
    <div className={`rounded-lg border ${isTop ? 'border-accent-primary border-opacity-30 bg-accent-primary bg-opacity-5' : 'border-border bg-bg-surface'}`}>
      <button
        className="w-full flex items-start gap-3 p-4 text-left"
        onClick={onToggle}
      >
        <div className="flex-shrink-0 w-5 h-5 rounded-full border border-border flex items-center justify-center mt-0.5">
          <span className="text-xs text-text-muted">{hyp.rank}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-text-primary text-sm font-medium">{hyp.title}</span>
            {isTop && <span className="badge-success text-xs">Leading</span>}
          </div>
          <div className="mt-1">
            <ConfidenceBadge confidence={hyp.confidence} />
          </div>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-text-muted flex-shrink-0" /> : <ChevronDown className="w-4 h-4 text-text-muted flex-shrink-0" />}
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-border animate-fade-in">
          <p className="text-text-muted text-xs mt-3 mb-4 leading-relaxed">{hyp.confidence_explanation}</p>

          {hyp.supporting_evidence.length > 0 && (
            <div className="mb-3">
              <div className="text-xs font-medium text-accent-primary mb-1.5">Supporting Evidence</div>
              <ul className="space-y-1">
                {hyp.supporting_evidence.map((e, i) => (
                  <li key={i} className="text-xs text-text-secondary flex gap-2">
                    <span className="text-accent-primary flex-shrink-0 mt-0.5">•</span>
                    <span>{e}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {hyp.contradictory_evidence.length > 0 && (
            <div className="mb-3">
              <div className="text-xs font-medium text-status-warning mb-1.5">What Remains Uncertain</div>
              <ul className="space-y-1">
                {hyp.contradictory_evidence.map((e, i) => (
                  <li key={i} className="text-xs text-text-muted flex gap-2">
                    <span className="text-status-warning flex-shrink-0 mt-0.5">•</span>
                    <span>{e}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-3 pt-3 border-t border-border">
            <div className="text-xs font-medium text-text-muted mb-1">Recommended Next Step</div>
            <p className="text-xs text-text-secondary">{hyp.recommended_action}</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Remediation Dialog ─────────────────────────────────────────────────────────

function RemediationDialog({ inv, onClose, onApprove }: {
  inv: Investigation;
  onClose: () => void;
  onApprove: (approved: boolean) => void;
}) {
  const rem = inv.remediation!;
  const [loading, setLoading] = useState(false);

  const handleDecision = async (approved: boolean) => {
    setLoading(true);
    onApprove(approved);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg-main bg-opacity-80 backdrop-blur-sm">
      <div className="bg-bg-elevated border border-border rounded-xl w-full max-w-lg animate-fade-in shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-border">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Shield className="w-4 h-4 text-status-warning" />
              <span className="text-text-primary font-semibold text-sm">Review Remediation</span>
              <span className="badge-muted text-xs">SIMULATED</span>
            </div>
            <p className="text-text-muted text-xs">
              Review the proposed action carefully before approving. This will execute in the simulated environment only.
            </p>
          </div>
          <button onClick={onClose} className="btn-ghost p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 max-h-96 overflow-y-auto">
          <div>
            <div className="text-xs text-text-muted mb-1">Proposed Action</div>
            <div className="text-text-primary font-medium text-sm">{rem.title}</div>
          </div>

          <div>
            <div className="text-xs text-text-muted mb-1">Why This Is Recommended</div>
            <p className="text-text-secondary text-xs leading-relaxed">{rem.reason}</p>
          </div>

          <div>
            <div className="text-xs text-text-muted mb-1">Expected Outcome</div>
            <p className="text-text-secondary text-xs">{rem.expected_outcome}</p>
          </div>

          <div>
            <div className="text-xs text-text-muted mb-1">What Will Change</div>
            <p className="text-text-secondary text-xs">{rem.what_will_change}</p>
          </div>

          {rem.risks.length > 0 && (
            <div>
              <div className="text-xs text-status-warning mb-1">Potential Side Effects</div>
              <ul className="space-y-1">
                {rem.risks.map((r, i) => (
                  <li key={i} className="text-xs text-text-muted flex gap-1.5">
                    <AlertTriangle className="w-3 h-3 text-status-warning flex-shrink-0 mt-0.5" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <div className="text-xs text-text-muted mb-1">Verification Procedure</div>
            <p className="text-text-secondary text-xs">{rem.verification_procedure}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 p-5 border-t border-border">
          <button
            className="btn-primary flex-1"
            onClick={() => handleDecision(true)}
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center gap-2 justify-center">
                <Spinner size="sm" /> Executing…
              </span>
            ) : 'Approve and Execute Simulation'}
          </button>
          <button
            className="btn-secondary"
            onClick={() => handleDecision(false)}
            disabled={loading}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Chat Panel ─────────────────────────────────────────────────────────────────

function ChatPanel({ inv }: { inv: Investigation }) {
  const [messages, setMessages] = useState<ChatMessage[]>(inv.chat_messages ?? []);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    const msg = input.trim();
    if (!msg || sending) return;
    setInput('');
    setSending(true);
    setMessages(m => [...m, {
      role: 'user', content: msg, timestamp: new Date().toISOString()
    }]);
    try {
      const res = await sendChatMessage(inv.id, msg);
      setMessages(m => [...m, { role: 'assistant', content: res.response, timestamp: res.timestamp }]);
    } catch {
      setMessages(m => [...m, {
        role: 'assistant',
        content: 'I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      }]);
    }
    setSending(false);
  };

  const suggestions = [
    'Why do you think this is the root cause?',
    'What evidence contradicts the hypothesis?',
    'What should I do next?',
    'Show me the most relevant logs',
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 ? (
          <div className="py-4">
            <p className="text-text-muted text-xs text-center mb-3">Ask anything about this investigation</p>
            <div className="space-y-1.5">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => setInput(s)}
                  className="w-full text-left px-2.5 py-1.5 rounded text-xs text-text-muted bg-bg-surface border border-border hover:border-accent-primary hover:text-text-secondary transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-lg px-3 py-2 text-xs leading-relaxed ${
                m.role === 'user'
                  ? 'bg-accent-primary bg-opacity-15 text-text-primary'
                  : 'bg-bg-surface border border-border text-text-secondary'
              }`}>
                <div className="whitespace-pre-wrap">{m.content}</div>
              </div>
            </div>
          ))
        )}
        {sending && (
          <div className="flex justify-start">
            <div className="bg-bg-surface border border-border rounded-lg px-3 py-2">
              <Spinner size="sm" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-border p-2 flex gap-2">
        <input
          className="flex-1 px-2.5 py-1.5 bg-bg-elevated border border-border rounded text-xs text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-primary"
          placeholder="Ask about this investigation…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
        />
        <button
          className="flex-shrink-0 p-1.5 rounded bg-accent-primary text-bg-main hover:bg-opacity-90 transition-colors disabled:opacity-40"
          onClick={send}
          disabled={!input.trim() || sending}
        >
          <Send className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}

// ── Verification Panel ─────────────────────────────────────────────────────────

function VerificationPanel({ inv }: { inv: Investigation }) {
  const ver = inv.verification_result;
  if (!ver) return null;
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-3">
        {ver.passed ? (
          <CheckCircle className="w-4 h-4 text-accent-primary" />
        ) : (
          <AlertCircle className="w-4 h-4 text-status-critical" />
        )}
        <span className="text-sm font-medium text-text-primary">
          Verification {ver.passed ? 'Passed' : 'Failed'}
        </span>
        <span className="badge-muted text-xs">{ver.final_status}</span>
      </div>
      <div className="space-y-2">
        {ver.checks.map((c, i) => (
          <div key={i} className="flex items-center gap-3">
            {c.passed
              ? <CheckCircle className="w-3 h-3 text-accent-primary flex-shrink-0" />
              : <X className="w-3 h-3 text-status-critical flex-shrink-0" />}
            <span className="text-xs text-text-secondary flex-1">{c.check}</span>
            <span className="mono text-xs text-text-muted">{c.before} → {c.after}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Investigation Page ────────────────────────────────────────────────────

const POLL_ACTIVE = new Set(['running', 'collecting_evidence', 'analyzing', 'remediating', 'verifying']);

export default function InvestigationPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [inv, setInv] = useState<Investigation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedHyps, setExpandedHyps] = useState<Set<string>>(new Set(['hyp-001']));
  const [showRemediation, setShowRemediation] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [toolsExpanded, setToolsExpanded] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetch = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getInvestigation(id);
      setInv(data);
      setError('');
      if (!POLL_ACTIVE.has(data.status)) {
        if (pollRef.current) clearInterval(pollRef.current);
      }
    } catch {
      setError('Failed to load investigation');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetch();
    pollRef.current = setInterval(fetch, 2000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetch]);

  const handleApprove = async (approved: boolean) => {
    if (!inv) return;
    setShowRemediation(false);
    try {
      const updated = await approveRemediation(inv.id, approved);
      setInv(updated);
      if (approved) {
        pollRef.current = setInterval(fetch, 2000);
      }
    } catch {}
  };

  const handleDownload = async (format: 'json' | 'markdown') => {
    if (!inv) return;
    await downloadReport(inv.id, format);
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <Spinner size="lg" />
    </div>
  );
  if (error || !inv) return (
    <div className="p-6">
      <div className="card p-8 text-center">
        <AlertCircle className="w-8 h-8 text-status-critical mx-auto mb-3" />
        <p className="text-text-secondary">{error || 'Investigation not found'}</p>
        <button className="btn-primary mt-4" onClick={() => navigate('/investigations')}>Back to Investigations</button>
      </div>
    </div>
  );

  const isActive = POLL_ACTIVE.has(inv.status);
  const showRemediationBtn = inv.remediation &&
    ['proposed', 'awaiting_approval'].includes(inv.remediation.status);
  const hasReport = inv.report || inv.status === 'completed';

  return (
    <div className="h-full flex flex-col">
      {/* Top bar */}
      <div className="border-b border-border px-6 py-4 flex items-start justify-between gap-4 flex-shrink-0">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="mono text-text-muted text-xs">{inv.id.slice(0, 8)}</span>
            <span className="text-text-muted">·</span>
            <span className="mono text-text-secondary text-xs">{inv.service}</span>
            <SeverityBadge severity={inv.hypotheses[0]?.confidence === 'strongly_supported' ? 'critical' : 'warning'} />
          </div>
          <p className="text-text-primary font-medium text-sm">{inv.incident_description}</p>
          <div className="flex items-center gap-4 mt-2">
            <StatusIndicator status={inv.status} />
            {inv.progress > 0 && (
              <div className="flex items-center gap-2 flex-1 max-w-xs">
                <ProgressBar value={inv.progress} />
                <span className="text-xs text-text-muted flex-shrink-0">{inv.progress}%</span>
              </div>
            )}
            <span className="text-xs text-text-muted">
              {formatDistanceToNow(new Date(inv.created_at), { addSuffix: true })}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {hasReport && (
            <div className="flex gap-1">
              <button className="btn-ghost flex items-center gap-1" onClick={() => handleDownload('json')}>
                <Download className="w-3.5 h-3.5" /> JSON
              </button>
              <button className="btn-ghost flex items-center gap-1" onClick={() => handleDownload('markdown')}>
                <Download className="w-3.5 h-3.5" /> MD
              </button>
            </div>
          )}
          <button
            className={`btn-ghost flex items-center gap-1.5 ${showChat ? 'text-accent-primary' : ''}`}
            onClick={() => setShowChat(c => !c)}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Assistant
          </button>
          {showRemediationBtn && (
            <button className="btn-primary" onClick={() => setShowRemediation(true)}>
              Review Remediation
            </button>
          )}
        </div>
      </div>

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left panel */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Tool execution */}
          <div className="card">
            <button
              className="w-full flex items-center justify-between px-4 py-3"
              onClick={() => setToolsExpanded(e => !e)}
            >
              <span className="text-xs font-semibold text-text-secondary">Investigation Steps</span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-muted">
                  {inv.tool_history.filter(t => t.status === 'completed').length}/{inv.tool_history.length} complete
                </span>
                {toolsExpanded ? <ChevronUp className="w-3.5 h-3.5 text-text-muted" /> : <ChevronDown className="w-3.5 h-3.5 text-text-muted" />}
              </div>
            </button>
            {toolsExpanded && (
              <div className="px-4 pb-4 border-t border-border pt-3">
                <ToolPanel inv={inv} />
              </div>
            )}
            {!toolsExpanded && isActive && (
              <div className="px-4 pb-3">
                <ProgressBar value={inv.progress} />
              </div>
            )}
          </div>

          {/* Remediation result */}
          {inv.remediation_result && (
            <div className="card p-4 animate-fade-in">
              <div className="flex items-center gap-2 mb-3">
                <Shield className="w-4 h-4 text-accent-primary" />
                <span className="text-sm font-medium text-text-primary">Remediation Executed</span>
                <span className="badge-muted text-xs">{inv.remediation_result.environment}</span>
              </div>
              <ul className="space-y-1.5">
                {inv.remediation_result.changes_applied.map((c, i) => (
                  <li key={i} className="flex gap-2 text-xs text-text-secondary">
                    <CheckCircle className="w-3 h-3 text-accent-primary flex-shrink-0 mt-0.5" />
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Verification */}
          {inv.verification_result && <VerificationPanel inv={inv} />}

          {/* Evidence summary */}
          {inv.evidence.length > 0 && (
            <div className="card">
              <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                <span className="text-xs font-semibold text-text-secondary">Evidence Collected</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-text-muted">{inv.evidence.length} items</span>
                  <button
                    className="btn-ghost text-xs"
                    onClick={() => navigate('/evidence', { state: { investigationId: inv.id } })}
                  >
                    View all
                  </button>
                </div>
              </div>
              <div className="divide-y divide-border">
                {inv.evidence.slice(0, 4).map(e => (
                  <div key={e.id} className="px-4 py-2.5 flex items-start gap-3">
                    <RelevanceTag relevance={e.relevance} />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-text-secondary truncate">{e.summary}</p>
                      <span className="mono text-text-muted">{e.source}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right panel: hypotheses */}
        <div className="w-[340px] flex-shrink-0 border-l border-border overflow-y-auto p-4 space-y-4">
          {/* Hypotheses */}
          {inv.hypotheses.length > 0 ? (
            <div>
              <div className="section-title mb-3">Root Cause Analysis</div>
              <div className="space-y-2">
                {inv.hypotheses.map(hyp => (
                  <HypothesisCard
                    key={hyp.id}
                    hyp={hyp}
                    expanded={expandedHyps.has(hyp.id)}
                    onToggle={() => setExpandedHyps(s => {
                      const n = new Set(s);
                      n.has(hyp.id) ? n.delete(hyp.id) : n.add(hyp.id);
                      return n;
                    })}
                  />
                ))}
              </div>
            </div>
          ) : isActive ? (
            <div className="py-8 text-center">
              <Spinner size="md" />
              <p className="text-text-muted text-xs mt-3">Analyzing evidence…</p>
            </div>
          ) : (
            <EmptyState
              title="No hypotheses"
              description="Run the investigation to generate root cause hypotheses."
            />
          )}

          {/* AI Provider */}
          {inv.ai_provider_used && (
            <div className="pt-2 border-t border-border">
              <div className="text-xs text-text-muted">
                Analysis: {inv.ai_provider_used === 'amazon_bedrock' ? 'Amazon Bedrock' : 'Local Simulation'}
              </div>
            </div>
          )}
        </div>

        {/* Chat panel */}
        {showChat && (
          <div className="w-[280px] flex-shrink-0 border-l border-border flex flex-col animate-slide-in">
            <div className="px-4 py-3 border-b border-border flex items-center justify-between flex-shrink-0">
              <span className="text-xs font-semibold text-text-secondary">Investigation Assistant</span>
              <button onClick={() => setShowChat(false)} className="btn-ghost p-1">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <ChatPanel inv={inv} />
          </div>
        )}
      </div>

      {/* Remediation dialog */}
      {showRemediation && inv.remediation && (
        <RemediationDialog
          inv={inv}
          onClose={() => setShowRemediation(false)}
          onApprove={handleApprove}
        />
      )}
    </div>
  );
}
