import React, { useEffect, useState } from 'react';
import {
  FileText, Download, Cloud, CheckCircle, Clock, AlertTriangle,
  ArrowRight, ShieldCheck, ChevronRight, Share2, Layers, RefreshCw
} from 'lucide-react';
import { getInvestigations, getReport, downloadReport, archiveToS3 } from '../services/api';
import type { Investigation, PostmortemReport } from '../types';

export default function ReportsPage() {
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [selectedInv, setSelectedInv] = useState<Investigation | null>(null);
  const [report, setReport] = useState<PostmortemReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [archiveSuccess, setArchiveSuccess] = useState<string | null>(null);
  const [archiveError, setArchiveError] = useState<string | null>(null);

  useEffect(() => {
    getInvestigations()
      .then((invs) => {
        setInvestigations(invs);
        const firstWithReport = invs.find(i => i.report || i.status === 'completed');
        if (firstWithReport) {
          setSelectedInv(firstWithReport);
        } else if (invs.length > 0) {
          setSelectedInv(invs[0]);
        }
      })
      .catch((err) => console.error('Failed to load investigations:', err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedInv) {
      setReport(null);
      return;
    }
    setArchiveSuccess(null);
    setArchiveError(null);
    setLoadingReport(true);

    getReport(selectedInv.id)
      .then((rep) => setReport(rep))
      .catch((err) => {
        console.warn('Report not available yet for this investigation:', err);
        setReport(null);
      })
      .finally(() => setLoadingReport(false));
  }, [selectedInv]);

  const handleArchive = async () => {
    if (!selectedInv) return;
    setArchiving(true);
    setArchiveError(null);
    setArchiveSuccess(null);
    try {
      const res = await archiveToS3(selectedInv.id);
      setArchiveSuccess(`Archived successfully: ${res.s3_uri}`);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Archival failed. Verify AWS S3 credentials in Settings.';
      setArchiveError(msg);
    } finally {
      setArchiving(false);
    }
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
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Incident Postmortems</h1>
          <p className="text-text-muted text-sm mt-1">
            Automated retrospective reports with root cause timeline, prevention actions, and archival
          </p>
        </div>

        {report && selectedInv && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => downloadReport(selectedInv.id, 'markdown')}
              className="px-3 py-2 bg-bg-card border border-border text-text-secondary hover:text-text-primary text-xs font-medium rounded-lg hover:bg-bg-elevated transition flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Markdown</span>
            </button>
            <button
              onClick={() => downloadReport(selectedInv.id, 'json')}
              className="px-3 py-2 bg-bg-card border border-border text-text-secondary hover:text-text-primary text-xs font-medium rounded-lg hover:bg-bg-elevated transition flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              <span>JSON</span>
            </button>
            <button
              onClick={handleArchive}
              disabled={archiving}
              className="px-3.5 py-2 bg-accent-primary text-white text-xs font-medium rounded-lg hover:bg-blue-600 transition flex items-center gap-1.5 disabled:opacity-50"
            >
              <Cloud className="w-3.5 h-3.5" />
              <span>{archiving ? 'Archiving...' : 'Archive to S3'}</span>
            </button>
          </div>
        )}
      </div>

      {archiveSuccess && (
        <div className="p-3 bg-emerald-950/40 border border-emerald-800/50 rounded-lg text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{archiveSuccess}</span>
        </div>
      )}

      {archiveError && (
        <div className="p-3 bg-amber-950/40 border border-amber-800/50 rounded-lg text-xs text-amber-300 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span>{archiveError}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Investigation Selector */}
        <div className="lg:col-span-1 space-y-2">
          <h3 className="text-xs uppercase font-semibold text-text-muted px-2 mb-2">Investigations</h3>
          {investigations.length === 0 ? (
            <div className="p-4 bg-bg-card border border-border rounded-xl text-center text-xs text-text-muted">
              No investigations created yet.
            </div>
          ) : (
            investigations.map((inv) => {
              const isSelected = selectedInv?.id === inv.id;
              const hasReport = !!inv.report || inv.status === 'completed';

              return (
                <div
                  key={inv.id}
                  onClick={() => setSelectedInv(inv)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-bg-card border-accent-primary/60 ring-1 ring-accent-primary/40'
                      : 'bg-bg-card/60 border-border hover:bg-bg-card hover:border-border/80'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-text-primary capitalize">{inv.service}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                      hasReport ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-800/30' : 'bg-bg-elevated text-text-muted'
                    }`}>
                      {hasReport ? 'Ready' : inv.status}
                    </span>
                  </div>
                  <p className="text-xs text-text-muted mt-1 line-clamp-1">{inv.incident_description}</p>
                  <div className="text-[10px] text-text-muted mt-2 font-mono">
                    {new Date(inv.created_at).toLocaleDateString()} · {new Date(inv.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Report Viewer */}
        <div className="lg:col-span-3">
          {loadingReport ? (
            <div className="bg-bg-card border border-border rounded-xl p-12 text-center min-h-[400px] flex flex-col items-center justify-center">
              <RefreshCw className="w-6 h-6 border-2 border-accent-primary border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-sm text-text-muted">Compiling postmortem report...</p>
            </div>
          ) : !report ? (
            <div className="bg-bg-card border border-border rounded-xl p-12 text-center min-h-[400px] flex flex-col items-center justify-center">
              <FileText className="w-12 h-12 text-text-muted opacity-30 mb-3" />
              <h3 className="text-base font-medium text-text-primary">No report available for this incident</h3>
              <p className="text-sm text-text-muted mt-1 max-w-md">
                Postmortem reports are compiled automatically once the investigation reaches completion and verification is completed.
              </p>
            </div>
          ) : (
            <div className="bg-bg-card border border-border rounded-xl p-6 lg:p-8 space-y-8">
              {/* Report Header */}
              <div className="border-b border-border pb-6">
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-bg-elevated border border-border text-accent-primary">
                    INCIDENT POSTMORTEM
                  </span>
                  <span className="text-xs font-mono text-text-muted">ID: {report.incident_id.slice(0, 12)}</span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-red-950/50 text-red-400 border border-red-800/40 uppercase">
                    {report.severity}
                  </span>
                  <span className="text-xs text-text-muted ml-auto font-mono">
                    Generated: {new Date(report.generated_at).toLocaleString()}
                  </span>
                </div>
                <h2 className="text-xl font-semibold text-text-primary">
                  {report.service} Service Outage Retrospective
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4 pt-4 border-t border-border/50 text-xs">
                  <div>
                    <span className="text-text-muted block">Service</span>
                    <span className="text-text-primary font-medium">{report.service}</span>
                  </div>
                  <div>
                    <span className="text-text-muted block">Duration</span>
                    <span className="text-text-primary font-medium">35 minutes</span>
                  </div>
                  <div>
                    <span className="text-text-muted block">Resolution</span>
                    <span className="text-emerald-400 font-medium">{report.final_status}</span>
                  </div>
                  <div>
                    <span className="text-text-muted block">Environment</span>
                    <span className="text-text-primary font-medium">Production</span>
                  </div>
                </div>
              </div>

              {/* Executive Impact Summary */}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-text-muted">Executive Impact</h3>
                <p className="text-sm text-text-secondary leading-relaxed bg-bg-elevated/40 p-4 rounded-lg border border-border/80">
                  {report.impact_summary}
                </p>
              </div>

              {/* Timeline */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-text-muted">Incident Timeline</h3>
                <div className="space-y-2 relative border-l-2 border-border/70 ml-2 pl-4">
                  {report.timeline.map((evt, idx) => (
                    <div key={idx} className="relative group">
                      <div className="absolute -left-[21px] top-1.5 w-2.5 h-2.5 rounded-full bg-accent-primary ring-4 ring-bg-card" />
                      <div className="text-xs font-mono text-text-muted">
                        {new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </div>
                      <div className="text-sm font-medium text-text-primary">{evt.title}</div>
                      <div className="text-xs text-text-secondary mt-0.5">{evt.description}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Root Cause Assessment */}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-text-muted">Root Cause Assessment</h3>
                <div className="text-sm text-text-secondary leading-relaxed bg-bg-elevated/40 p-4 rounded-lg border border-border/80 whitespace-pre-wrap">
                  {report.root_cause_assessment}
                </div>
              </div>

              {/* Contributing Factors */}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-text-muted">Contributing Factors</h3>
                <ul className="list-disc list-inside space-y-1.5 text-sm text-text-secondary">
                  {report.contributing_factors.map((cf, idx) => (
                    <li key={idx} className="leading-relaxed">{cf}</li>
                  ))}
                </ul>
              </div>

              {/* Resolution & Remediation */}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-text-muted">Resolution Applied</h3>
                <div className="text-sm text-text-secondary leading-relaxed bg-emerald-950/20 p-4 rounded-lg border border-emerald-800/30">
                  {report.resolution}
                </div>
              </div>

              {/* What Went Well & What Could Improve */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-bg-elevated/40 border border-border/80 space-y-2">
                  <h4 className="text-xs uppercase font-semibold text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5" />
                    What Went Well
                  </h4>
                  <ul className="space-y-1.5 text-xs text-text-secondary">
                    {report.what_went_well.map((item, idx) => (
                      <li key={idx}>• {item}</li>
                    ))}
                  </ul>
                </div>

                <div className="p-4 rounded-lg bg-bg-elevated/40 border border-border/80 space-y-2">
                  <h4 className="text-xs uppercase font-semibold text-amber-400 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    What Could Improve
                  </h4>
                  <ul className="space-y-1.5 text-xs text-text-secondary">
                    {report.what_could_improve.map((item, idx) => (
                      <li key={idx}>• {item}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Follow-up Action Items */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-text-muted">Preventive Action Items</h3>
                <div className="divide-y divide-border/60 border border-border/80 rounded-lg overflow-hidden bg-bg-elevated/30">
                  {report.follow_up_actions.map((act, idx) => (
                    <div key={idx} className="p-3.5 flex items-start gap-3">
                      <span className={`text-[10px] uppercase font-semibold px-2 py-0.5 rounded border mt-0.5 ${
                        act.priority === 'high'
                          ? 'bg-red-950/50 text-red-300 border-red-800/40'
                          : 'bg-amber-950/50 text-amber-300 border-amber-800/40'
                      }`}>
                        {act.priority || 'MED'}
                      </span>
                      <div>
                        <div className="text-xs font-medium text-text-primary">{act.action}</div>
                        <div className="text-xs text-text-muted mt-0.5">{act.rationale}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
