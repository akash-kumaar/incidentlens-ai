import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, Play, ChevronDown } from 'lucide-react';
import { getScenarios, getServices, createInvestigation, runInvestigation } from '../services/api';
import type { Scenario, Service } from '../types';

const DEPTHS = [
  { id: 'quick', label: 'Quick', description: 'Essential checks only (~30s)' },
  { id: 'standard', label: 'Standard', description: 'Full evidence collection (~60s)' },
  { id: 'deep', label: 'Deep', description: 'Exhaustive analysis (~120s)' },
];

export default function NewInvestigationPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const preselectedScenario = location.state?.scenarioId;

  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    scenario_id: preselectedScenario ?? '',
    service: '',
    incident_description: '',
    depth: 'standard',
  });

  useEffect(() => {
    Promise.all([getScenarios(), getServices()])
      .then(([scens, svcs]) => {
        setScenarios(scens);
        setServices(svcs);
        // Auto-fill scenario data
        if (preselectedScenario) {
          const s = scens.find(sc => sc.id === preselectedScenario);
          if (s) {
            setForm(f => ({ ...f, service: s.service, incident_description: s.description }));
          }
        }
      })
      .catch(() => setError('Failed to load scenarios'))
      .finally(() => setLoading(false));
  }, []);

  const handleScenarioSelect = (id: string) => {
    const s = scenarios.find(sc => sc.id === id);
    if (s) {
      setForm(f => ({
        ...f,
        scenario_id: id,
        service: s.service,
        incident_description: s.description,
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.scenario_id) { setError('Please select a scenario'); return; }
    if (!form.incident_description.trim()) { setError('Please describe the incident'); return; }

    setSubmitting(true);
    try {
      const inv = await createInvestigation(form);
      await runInvestigation(inv.id);
      navigate(`/investigations/${inv.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Failed to start investigation');
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-border border-t-accent-primary rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl mx-auto animate-fade-in">
      <button
        onClick={() => navigate(-1)}
        className="btn-ghost flex items-center gap-1.5 mb-6 -ml-1"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Back
      </button>

      <div className="mb-6">
        <h1 className="text-lg font-semibold text-text-primary mb-1">Start Investigation</h1>
        <p className="text-text-muted text-sm">
          Select a scenario, describe the incident, and the investigation engine will
          collect evidence, rank hypotheses, and propose a safe remediation.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Scenario */}
        <div>
          <label className="block text-xs font-medium text-text-secondary mb-2">
            Scenario <span className="text-status-critical">*</span>
          </label>
          <div className="space-y-2">
            {scenarios.map(s => (
              <label
                key={s.id}
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                  form.scenario_id === s.id
                    ? 'border-accent-primary bg-accent-primary bg-opacity-5'
                    : 'border-border hover:border-border hover:bg-bg-elevated'
                }`}
              >
                <input
                  type="radio"
                  name="scenario"
                  value={s.id}
                  checked={form.scenario_id === s.id}
                  onChange={() => handleScenarioSelect(s.id)}
                  className="mt-0.5 accent-[#78E5C1]"
                />
                <div className="min-w-0">
                  <div className="text-text-primary text-sm font-medium">{s.name}</div>
                  <div className="text-text-muted text-xs mt-0.5">{s.description.slice(0, 100)}…</div>
                  <div className="flex gap-1.5 mt-1.5">
                    {s.tags.map(t => (
                      <span key={t} className="badge-muted text-xs">{t}</span>
                    ))}
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Service */}
        <div>
          <label className="block text-xs font-medium text-text-secondary mb-1.5">
            Affected Service <span className="text-status-critical">*</span>
          </label>
          <select
            value={form.service}
            onChange={e => setForm(f => ({ ...f, service: e.target.value }))}
            className="input"
            required
          >
            <option value="">Select a service…</option>
            {services.map(s => (
              <option key={s.id} value={s.id}>{s.name} ({s.id})</option>
            ))}
          </select>
        </div>

        {/* Description */}
        <div>
          <label className="block text-xs font-medium text-text-secondary mb-1.5">
            Incident Description <span className="text-status-critical">*</span>
          </label>
          <textarea
            value={form.incident_description}
            onChange={e => setForm(f => ({ ...f, incident_description: e.target.value }))}
            placeholder="Describe the incident in natural language…"
            className="input resize-none h-24"
            required
          />
        </div>

        {/* Depth */}
        <div>
          <label className="block text-xs font-medium text-text-secondary mb-2">
            Investigation Depth
          </label>
          <div className="flex gap-2">
            {DEPTHS.map(d => (
              <button
                key={d.id}
                type="button"
                onClick={() => setForm(f => ({ ...f, depth: d.id }))}
                className={`flex-1 px-3 py-2 rounded-md text-xs border transition-all text-left ${
                  form.depth === d.id
                    ? 'border-accent-primary bg-accent-primary bg-opacity-10 text-accent-primary'
                    : 'border-border text-text-muted hover:border-border hover:bg-bg-elevated'
                }`}
              >
                <div className="font-medium">{d.label}</div>
                <div className="opacity-70 mt-0.5">{d.description}</div>
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="px-3 py-2 rounded-md bg-status-critical bg-opacity-10 border border-status-critical border-opacity-20 text-status-critical text-xs">
            {error}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <button type="submit" className="btn-primary flex items-center gap-2" disabled={submitting}>
            {submitting ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-bg-main border-t-transparent rounded-full animate-spin" />
                Starting…
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" />
                Start Investigation
              </>
            )}
          </button>
          <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
