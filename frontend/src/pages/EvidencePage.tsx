import React, { useEffect, useState } from 'react';
import { Database, Search, Filter, ChevronDown, ChevronRight, FileText, CheckCircle2, XCircle, Info, ExternalLink } from 'lucide-react';
import { getInvestigations, getEvidence } from '../services/api';
import type { Investigation, EvidenceItem } from '../types';
import { SeverityBadge } from '../components/shared';

export default function EvidencePage() {
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [selectedInvId, setSelectedInvId] = useState<string>('');
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingEvidence, setLoadingEvidence] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    getInvestigations()
      .then((invs) => {
        setInvestigations(invs);
        if (invs.length > 0) {
          setSelectedInvId(invs[0].id);
        }
      })
      .catch((err) => console.error('Failed to load investigations:', err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedInvId) {
      setEvidenceList([]);
      return;
    }
    setLoadingEvidence(true);
    getEvidence(selectedInvId)
      .then((items) => {
        setEvidenceList(items);
        if (items.length > 0) {
          setExpandedId(items[0].id);
        }
      })
      .catch((err) => {
        console.error('Failed to load evidence for investigation:', err);
        setEvidenceList([]);
      })
      .finally(() => setLoadingEvidence(false));
  }, [selectedInvId]);

  // Derived evidence types
  const evidenceTypes = Array.from(new Set(evidenceList.map(e => e.evidence_type))).filter(Boolean);

  const filteredEvidence = evidenceList.filter((item) => {
    const matchesSearch =
      searchQuery === '' ||
      item.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.detail.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.source.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = selectedType === 'all' || item.evidence_type === selectedType;
    const matchesSeverity = selectedSeverity === 'all' || item.severity === selectedSeverity;
    return matchesSearch && matchesType && matchesSeverity;
  });

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="w-6 h-6 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Evidence Explorer</h1>
          <p className="text-text-muted text-sm mt-1">
            Telemetry, log excerpts, traces, and runbook artifacts verified during automated investigations
          </p>
        </div>

        {/* Investigation Picker */}
        <div className="flex items-center gap-3">
          <label className="text-xs text-text-muted uppercase font-medium">Investigation:</label>
          <select
            value={selectedInvId}
            onChange={(e) => setSelectedInvId(e.target.value)}
            className="bg-bg-card border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-primary"
          >
            {investigations.map((inv) => (
              <option key={inv.id} value={inv.id}>
                {inv.service} · {new Date(inv.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ({inv.status})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-bg-card border border-border rounded-xl p-4 flex flex-wrap items-center gap-4">
        <div className="flex-1 min-w-[240px] relative">
          <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search evidence summaries, logs, details..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-bg-elevated border border-border rounded-lg pl-9 pr-4 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-primary"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-text-muted" />
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="bg-bg-elevated border border-border rounded-lg px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-accent-primary"
          >
            <option value="all">All Types</option>
            {evidenceTypes.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>

          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="bg-bg-elevated border border-border rounded-lg px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-accent-primary"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
        </div>

        <div className="text-xs text-text-muted ml-auto font-mono">
          Showing {filteredEvidence.length} of {evidenceList.length} items
        </div>
      </div>

      {/* Evidence Content */}
      {loadingEvidence ? (
        <div className="p-12 text-center">
          <div className="w-6 h-6 border-2 border-accent-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-text-muted">Loading telemetry and artifacts...</p>
        </div>
      ) : filteredEvidence.length === 0 ? (
        <div className="bg-bg-card border border-border rounded-xl p-12 text-center">
          <Database className="w-10 h-10 text-text-muted mx-auto mb-3 opacity-40" />
          <h3 className="text-base font-medium text-text-primary">No evidence items found</h3>
          <p className="text-sm text-text-muted mt-1">
            {investigations.length === 0
              ? 'No investigations have been executed yet.'
              : 'Try selecting another investigation or adjusting the filter criteria.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEvidence.map((item) => {
            const isExpanded = expandedId === item.id;
            return (
              <div
                key={item.id}
                className="bg-bg-card border border-border rounded-xl overflow-hidden transition-all duration-150 hover:border-border/80"
              >
                <div
                  onClick={() => setExpandedId(isExpanded ? null : item.id)}
                  className="p-4 flex items-start gap-3 cursor-pointer select-none"
                >
                  <button className="text-text-muted hover:text-text-primary mt-0.5">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </button>

                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-bg-elevated border border-border text-accent-primary">
                        {item.evidence_type}
                      </span>
                      <SeverityBadge severity={item.severity as any} />
                      <span className="text-xs text-text-muted font-mono">{item.source}</span>

                      {item.relevance === 'supporting' && (
                        <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40 ml-auto">
                          <CheckCircle2 className="w-3 h-3" />
                          Supports Root Cause
                        </span>
                      )}
                      {item.relevance === 'contradictory' && (
                        <span className="flex items-center gap-1 text-[11px] font-medium text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800/40 ml-auto">
                          <XCircle className="w-3 h-3" />
                          Contradicts Hypothesis
                        </span>
                      )}
                    </div>

                    <h4 className="text-sm font-medium text-text-primary">{item.summary}</h4>
                  </div>
                </div>

                {isExpanded && (
                  <div className="px-5 pb-5 pt-2 border-t border-border/60 bg-bg-elevated/30 space-y-4">
                    <div>
                      <h5 className="text-xs uppercase font-semibold text-text-muted mb-1.5">Analytical Detail</h5>
                      <div className="p-3 rounded-lg bg-bg-card border border-border font-mono text-xs text-text-secondary leading-relaxed whitespace-pre-wrap">
                        {item.detail}
                      </div>
                    </div>

                    {item.raw && Object.keys(item.raw).length > 0 && (
                      <div>
                        <h5 className="text-xs uppercase font-semibold text-text-muted mb-1.5">Raw Telemetry Payload</h5>
                        <pre className="p-3 rounded-lg bg-bg-main border border-border font-mono text-xs text-text-muted overflow-x-auto max-h-60">
                          {JSON.stringify(item.raw, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
