import axios from 'axios';
import type {
  Scenario, Service, Investigation, EvidenceItem, Hypothesis,
  RemediationProposal, VerificationResult, PostmortemReport, ProviderStatus
} from '../types';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

// Scenarios
export const getScenarios = (): Promise<Scenario[]> =>
  api.get('/scenarios').then(r => r.data);

// Services
export const getServices = (): Promise<Service[]> =>
  api.get('/services').then(r => r.data);

// Investigations
export const getInvestigations = (): Promise<Investigation[]> =>
  api.get('/investigations').then(r => r.data);

export const createInvestigation = (data: {
  incident_description: string;
  service: string;
  scenario_id: string;
  depth?: string;
}): Promise<Investigation> =>
  api.post('/investigations', data).then(r => r.data);

export const getInvestigation = (id: string): Promise<Investigation> =>
  api.get(`/investigations/${id}`).then(r => r.data);

export const runInvestigation = (id: string): Promise<{ message: string }> =>
  api.post(`/investigations/${id}/run`).then(r => r.data);

export const getEvidence = (id: string, filters?: { evidence_type?: string; severity?: string }): Promise<EvidenceItem[]> =>
  api.get(`/investigations/${id}/evidence`, { params: filters }).then(r => r.data);

export const getHypotheses = (id: string): Promise<Hypothesis[]> =>
  api.get(`/investigations/${id}/hypotheses`).then(r => r.data);

// Remediation
export const proposeRemediation = (id: string): Promise<RemediationProposal> =>
  api.post(`/investigations/${id}/remediation/propose`).then(r => r.data);

export const approveRemediation = (id: string, approved: boolean): Promise<Investigation> =>
  api.post(`/investigations/${id}/remediation/approve`, { approved }).then(r => r.data);

// Verification
export const verifyRecovery = (id: string): Promise<VerificationResult> =>
  api.post(`/investigations/${id}/verify`).then(r => r.data);

// Reports
export const getReport = (id: string): Promise<PostmortemReport> =>
  api.get(`/investigations/${id}/report`).then(r => r.data);

export const downloadReport = (id: string, format: 'json' | 'markdown' = 'json') =>
  api.get(`/investigations/${id}/report/download`, {
    params: { format },
    responseType: 'blob',
  }).then(r => {
    const url = window.URL.createObjectURL(new Blob([r.data]));
    const link = document.createElement('a');
    link.href = url;
    link.download = `report_${id.slice(0, 8)}.${format === 'markdown' ? 'md' : 'json'}`;
    link.click();
    window.URL.revokeObjectURL(url);
  });

export const archiveToS3 = (id: string) =>
  api.post(`/investigations/${id}/report/archive`).then(r => r.data);

// Chat
export const sendChatMessage = (investigationId: string, message: string): Promise<{ response: string; timestamp: string }> =>
  api.post('/chat', { investigation_id: investigationId, message }).then(r => r.data);

// Settings
export const getProviderStatus = (): Promise<ProviderStatus> =>
  api.get('/settings/provider').then(r => r.data);

export default api;
