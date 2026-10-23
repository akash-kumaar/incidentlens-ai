import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Filter } from 'lucide-react';
import { getInvestigations } from '../services/api';
import type { Investigation } from '../types';
import { StatusIndicator, SeverityBadge, EmptyState, Spinner } from '../components/shared';
import { formatDistanceToNow } from 'date-fns';

const STATUS_FILTERS = ['all', 'running', 'awaiting_approval', 'completed', 'failed'];

export default function InvestigationsListPage() {
  const navigate = useNavigate();
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    getInvestigations()
      .then(setInvestigations)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = investigations.filter(inv => {
    const matchesSearch =
      !search ||
      inv.incident_description.toLowerCase().includes(search.toLowerCase()) ||
      inv.service.includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || inv.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="p-6 max-w-5xl mx-auto animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Investigations</h1>
          <p className="text-text-muted text-xs mt-0.5">{investigations.length} total</p>
        </div>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={() => navigate('/investigations/new')}
        >
          <Plus className="w-4 h-4" /> New Investigation
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" />
          <input
            className="input pl-8"
            placeholder="Search investigations…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-1">
          {STATUS_FILTERS.map(f => (
            <button
              key={f}
              className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                statusFilter === f
                  ? 'border-accent-primary text-accent-primary bg-accent-primary bg-opacity-10'
                  : 'border-border text-text-muted hover:text-text-secondary hover:bg-bg-elevated'
              }`}
              onClick={() => setStatusFilter(f)}
            >
              {f === 'all' ? 'All' : f.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <Spinner size="lg" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title={search || statusFilter !== 'all' ? 'No matching investigations' : 'No investigations yet'}
          description={
            search || statusFilter !== 'all'
              ? 'Try adjusting your search or filters.'
              : 'Start an investigation to inspect service health, correlate evidence, and identify root causes.'
          }
          action={
            !search && statusFilter === 'all' ? (
              <button className="btn-primary" onClick={() => navigate('/investigations/new')}>
                Start investigation
              </button>
            ) : undefined
          }
        />
      ) : (
        <div className="card divide-y divide-border">
          {filtered.map(inv => (
            <button
              key={inv.id}
              className="w-full text-left px-5 py-4 hover:bg-bg-elevated transition-colors group"
              onClick={() => navigate(`/investigations/${inv.id}`)}
            >
              <div className="flex items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="mono text-text-muted text-xs">{inv.id.slice(0, 8)}</span>
                    <span className="mono text-text-secondary text-xs">{inv.service}</span>
                  </div>
                  <p className="text-text-primary text-sm group-hover:text-accent-primary transition-colors truncate font-medium">
                    {inv.incident_description}
                  </p>
                  <div className="flex items-center gap-4 mt-2">
                    <StatusIndicator status={inv.status} />
                    {inv.hypotheses[0] && (
                      <span className="text-xs text-text-muted truncate">
                        {inv.hypotheses[0].title.slice(0, 50)}
                        {inv.hypotheses[0].title.length > 50 ? '…' : ''}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex-shrink-0 text-right">
                  <div className="text-text-muted text-xs">
                    {formatDistanceToNow(new Date(inv.created_at), { addSuffix: true })}
                  </div>
                  <div className="mt-1">
                    <span className={`badge ${
                      inv.progress === 100 ? 'badge-success' :
                      inv.status === 'failed' ? 'badge-critical' : 'badge-info'
                    }`}>
                      {inv.progress}%
                    </span>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
