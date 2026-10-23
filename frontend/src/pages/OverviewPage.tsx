import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, CheckCircle, Server, Activity, ArrowRight, Clock, Plus } from 'lucide-react';
import { getInvestigations, getScenarios } from '../services/api';
import type { Investigation, Scenario } from '../types';
import { StatusIndicator, SeverityBadge } from '../components/shared';
import { formatDistanceToNow } from 'date-fns';

function MetricCard({ value, label, sub, color }: {
  value: string | number; label: string; sub?: string; color?: string
}) {
  return (
    <div className="card px-5 py-4">
      <div className={`text-2xl font-semibold mb-0.5 ${color ?? 'text-text-primary'}`}>{value}</div>
      <div className="text-text-secondary text-xs">{label}</div>
      {sub && <div className="text-text-muted text-xs mt-0.5">{sub}</div>}
    </div>
  );
}

export default function OverviewPage() {
  const navigate = useNavigate();
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getInvestigations(), getScenarios()])
      .then(([invs, scens]) => {
        setInvestigations(invs);
        setScenarios(scens);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  const openCount = investigations.filter(i => !['completed', 'failed'].includes(i.status)).length;
  const completedCount = investigations.filter(i => i.status === 'completed').length;
  const criticalFindings = investigations.filter(i =>
    i.hypotheses.some(h => h.confidence === 'strongly_supported')
  ).length;
  const servicesAffected = new Set(investigations.map(i => i.service)).size;

  const recent = investigations.slice(0, 5);

  // Build a simple activity feed from investigations
  const activityItems = investigations.flatMap(inv =>
    inv.tool_history.filter(t => t.status === 'completed').map(t => ({
      time: t.completed_at ?? inv.updated_at,
      text: `${t.display_name} — ${inv.service}`,
      type: 'tool',
    }))
  ).sort((a, b) => b.time.localeCompare(a.time)).slice(0, 8);

  return (
    <div className="p-6 max-w-6xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-xl font-semibold text-text-primary mb-1">
            {greeting}. Let's investigate.
          </h1>
          <p className="text-text-muted text-sm">
            IncidentLens AI — evidence-driven incident investigation workspace.
          </p>
        </div>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={() => navigate('/investigations/new')}
        >
          <Plus className="w-4 h-4" />
          Start investigation
        </button>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-3 mb-8">
        <MetricCard
          value={openCount}
          label="Open incidents"
          color={openCount > 0 ? 'text-status-warning' : 'text-text-primary'}
        />
        <MetricCard
          value={criticalFindings}
          label="Critical findings"
          color={criticalFindings > 0 ? 'text-status-critical' : 'text-text-primary'}
        />
        <MetricCard value={completedCount} label="Investigations completed" />
        <MetricCard value={servicesAffected || scenarios.length} label="Services in scope" />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Recent investigations */}
        <div className="col-span-2">
          <div className="flex items-center justify-between mb-3">
            <span className="section-title">Recent Investigations</span>
            <button
              className="btn-ghost text-xs"
              onClick={() => navigate('/investigations')}
            >
              View all <ArrowRight className="w-3 h-3 inline ml-1" />
            </button>
          </div>

          {loading ? (
            <div className="card p-8 flex justify-center">
              <div className="w-5 h-5 border-2 border-border border-t-accent-primary rounded-full animate-spin" />
            </div>
          ) : recent.length === 0 ? (
            <div className="card p-8 text-center">
              <Activity className="w-8 h-8 text-text-muted mx-auto mb-3 opacity-40" />
              <p className="text-text-secondary text-sm font-medium mb-1">No investigations yet</p>
              <p className="text-text-muted text-xs mb-4">
                Start an investigation to inspect service health and identify root causes.
              </p>
              <button className="btn-primary" onClick={() => navigate('/investigations/new')}>
                Start investigation
              </button>
            </div>
          ) : (
            <div className="card divide-y divide-border">
              {recent.map(inv => (
                <button
                  key={inv.id}
                  className="w-full text-left px-4 py-3 hover:bg-bg-elevated transition-colors group"
                  onClick={() => navigate(`/investigations/${inv.id}`)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="text-text-primary text-sm truncate font-medium group-hover:text-accent-primary transition-colors">
                        {inv.incident_description.length > 70
                          ? inv.incident_description.slice(0, 70) + '…'
                          : inv.incident_description}
                      </div>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="mono text-text-muted">{inv.service}</span>
                        <StatusIndicator status={inv.status} />
                      </div>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <div className="text-text-muted text-xs">
                        {formatDistanceToNow(new Date(inv.created_at), { addSuffix: true })}
                      </div>
                      {inv.hypotheses[0] && (
                        <div className="text-xs mt-1 text-text-muted truncate max-w-[120px]">
                          {inv.hypotheses[0].confidence.replace(/_/g, ' ')}
                        </div>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Current incidents (scenarios as demo data) */}
          {scenarios.length > 0 && (
            <div className="mt-6">
              <div className="section-title mb-3">Available Scenarios</div>
              <div className="space-y-2">
                {scenarios.map(s => (
                  <div key={s.id} className="card px-4 py-3 flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="text-text-secondary text-sm font-medium truncate">{s.name}</div>
                      <div className="text-text-muted text-xs truncate mt-0.5">{s.description.slice(0, 80)}…</div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <SeverityBadge severity={s.severity} />
                      <button
                        className="btn-ghost"
                        onClick={() => navigate('/investigations/new', { state: { scenarioId: s.id } })}
                      >
                        Investigate
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Activity Timeline */}
        <div>
          <div className="section-title mb-3">Activity Timeline</div>
          <div className="card p-4">
            {activityItems.length === 0 ? (
              <div className="text-center py-6">
                <Clock className="w-6 h-6 text-text-muted mx-auto mb-2 opacity-40" />
                <p className="text-text-muted text-xs">No activity yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {activityItems.map((item, i) => (
                  <div key={i} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-1.5 h-1.5 rounded-full bg-accent-primary mt-1 flex-shrink-0" />
                      {i < activityItems.length - 1 && (
                        <div className="w-px flex-1 bg-border mt-1" />
                      )}
                    </div>
                    <div className="pb-3 min-w-0">
                      <div className="text-text-secondary text-xs truncate">{item.text}</div>
                      <div className="mono text-text-muted mt-0.5">
                        {formatDistanceToNow(new Date(item.time), { addSuffix: true })}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
