import React, { useEffect, useState } from 'react';
import {
  Settings, Cpu, Cloud, ShieldCheck, CheckCircle2, AlertCircle,
  RefreshCw, Terminal, ExternalLink, Key, HardDrive
} from 'lucide-react';
import { getProviderStatus } from '../services/api';
import type { ProviderStatus } from '../types';

export default function SettingsPage() {
  const [status, setStatus] = useState<ProviderStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStatus = () => {
    setRefreshing(true);
    getProviderStatus()
      .then((st) => setStatus(st))
      .catch((err) => console.error('Failed to get provider status:', err))
      .finally(() => {
        setLoading(false);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="w-6 h-6 border-2 border-accent-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">System Settings & Integrations</h1>
          <p className="text-text-muted text-sm mt-1">
            Configure AWS Bedrock foundation models, S3 cold storage archives, and local simulation runtime
          </p>
        </div>
        <button
          onClick={fetchStatus}
          disabled={refreshing}
          className="px-3.5 py-2 bg-bg-card border border-border text-text-secondary hover:text-text-primary text-xs font-medium rounded-lg hover:bg-bg-elevated transition flex items-center gap-2"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          <span>Refresh Status</span>
        </button>
      </div>

      {/* Provider Status Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* AI Provider */}
        <div className="bg-bg-card border border-border rounded-xl p-6 space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-bg-elevated border border-border text-accent-primary">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-medium text-text-primary">AI Inference Engine</h3>
                <span className="text-xs text-text-muted">Amazon Bedrock or Local Rule Engine</span>
              </div>
            </div>
            {status?.bedrock_configured ? (
              <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-400 bg-emerald-950/40 px-2.5 py-1 rounded-full border border-emerald-800/40">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Connected
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-medium text-amber-400 bg-amber-950/40 px-2.5 py-1 rounded-full border border-amber-800/40">
                <AlertCircle className="w-3.5 h-3.5" />
                Local Demo Mode
              </span>
            )}
          </div>

          <div className="divide-y divide-border/60 text-xs">
            <div className="py-2.5 flex justify-between">
              <span className="text-text-muted">Active Provider</span>
              <span className="font-mono text-text-primary capitalize">{status?.provider || 'local'}</span>
            </div>
            <div className="py-2.5 flex justify-between">
              <span className="text-text-muted">Bedrock Region</span>
              <span className="font-mono text-text-primary">{status?.bedrock_region || 'us-east-1 (Default)'}</span>
            </div>
            <div className="py-2.5 flex justify-between">
              <span className="text-text-muted">Foundation Model</span>
              <span className="font-mono text-text-primary">{status?.bedrock_model || 'Claude 3.5 Sonnet'}</span>
            </div>
            <div className="py-2.5 flex justify-between">
              <span className="text-text-muted">Status Message</span>
              <span className="font-mono text-text-secondary">{status?.bedrock_status}</span>
            </div>
          </div>
        </div>

        {/* AWS S3 cold storage */}
        <div className="bg-bg-card border border-border rounded-xl p-6 space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-bg-elevated border border-border text-accent-primary">
                <Cloud className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-medium text-text-primary">AWS S3 Cold Archive</h3>
                <span className="text-xs text-text-muted">Durable postmortem artifact storage</span>
              </div>
            </div>
            {status?.s3_configured ? (
              <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-400 bg-emerald-950/40 px-2.5 py-1 rounded-full border border-emerald-800/40">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Bucket Configured
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-medium text-text-muted bg-bg-elevated px-2.5 py-1 rounded-full border border-border">
                Optional / Disabled
              </span>
            )}
          </div>

          <div className="divide-y divide-border/60 text-xs">
            <div className="py-2.5 flex justify-between">
              <span className="text-text-muted">Configured Bucket</span>
              <span className="font-mono text-text-primary">{status?.s3_bucket || 'None (Local In-Memory)'}</span>
            </div>
            <div className="py-2.5 flex justify-between">
              <span className="text-text-muted">Archival Status</span>
              <span className="font-mono text-text-secondary">{status?.s3_status}</span>
            </div>
            <div className="py-2.5 flex justify-between">
              <span className="text-text-muted">Download Format</span>
              <span className="font-mono text-text-primary">Markdown (.md) & JSON</span>
            </div>
            <div className="py-2.5 flex justify-between">
              <span className="text-text-muted">Encryption</span>
              <span className="font-mono text-text-primary">AES-256 Server-Side</span>
            </div>
          </div>
        </div>
      </div>

      {/* Configuration Guide */}
      <div className="bg-bg-card border border-border rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-accent-primary" />
          <h3 className="text-base font-medium text-text-primary">Environment Variables</h3>
        </div>
        <p className="text-xs text-text-muted">
          IncidentLens AI functions out-of-the-box in local demo mode with 3 realistic pre-seeded incidents.
          To hook into your real AWS Bedrock or S3 environment, configure these environment variables in your backend:
        </p>

        <div className="p-4 bg-bg-main border border-border rounded-lg font-mono text-xs text-text-secondary space-y-2 overflow-x-auto">
          <div><span className="text-text-muted"># Set AI provider to bedrock</span></div>
          <div><span className="text-accent-primary">AI_PROVIDER</span>=bedrock</div>
          <div><span className="text-accent-primary">AWS_REGION</span>=us-east-1</div>
          <div><span className="text-accent-primary">BEDROCK_MODEL_ID</span>=anthropic.claude-3-5-sonnet-20241022-v2:0</div>
          <div className="pt-2"><span className="text-text-muted"># Optional AWS S3 archival bucket</span></div>
          <div><span className="text-accent-primary">S3_BUCKET</span>=my-incident-reports-bucket</div>
          <div className="pt-2"><span className="text-text-muted"># AWS credentials (or use IAM role)</span></div>
          <div><span className="text-accent-primary">AWS_ACCESS_KEY_ID</span>=&lt;your-access-key-id&gt;</div>
          <div><span className="text-accent-primary">AWS_SECRET_ACCESS_KEY</span>=&lt;your-secret-access-key&gt;</div>
        </div>
      </div>

      {/* Architecture & Safety Guardrails */}
      <div className="bg-bg-card border border-border rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          <h3 className="text-base font-medium text-text-primary">Autonomous Safety Guardrails</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3.5 rounded-lg bg-bg-elevated border border-border space-y-1">
            <span className="font-semibold text-text-primary block">Human-in-the-Loop</span>
            <p className="text-text-muted">
              Remediations require explicit engineer approval before rollback or resource adjustments execute.
            </p>
          </div>
          <div className="p-3.5 rounded-lg bg-bg-elevated border border-border space-y-1">
            <span className="font-semibold text-text-primary block">Pre/Post Verification</span>
            <p className="text-text-muted">
              Every action runs an automated health verification checkpoint to confirm telemetry recovery.
            </p>
          </div>
          <div className="p-3.5 rounded-lg bg-bg-elevated border border-border space-y-1">
            <span className="font-semibold text-text-primary block">Audit Trail</span>
            <p className="text-text-muted">
              Complete timeline events, diagnostic tool traces, and hypothesis confidences are permanently recorded.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
