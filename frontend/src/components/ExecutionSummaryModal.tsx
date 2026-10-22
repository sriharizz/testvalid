import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Download,
  ShieldCheck,
  Lock,
  ArrowRight,
  X
} from 'lucide-react';

export interface StepRCA {
  step_id: string;
  scenario: string;
  failure_observation: string;
  root_cause_explanation: string;
  impact_assessment: 'CRITICAL' | 'MAJOR' | 'MINOR';
  capa_remediation: string;
}

export interface SummaryReportData {
  session_id: string;
  document_no: string;
  protocol_title: string;
  tester: string;
  execution_date_utc: string;
  total_steps: number;
  passed_count: number;
  failed_count: number;
  blocked_count: number;
  overall_status: 'PASS' | 'FAIL' | 'BLOCKED';
  acceptance_criteria_met: boolean;
  deviation_ids: string[];
  root_cause_analyses: StepRCA[];
  compliance_statement: string;
  archive_status?: string;
  manifest_sha256?: string | null;
}

interface ExecutionSummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  summary: SummaryReportData | null;
  onDownloadDocx: () => void;
  onDownloadEvidence: () => void;
  onArchive: () => Promise<any>;
}

export const ExecutionSummaryModal: React.FC<ExecutionSummaryModalProps> = ({
  isOpen,
  onClose,
  summary,
  onDownloadDocx,
  onDownloadEvidence,
  onArchive
}) => {
  const [isArchiving, setIsArchiving] = useState(false);
  const [archivedManifest, setArchivedManifest] = useState<string | null>(null);

  if (!isOpen || !summary) return null;

  const isPassed = summary.overall_status === 'PASS';

  const handleArchiveClick = async () => {
    setIsArchiving(true);
    try {
      const res = await onArchive();
      if (res && res.manifest && res.manifest.files) {
        setArchivedManifest(res.manifest.session_id);
      }
    } catch (e) {
      console.error('Archive error:', e);
    } finally {
      setIsArchiving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className={`px-6 py-4 flex items-center justify-between text-white ${
          isPassed ? 'bg-gradient-to-r from-emerald-600 to-teal-700' : 'bg-gradient-to-r from-rose-600 to-red-800'
        }`}>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-white/10 rounded-xl">
              {isPassed ? <CheckCircle2 className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-lg">Computer Systems Validation — Executive Summary</h2>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-white/20 uppercase tracking-wider">
                  {summary.overall_status}
                </span>
              </div>
              <p className="text-xs text-white/80">
                {summary.document_no} • {summary.execution_date_utc} • Tester: {summary.tester}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-white/20 text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* KPI Matrix Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-center">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Steps</span>
              <p className="text-2xl font-bold text-slate-800 mt-1">{summary.total_steps}</p>
            </div>
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 text-center">
              <span className="text-[11px] font-semibold text-emerald-600 uppercase tracking-wider">Passed</span>
              <p className="text-2xl font-bold text-emerald-700 mt-1">{summary.passed_count}</p>
            </div>
            <div className="bg-rose-50 border border-rose-200 rounded-xl p-3.5 text-center">
              <span className="text-[11px] font-semibold text-rose-600 uppercase tracking-wider">Failed / Blocked</span>
              <p className="text-2xl font-bold text-rose-700 mt-1">{summary.failed_count + summary.blocked_count}</p>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-3.5 text-center">
              <span className="text-[11px] font-semibold text-blue-600 uppercase tracking-wider">21 CFR Part 11</span>
              <p className="text-sm font-bold text-blue-700 mt-2 flex items-center justify-center gap-1">
                <ShieldCheck className="w-4 h-4 text-blue-600" />
                <span>Watermarked</span>
              </p>
            </div>
          </div>

          {/* AI Root-Cause Diagnostic Section (when failures occur) */}
          {summary.root_cause_analyses.length > 0 ? (
            <div className="border border-rose-200 bg-rose-50/50 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2 text-rose-800 font-bold text-sm">
                <AlertTriangle className="w-4 h-4 text-rose-600" />
                <span>AI Root-Cause Diagnostic & CAPA Recommendations</span>
              </div>
              <div className="space-y-3">
                {summary.root_cause_analyses.map((rca) => (
                  <div key={rca.step_id} className="bg-white border border-rose-200 rounded-lg p-3 text-xs space-y-1.5 shadow-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900">[{rca.step_id}] {rca.scenario}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        rca.impact_assessment === 'CRITICAL' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                      }`}>
                        Impact: {rca.impact_assessment}
                      </span>
                    </div>
                    <p className="text-slate-600">
                      <strong className="text-slate-800">Observed Discrepancy:</strong> {rca.failure_observation}
                    </p>
                    <p className="text-slate-700 bg-slate-50 p-2 rounded border border-slate-100">
                      <strong className="text-blue-900">AI Diagnostic Root Cause:</strong> {rca.root_cause_explanation}
                    </p>
                    <p className="text-emerald-700">
                      <strong>Recommended Corrective Action (CAPA):</strong> {rca.capa_remediation}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="border border-emerald-200 bg-emerald-50/40 rounded-xl p-4 flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              <div className="text-xs text-emerald-900">
                <span className="font-bold">100% Acceptance Criteria Met:</span> All {summary.total_steps} validation steps completed without discrepancies. Primary protocol Table 6 is pre-populated with formal sign-off approval.
              </div>
            </div>
          )}

          {/* Post-Approval Archival Manifest Box */}
          <div className="bg-slate-900 text-white rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-emerald-400" />
                <span className="text-sm font-bold">Post-Approval File Management & SHA-256 Indexing</span>
              </div>
              <p className="text-xs text-slate-400">
                Locks all executed protocols, companion dossiers, and stamped evidence into an immutable audit directory with SHA-256 manifests.
              </p>
              {archivedManifest && (
                <div className="text-[11px] text-emerald-300 font-mono">
                  ✅ Successfully Locked & Archived (Session: {archivedManifest})
                </div>
              )}
            </div>
            <button
              onClick={handleArchiveClick}
              disabled={isArchiving || Boolean(archivedManifest)}
              className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center space-x-1.5 transition-all shadow-md shrink-0 ${
                archivedManifest
                  ? 'bg-emerald-600 text-white cursor-default'
                  : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 active:scale-95'
              }`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span>{isArchiving ? 'Archiving...' : (archivedManifest ? 'Archived & Locked' : 'Approve & Archive')}</span>
            </button>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2 text-xs">
          <span className="text-slate-500 italic">21 CFR Part 11 / EU Annex 11 Electronic Validation</span>
          <div className="flex items-center space-x-2">
            <button
              onClick={onDownloadDocx}
              className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 font-semibold rounded-lg flex items-center gap-1.5 shadow-2xs"
            >
              <FileText className="w-3.5 h-3.5 text-blue-600" />
              <span>Download Protocol (.docx)</span>
            </button>
            <button
              onClick={onDownloadEvidence}
              className="px-3.5 py-1.5 bg-[#1d63dc] hover:bg-blue-600 text-white font-semibold rounded-lg flex items-center gap-1.5 shadow-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Evidence Dossier (.docx)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
