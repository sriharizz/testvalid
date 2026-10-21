import React from 'react';
import { X, Code2, FileText, CheckCircle2, ShieldCheck, GitCommit } from 'lucide-react';
import { TraceStage } from '../types';

interface ArtifactModalProps {
  stage: TraceStage | null;
  onClose: () => void;
}

export const ArtifactModal: React.FC<ArtifactModalProps> = ({ stage, onClose }) => {
  if (!stage) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in select-none">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl max-w-4xl w-full overflow-hidden flex flex-col max-h-[88vh]">
        {/* Header */}
        <div className="bg-slate-950 px-5 py-3 border-b border-slate-800 flex items-center justify-between text-white">
          <div className="flex items-center space-x-2.5">
            {stage.artifact_type === 'CODE' ? (
              <Code2 className="w-5 h-5 text-blue-400" />
            ) : stage.artifact_type === 'COVERAGE' ? (
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
            ) : stage.artifact_type === 'GIT' ? (
              <GitCommit className="w-5 h-5 text-indigo-400" />
            ) : (
              <FileText className="w-5 h-5 text-cyan-400" />
            )}
            <div>
              <h3 className="font-bold text-sm">{stage.title}</h3>
              <p className="text-[11px] text-slate-400">{stage.subtitle}</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
              PASS
            </span>
            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content Viewer */}
        <div className="p-4 bg-slate-950/70 overflow-auto flex-1 font-mono text-xs text-slate-300">
          <pre className="whitespace-pre-wrap leading-relaxed select-text bg-slate-950 p-4 rounded-xl border border-slate-800 text-[11px]">
            {stage.artifact_content || '// No artifact content recorded for this stage.'}
          </pre>
        </div>

        {/* Footer */}
        <div className="bg-slate-950 px-5 py-2.5 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>Artifact Type: {stage.artifact_type}</span>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded text-xs font-semibold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
