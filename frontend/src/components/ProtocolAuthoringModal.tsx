import React, { useState } from 'react';
import {
  FileCode,
  FileText,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  Download,
  X,
  BookOpen,
  Layers
} from 'lucide-react';

interface ProtocolAuthoringModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoadGeneratedProtocol: (filename: string) => void;
}

export const ProtocolAuthoringModal: React.FC<ProtocolAuthoringModalProps> = ({
  isOpen,
  onClose,
  onLoadGeneratedProtocol
}) => {
  const [protocolType, setProtocolType] = useState<'OQ' | 'PQ'>('OQ');
  const [systemName, setSystemName] = useState('OnePV Safety System');
  const [version, setVersion] = useState('1.0');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedResult, setGeneratedResult] = useState<any | null>(null);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGeneratedResult(null);

    try {
      const res = await fetch('/api/generate-protocol', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          protocol_type: protocolType,
          source_type: protocolType === 'OQ' ? 'FDS' : 'URS',
          system_name: systemName,
          version: version
        })
      });

      const data = await res.json();
      setGeneratedResult(data);
    } catch (e) {
      console.error('Error generating protocol:', e);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleLoadIntoPortal = () => {
    if (generatedResult && generatedResult.filename) {
      onLoadGeneratedProtocol(generatedResult.filename);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-3xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-blue-700 via-indigo-700 to-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-white/10 rounded-xl">
              <Sparkles className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <h2 className="font-bold text-base md:text-lg">AI-Assisted OQ / PQ Protocol Authoring</h2>
              <p className="text-xs text-blue-200">
                Automated GxP Validation Protocol Preparation from FDS & URS Specifications
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

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs text-slate-700">
          {/* Protocol Type Selector */}
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => { setProtocolType('OQ'); setGeneratedResult(null); }}
              className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between ${
                protocolType === 'OQ'
                  ? 'border-blue-600 bg-blue-50/60 shadow-sm ring-2 ring-blue-500/20'
                  : 'border-slate-200 hover:border-slate-300 bg-white'
              }`}
            >
              <div className="flex items-center justify-between w-full mb-2">
                <span className="font-bold text-sm text-slate-900 flex items-center gap-1.5">
                  <FileCode className="w-4 h-4 text-blue-600" />
                  <span>Operational Qualification (OQ)</span>
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">FDS Source</span>
              </div>
              <p className="text-slate-500 text-[11px] leading-relaxed">
                Generates functional module tests, boundary checks, field validations, and security limits from Functional Design Specs (FDS).
              </p>
            </button>

            <button
              type="button"
              onClick={() => { setProtocolType('PQ'); setGeneratedResult(null); }}
              className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between ${
                protocolType === 'PQ'
                  ? 'border-indigo-600 bg-indigo-50/60 shadow-sm ring-2 ring-indigo-500/20'
                  : 'border-slate-200 hover:border-slate-300 bg-white'
              }`}
            >
              <div className="flex items-center justify-between w-full mb-2">
                <span className="font-bold text-sm text-slate-900 flex items-center gap-1.5">
                  <BookOpen className="w-4 h-4 text-indigo-600" />
                  <span>Performance Qualification (PQ)</span>
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800">URS Source</span>
              </div>
              <p className="text-slate-500 text-[11px] leading-relaxed">
                Generates end-to-end clinical workflow scenarios, user personas, MedDRA coding, and negative testing from User Requirements (URS).
              </p>
            </button>
          </div>

          {/* Configuration Form */}
          <div className="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Target System Name</label>
              <input
                type="text"
                value={systemName}
                onChange={(e) => setSystemName(e.target.value)}
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-900 font-medium"
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Protocol Version</label>
              <input
                type="text"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-900 font-medium"
              />
            </div>
          </div>

          {/* Standards & RTM Note */}
          <div className="bg-amber-50 border border-amber-200 text-amber-900 p-3 rounded-xl flex items-start gap-2.5">
            <Layers className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">GxP 8-Table Protocol Structure with Built-In RTM:</span>
              <p className="text-[11px] text-amber-800 mt-0.5">
                Automatically formats Document History, Approvals, Test Scenarios, Acceptance Criteria (Table 6), Deviation Log (Table 7), and full Requirements Traceability Matrix (Table 8).
              </p>
            </div>
          </div>

          {/* Generated Result Preview */}
          {generatedResult && (
            <div className="border border-emerald-200 bg-emerald-50/50 rounded-xl p-4 space-y-2 animate-in fade-in">
              <div className="flex items-center justify-between text-emerald-900 font-bold text-sm">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Protocol Successfully Generated & Saved</span>
                </span>
                <span className="text-xs font-semibold px-2 py-0.5 bg-emerald-200 rounded text-emerald-800">
                  {generatedResult.total_steps_generated} Test Steps
                </span>
              </div>
              <p className="text-slate-600 font-mono text-[11px]">
                {generatedResult.filename}
              </p>
              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  onClick={handleLoadIntoPortal}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg flex items-center gap-1.5 shadow-sm active:scale-95 transition-all text-xs"
                >
                  <span>Load Protocol Into Validation Engine</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <span className="text-slate-500 italic">21 CFR Part 11 / GAMP 5 Category 4 Protocol Authoring</span>
          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 font-semibold rounded-lg shadow-2xs"
            >
              Close
            </button>
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="px-4 py-1.5 bg-[#1d63dc] hover:bg-blue-600 text-white font-bold rounded-lg flex items-center gap-1.5 shadow-sm active:scale-95 transition-all"
            >
              <Sparkles className="w-3.5 h-3.5 fill-amber-300 text-amber-300" />
              <span>{isGenerating ? 'Drafting Protocol...' : `Generate ${protocolType} Protocol`}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
