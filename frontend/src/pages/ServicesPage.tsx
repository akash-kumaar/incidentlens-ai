import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Server, Activity, ArrowRight, ShieldCheck, Cpu, Code2, Users, Layers, AlertCircle } from 'lucide-react';
import { getServices, getInvestigations, getScenarios } from '../services/api';
import type { Service, Investigation, Scenario } from '../types';
import { StatusIndicator } from '../components/shared';

export default function ServicesPage() {
  const navigate = useNavigate();
  const [services, setServices] = useState<Service[]>([]);
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedService, setSelectedService] = useState<Service | null>(null);

  useEffect(() => {
    Promise.all([getServices(), getInvestigations(), getScenarios()])
      .then(([srvs, invs, scns]) => {
        setServices(srvs);
        setInvestigations(invs);
        setScenarios(scns);
        if (srvs.length > 0) setSelectedService(srvs[0]);
      })
      .catch((err) => console.error('Failed to load services:', err))
      .finally(() => setLoading(false));
  }, []);

  const getServiceStats = (serviceId: string) => {
    const serviceInvs = investigations.filter(i => i.service === serviceId);
    const activeInvs = serviceInvs.filter(i => !['completed', 'failed'].includes(i.status));
    const serviceScenarios = scenarios.filter(s => s.service === serviceId);
    return {
      total: serviceInvs.length,
      active: activeInvs.length,
      scenarios: serviceScenarios,
      health: activeInvs.length > 0 ? 'degraded' : 'healthy',
    };
  };

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Services Catalog</h1>
          <p className="text-text-muted text-sm mt-1">
            Production microservices monitored by IncidentLens autonomous diagnostics
          </p>
        </div>
        <button
          onClick={() => navigate('/investigations/new')}
          className="px-4 py-2 bg-accent-primary text-white text-sm font-medium rounded-lg hover:bg-blue-600 transition flex items-center gap-2 shadow-sm"
        >
          <Activity className="w-4 h-4" />
          <span>New Diagnostic</span>
        </button>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Services List */}
        <div className="lg:col-span-2 space-y-4">
          {services.map((service) => {
            const stats = getServiceStats(service.id);
            const isSelected = selectedService?.id === service.id;

            return (
              <div
                key={service.id}
                onClick={() => setSelectedService(service)}
                className={`p-5 rounded-xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-bg-card border-accent-primary/60 ring-1 ring-accent-primary/40 shadow-md'
                    : 'bg-bg-card/70 border-border hover:border-border/80 hover:bg-bg-card'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3.5">
                    <div className="p-2.5 rounded-lg bg-bg-elevated border border-border text-accent-primary">
                      <Server className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2.5">
                        <h3 className="text-base font-medium text-text-primary">{service.name}</h3>
                        <span className="text-xs font-mono text-text-muted bg-bg-elevated px-2 py-0.5 rounded border border-border">
                          {service.id}
                        </span>
                        {stats.active > 0 ? (
                          <span className="flex items-center gap-1.5 text-xs font-medium text-red-400 bg-red-950/40 px-2 py-0.5 rounded border border-red-800/50">
                            <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
                            {stats.active} Active Incident{stats.active > 1 ? 's' : ''}
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-950/30 px-2 py-0.5 rounded border border-emerald-800/40">
                            <ShieldCheck className="w-3.5 h-3.5" />
                            Healthy
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-text-secondary mt-1 line-clamp-2">
                        {service.description}
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/investigations/new?service=${service.id}`);
                    }}
                    className="flex-shrink-0 text-xs text-accent-primary hover:text-blue-300 font-medium flex items-center gap-1 py-1.5 px-3 rounded bg-accent-primary/10 hover:bg-accent-primary/20 transition"
                  >
                    Diagnose
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="mt-4 pt-3 border-t border-border/60 flex items-center gap-6 text-xs text-text-muted">
                  <div className="flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5 text-text-muted" />
                    <span>Team: <strong className="text-text-secondary capitalize">{service.team}</strong></span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Code2 className="w-3.5 h-3.5 text-text-muted" />
                    <span>Stack: <strong className="text-text-secondary">{service.language} ({service.framework})</strong></span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-text-muted" />
                    <span>Env: <strong className="text-text-secondary capitalize">{service.environment}</strong></span>
                  </div>
                  <div className="ml-auto text-text-muted">
                    <span>{stats.total} total investigations</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Service Detail Panel */}
        <div className="bg-bg-card border border-border rounded-xl p-6 h-fit sticky top-24 space-y-6">
          {selectedService ? (
            <>
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase tracking-wider text-text-muted font-semibold">Service Profile</span>
                  <span className="text-xs font-mono text-accent-primary">{selectedService.id}</span>
                </div>
                <h2 className="text-lg font-semibold text-text-primary mt-1">{selectedService.name}</h2>
                <p className="text-sm text-text-secondary mt-2 leading-relaxed">
                  {selectedService.description}
                </p>
              </div>

              <div className="space-y-3 pt-4 border-t border-border">
                <h4 className="text-xs uppercase tracking-wider text-text-muted font-semibold">Metadata</h4>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-2.5 rounded-lg bg-bg-elevated border border-border">
                    <span className="text-text-muted block">Runtime</span>
                    <span className="text-text-primary font-medium mt-0.5 block">{selectedService.language}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-bg-elevated border border-border">
                    <span className="text-text-muted block">Framework</span>
                    <span className="text-text-primary font-medium mt-0.5 block">{selectedService.framework}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-bg-elevated border border-border">
                    <span className="text-text-muted block">Owner Team</span>
                    <span className="text-text-primary font-medium mt-0.5 block capitalize">{selectedService.team}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-bg-elevated border border-border">
                    <span className="text-text-muted block">Environment</span>
                    <span className="text-text-primary font-medium mt-0.5 block capitalize">{selectedService.environment}</span>
                  </div>
                </div>
              </div>

              {/* Known Scenarios */}
              <div className="space-y-3 pt-4 border-t border-border">
                <h4 className="text-xs uppercase tracking-wider text-text-muted font-semibold">Simulated Failure Scenarios</h4>
                <div className="space-y-2">
                  {scenarios.filter(s => s.service === selectedService.id).map(scn => (
                    <div
                      key={scn.id}
                      onClick={() => navigate(`/investigations/new?scenario=${scn.id}&service=${selectedService.id}`)}
                      className="p-3 rounded-lg bg-bg-elevated/70 border border-border hover:border-accent-primary/50 transition cursor-pointer group"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-text-primary group-hover:text-accent-primary transition">
                          {scn.name}
                        </span>
                        <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-red-950/60 text-red-300 border border-red-800/40">
                          {scn.severity}
                        </span>
                      </div>
                      <p className="text-xs text-text-muted mt-1 line-clamp-2">{scn.description}</p>
                    </div>
                  ))}
                  {scenarios.filter(s => s.service === selectedService.id).length === 0 && (
                    <div className="text-xs text-text-muted italic">No predefined scenarios for this service.</div>
                  )}
                </div>
              </div>

              {/* Quick Action Button */}
              <button
                onClick={() => navigate(`/investigations/new?service=${selectedService.id}`)}
                className="w-full py-2.5 px-4 bg-accent-primary text-white text-sm font-medium rounded-lg hover:bg-blue-600 transition flex items-center justify-center gap-2 shadow-sm"
              >
                <Activity className="w-4 h-4" />
                <span>Launch New Investigation</span>
              </button>
            </>
          ) : (
            <div className="text-center text-text-muted text-sm py-12">
              Select a service to view full diagnostics profile
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
