import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, Wifi, WifiOff } from 'lucide-react';
import { getProviderStatus } from '../services/api';
import type { ProviderStatus } from '../types';

interface Props {
  activeInvestigationId?: string;
}

export default function TopBar({ activeInvestigationId }: Props) {
  const [provider, setProvider] = useState<ProviderStatus | null>(null);

  useEffect(() => {
    getProviderStatus().then(setProvider).catch(() => null);
  }, []);

  const isDemo = !provider || provider.demo_mode;

  return (
    <header className="h-12 border-b border-border bg-bg-main flex items-center justify-between px-6 flex-shrink-0">
      <div className="flex items-center gap-3">
        {isDemo ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-status-warning bg-opacity-10 border border-status-warning border-opacity-20">
            <div className="w-1.5 h-1.5 rounded-full bg-status-warning" />
            <span className="text-status-warning text-xs font-medium tracking-wide">DEMO ENVIRONMENT</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-accent-primary bg-opacity-10 border border-accent-primary border-opacity-20">
            <div className="w-1.5 h-1.5 rounded-full bg-accent-primary" />
            <span className="text-accent-primary text-xs font-medium tracking-wide">AWS CONNECTED</span>
          </div>
        )}
        {activeInvestigationId && (
          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            <span>Active:</span>
            <span className="mono text-text-secondary">{activeInvestigationId.slice(0, 8)}</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-4 text-xs text-text-muted">
        {provider && (
          <div className="flex items-center gap-1.5">
            {provider.bedrock_configured ? (
              <CheckCircle className="w-3 h-3 text-accent-primary" />
            ) : (
              <WifiOff className="w-3 h-3" />
            )}
            <span>
              AI: {provider.provider === 'bedrock' && provider.bedrock_configured
                ? 'Amazon Bedrock'
                : 'Local Simulation'}
            </span>
          </div>
        )}
        {provider?.s3_configured && (
          <div className="flex items-center gap-1.5">
            <CheckCircle className="w-3 h-3 text-accent-primary" />
            <span>S3 Archival</span>
          </div>
        )}
      </div>
    </header>
  );
}
