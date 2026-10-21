import React from 'react';
import { ProtocolStep } from '../types';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Clock,
  ListOrdered,
  Zap,
  Camera,
  ZoomIn,
} from 'lucide-react';

interface MiddleSequencePaneProps {
  steps: ProtocolStep[];
  selectedStepId: string | null;
  onSelectStep: (stepId: string) => void;
  documentShortCode: string;
  isAuthoring?: boolean;
  onExecute: () => void;
  isExecuting: boolean;
  onOpenLightbox?: (step: ProtocolStep, type?: 'form' | 'modal' | 'combined', overrideUrl?: string) => void;
}

export const MiddleSequencePane: React.FC<MiddleSequencePaneProps> = ({
  steps,
  selectedStepId,
  onSelectStep,
  documentShortCode,
  isAuthoring,
  onExecute,
  isExecuting,
  onOpenLightbox,
}) => {
  const executedCount = steps.filter((s) => s.status === 'PASS' || s.status === 'FAIL').length;

  return (
    <section className="w-[440px] xl:w-[480px] flex-shrink-0 flex flex-col p-3 border-r border-slate-200 bg-[#f8fafc] h-[calc(100vh-3.5rem)] overflow-hidden select-none">
      {/* Header */}
      <div className="pb-2">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800 truncate">
          LIVE TEST SEQUENCE (Connected Series {documentShortCode ? `— ${documentShortCode}` : ''})
        </h2>
        <div className="h-0.5 w-12 bg-[#1d63dc] rounded-full mt-1" />
      </div>

      {/* Prominent Playwright Live Execution CTA Banner */}
      {steps.length > 0 && (
        <div className="mb-2.5">
          <button
            type="button"
            onClick={onExecute}
            disabled={isExecuting}
            className={`w-full py-2.5 px-3.5 rounded-xl font-bold text-xs flex items-center justify-between shadow-md transition-all ${
              isExecuting
                ? 'bg-blue-800 text-blue-200 cursor-not-allowed animate-pulse shadow-blue-500/20'
                : 'bg-gradient-to-r from-[#1d63dc] via-blue-600 to-indigo-600 hover:from-blue-600 hover:to-[#1d63dc] text-white hover:shadow-blue-500/25 active:scale-[0.99]'
            }`}
            title="Execute serial Playwright test automation against https://mpv-two.vercel.app and populate document"
          >
            <div className="flex items-center space-x-2">
              {isExecuting ? (
                <Loader2 className="w-4 h-4 animate-spin text-cyan-300" />
              ) : (
                <Zap className="w-4 h-4 fill-amber-300 text-amber-300" />
              )}
              <span className="text-left font-semibold">
                {isExecuting
                  ? `Automating Protocol (${executedCount}/${steps.length})...`
                  : 'Run Full Protocol Automation'}
              </span>
            </div>
            <span className="text-[10px] bg-white/20 px-2.5 py-0.5 rounded-full font-mono">
              {steps.length} Steps
            </span>
          </button>
        </div>
      )}

      {/* When no steps are loaded */}
      {steps.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
          <div className="w-14 h-14 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center justify-center text-slate-400 mb-3">
            <ListOrdered className="w-7 h-7 stroke-[1.5]" />
          </div>
          <h3 className="text-xs font-bold text-slate-700">
            {isAuthoring ? 'Extracting Test Steps...' : 'No Test Steps Loaded'}
          </h3>
          <p className="text-[11px] text-slate-500 max-w-[240px] mt-1 leading-relaxed">
            {isAuthoring
              ? 'Parsing tables, scenarios, and screenshot checkpoints from your document...'
              : 'Upload your validation protocol (.docx) above to extract test sequences dynamically.'}
          </p>
        </div>
      ) : (
        /* Step Cards List */
        <div className="flex-1 overflow-y-auto pr-1 space-y-2.5 pt-1">
          {steps.map((step, idx) => {
            const isSelected = step.step_id === selectedStepId;
            const stepNumber = idx + 1;

            // Status Badge rendering
            let statusBadge = (
              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200 flex items-center space-x-1">
                <Clock className="w-3 h-3 text-slate-400" />
                <span>Queued</span>
              </span>
            );

            if (step.status === 'PASS') {
              const secStr = step.latency_ms ? `${(step.latency_ms / 1000).toFixed(1)}s` : '1.2s';
              statusBadge = (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center space-x-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  <span>PASS - {secStr}</span>
                </span>
              );
            } else if (step.status === 'FAIL') {
              const secStr = step.latency_ms ? `${(step.latency_ms / 1000).toFixed(1)}s` : '1.4s';
              statusBadge = (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-50 text-red-700 border border-red-200 flex items-center space-x-1">
                  <XCircle className="w-3 h-3 text-red-600" />
                  <span>FAIL - {secStr}</span>
                </span>
              );
            } else if (step.status === 'BLOCKED') {
              statusBadge = (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200 flex items-center space-x-1">
                  <AlertTriangle className="w-3 h-3 text-amber-600" />
                  <span>BLOCKED</span>
                </span>
              );
            } else if (step.status === 'EXECUTING') {
              statusBadge = (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-300 animate-pulse flex items-center space-x-1">
                  <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
                  <span>Executing...</span>
                </span>
              );
            }

            return (
              <div
                key={step.step_id}
                onClick={() => onSelectStep(step.step_id)}
                className={`relative rounded-xl p-3 cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-blue-50/50 border-2 border-[#1d63dc] shadow-md shadow-blue-500/10'
                    : 'bg-white border border-slate-200 hover:border-slate-300 hover:shadow-xs'
                }`}
              >
                {/* Connector Line behind badge */}
                {idx < steps.length - 1 && (
                  <div className="absolute left-6 top-10 bottom-[-16px] w-0.5 bg-slate-200 -z-0" />
                )}

                <div className="flex items-start space-x-3 relative z-10">
                  {/* Number Badge */}
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 ${
                      isSelected
                        ? 'bg-[#1d63dc] text-white shadow-sm'
                        : step.status === 'PASS'
                        ? 'bg-emerald-600 text-white'
                        : 'bg-slate-200 text-slate-600'
                    }`}
                  >
                    {stepNumber}
                  </div>

                  {/* Card Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-xs font-bold text-slate-800">
                        {step.step_id}
                      </span>
                      {statusBadge}
                    </div>

                    <h4 className="text-xs font-semibold text-slate-800 leading-snug line-clamp-1">
                      {step.scenario}
                    </h4>

                    <p className="text-[11px] text-slate-500 line-clamp-2 mt-1 leading-normal">
                      {step.procedure}
                    </p>

                    {/* Separated Evidence Screenshots Container */}
                    {(step.form_screenshot_url || step.modal_screenshot_url || step.screenshot_url) && (
                      <div className="mt-2.5 pt-2 border-t border-slate-200/90">
                        <div className="text-[10px] font-bold text-slate-700 mb-1.5 flex items-center justify-between">
                          <span className="flex items-center gap-1 text-slate-700">
                            <Camera className="w-3 h-3 text-cyan-600" />
                            Evidence:
                          </span>
                          <span className="text-[9.5px] text-blue-600 font-semibold flex items-center gap-0.5">
                            <ZoomIn className="w-2.5 h-2.5" /> Click to Zoom
                          </span>
                        </div>

                        {step.form_screenshot_url && step.modal_screenshot_url ? (
                          <div className="grid grid-cols-2 gap-2">
                            {/* 1. Form Populated */}
                            <div
                              onClick={(e) => {
                                e.stopPropagation();
                                onOpenLightbox?.(step, 'form', step.form_screenshot_url!);
                              }}
                              className="bg-white border-2 border-blue-200 hover:border-blue-500 rounded-lg p-1 shadow-2xs hover:shadow-xs transition-all cursor-zoom-in group"
                              title="Click to Zoom Form Populated Evidence"
                            >
                              <div className="text-[8px] font-bold text-blue-800 truncate mb-0.5 group-hover:text-blue-600">
                                📋 1. Form State
                              </div>
                              <img
                                src={step.form_screenshot_url}
                                alt="Form Evidence"
                                className="w-full h-14 object-cover rounded border border-slate-100"
                              />
                            </div>

                            {/* 2. Confirmation Modal */}
                            <div
                              onClick={(e) => {
                                e.stopPropagation();
                                onOpenLightbox?.(step, 'modal', step.modal_screenshot_url!);
                              }}
                              className="bg-white border-2 border-emerald-200 hover:border-emerald-500 rounded-lg p-1 shadow-2xs hover:shadow-xs transition-all cursor-zoom-in group"
                              title="Click to Zoom Confirmation Dialog Evidence"
                            >
                              <div className="text-[8px] font-bold text-emerald-800 truncate mb-0.5 group-hover:text-emerald-600">
                                ✅ 2. Confirmation
                              </div>
                              <img
                                src={step.modal_screenshot_url}
                                alt="Modal Evidence"
                                className="w-full h-14 object-cover rounded border border-slate-100"
                              />
                            </div>
                          </div>
                        ) : step.screenshot_url ? (
                          <div
                            onClick={(e) => {
                              e.stopPropagation();
                              onOpenLightbox?.(step, 'combined', step.screenshot_url!);
                            }}
                            className="bg-white border-2 border-slate-200 hover:border-blue-400 rounded-lg p-1 shadow-2xs hover:shadow-xs transition-all cursor-zoom-in group"
                            title="Click to Zoom Evidence"
                          >
                            <div className="text-[8px] font-bold text-slate-700 truncate mb-0.5 group-hover:text-blue-600">
                              🔍 Step Evidence Screenshot
                            </div>
                            <img
                              src={step.screenshot_url}
                              alt="Evidence"
                              className="w-full h-14 object-cover rounded border border-slate-100"
                            />
                          </div>
                        ) : null}
                      </div>
                    )}

                    {/* Footer Tags */}
                    <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500">
                      <span className="truncate max-w-[160px] font-medium text-slate-600">
                        {step.action_intent}
                      </span>
                      {step.screenshot_required && (
                        <span className="px-1.5 py-0.2 bg-purple-50 text-purple-700 border border-purple-200 rounded font-bold">
                          µ Screenshot
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
