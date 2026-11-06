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
  Layers,
  Edit3,
  Plus,
  Trash2,
  PlayCircle
} from 'lucide-react';

interface ProtocolAuthoringModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoadGeneratedProtocol: (filename: string) => void;
  onLoadDirectSession?: (sessionData: any) => void;
}

export const ProtocolAuthoringModal: React.FC<ProtocolAuthoringModalProps> = ({
  isOpen,
  onClose,
  onLoadGeneratedProtocol,
  onLoadDirectSession
}) => {
  const [activeTab, setActiveTab] = useState<'studio' | 'generator'>('studio');

  // Generator State
  const [protocolType, setProtocolType] = useState<'OQ' | 'PQ'>('PQ');
  const [systemName, setSystemName] = useState('OnePV Safety System');
  const [version, setVersion] = useState('1.0');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedResult, setGeneratedResult] = useState<any | null>(null);

  // Direct Studio State
  const [directDocNo, setDirectDocNo] = useState('CLIN-PQ-STUDIO-001');
  const [directTitle, setDirectTitle] = useState('Direct Studio Pharmacovigilance Qualification');
  const [directType, setDirectType] = useState<'PQ' | 'OQ'>('PQ');
  const [directTargetUrl, setDirectTargetUrl] = useState('https://mpv-two.vercel.app');
  const [isCompilingDirect, setIsCompilingDirect] = useState(false);
  const [directSteps, setDirectSteps] = useState([
    {
      step_id: 'TS1-S01',
      scenario: '[REQ-01] fill reporter details Case',
      procedure: 'fill reporter details and check (µ)',
      expected_result: 'Reporter details saved successfully',
      requires_screenshot: true
    },
    {
      step_id: 'TS1-S02',
      scenario: '[REQ-02] General Case Intake Registration',
      procedure: 'Under General Information section, select Case Classification: Adverse Event, Case Intake Source: Spontaneous, and set Company Receipt Date: today and Processing Center Received Date: today. Click Save. (µ)',
      expected_result: 'General Information saved successfully',
      requires_screenshot: true
    },
    {
      step_id: 'TS1-S03',
      scenario: '[REQ-03] Patient Missing First Name Validation',
      procedure: 'fill patient details without first name and check (µ)',
      expected_result: 'System shall display error because first name is mandatory',
      requires_screenshot: true
    }
  ]);

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

  const handleCompileDirect = async () => {
    setIsCompilingDirect(true);
    try {
      const res = await fetch('/api/author-direct-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          protocol_type: directType,
          product_id: 'onepv',
          system_name: systemName,
          document_no: directDocNo,
          version: version,
          title: directTitle,
          target_url: directTargetUrl,
          steps: directSteps
        })
      });

      if (!res.ok) {
        throw new Error(`Failed to compile direct session: ${res.statusText}`);
      }
      const data = await res.json();
      if (onLoadDirectSession) {
        onLoadDirectSession(data);
      } else {
        onLoadGeneratedProtocol(data.filename);
      }
      onClose();
    } catch (e) {
      console.error('Error authoring direct session:', e);
      alert('Failed to compile direct session. See console.');
    } finally {
      setIsCompilingDirect(false);
    }
  };

  const addStep = () => {
    const nextIdx = directSteps.length + 1;
    setDirectSteps([
      ...directSteps,
      {
        step_id: `TS1-S${nextIdx.toString().padStart(2, '0')}`,
        scenario: `Verification Scenario #${nextIdx}`,
        procedure: 'Enter test procedure instructions here. (µ)',
        expected_result: 'Expected system response and acceptance criteria.',
        requires_screenshot: true
      }
    ]);
  };

  const removeStep = (index: number) => {
    if (directSteps.length <= 1) return;
    setDirectSteps(directSteps.filter((_, i) => i !== index));
  };

  const updateStep = (index: number, field: string, val: any) => {
    const updated = [...directSteps];
    updated[index] = { ...updated[index], [field]: val };
    setDirectSteps(updated);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-blue-700 via-indigo-700 to-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-white/10 rounded-xl">
              <Sparkles className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <h2 className="font-bold text-base md:text-lg">Protocol Authoring & Direct Studio</h2>
              <p className="text-xs text-blue-200">
                Write test steps directly in-system (0 Doc Upload) or generate GxP CSV templates from specifications
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-white/20 text-white transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 bg-slate-50 px-6 pt-3 gap-2">
          <button
            type="button"
            onClick={() => setActiveTab('studio')}
            className={`px-4 py-2 text-xs font-bold rounded-t-lg transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'studio'
                ? 'bg-white text-blue-700 border-t-2 border-blue-600 border-x border-slate-200 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <Edit3 className="w-3.5 h-3.5 text-blue-600" />
            <span>Direct Step Studio (Write In-System — 0 Doc Upload)</span>
            <span className="px-1.5 py-0.2 bg-blue-100 text-blue-800 text-[10px] font-bold rounded-full">New v4</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('generator')}
            className={`px-4 py-2 text-xs font-bold rounded-t-lg transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === 'generator'
                ? 'bg-white text-indigo-700 border-t-2 border-indigo-600 border-x border-slate-200 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>AI Template Generator (FDS / URS)</span>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs text-slate-700 flex-1">
          {activeTab === 'studio' ? (
            /* TAB 1: DIRECT STEP STUDIO */
            <div className="space-y-4">
              <div className="grid grid-cols-4 gap-3 bg-slate-50 p-3.5 rounded-xl border border-slate-200">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Document No</label>
                  <input
                    type="text"
                    value={directDocNo}
                    onChange={(e) => setDirectDocNo(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-900 font-mono text-[11px]"
                  />
                </div>
                <div className="col-span-2">
                  <label className="font-semibold text-slate-700 block mb-1">Protocol Title</label>
                  <input
                    type="text"
                    value={directTitle}
                    onChange={(e) => setDirectTitle(e.target.value)}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-900 font-medium text-[11px]"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Type</label>
                  <select
                    value={directType}
                    onChange={(e) => setDirectType(e.target.value as 'PQ' | 'OQ')}
                    className="w-full px-2.5 py-1.5 border border-slate-300 rounded-lg bg-white text-slate-900 font-medium text-[11px]"
                  >
                    <option value="PQ">PQ (Performance)</option>
                    <option value="OQ">OQ (Operational)</option>
                  </select>
                </div>
              </div>

              {/* Steps Table */}
              <div className="border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
                <div className="bg-slate-100 px-4 py-2 border-b border-slate-200 flex items-center justify-between">
                  <span className="font-bold text-slate-800 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-blue-600" />
                    <span>Interactive Test Step Authoring Table ({directSteps.length} steps)</span>
                  </span>
                  <button
                    type="button"
                    onClick={addStep}
                    className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-[11px] font-bold flex items-center gap-1 shadow-2xs cursor-pointer"
                  >
                    <Plus className="w-3 h-3" />
                    <span>Add Step</span>
                  </button>
                </div>
                <div className="divide-y divide-slate-200 max-h-[38vh] overflow-y-auto">
                  {directSteps.map((step, idx) => (
                    <div key={idx} className="p-3.5 bg-white hover:bg-blue-50/20 transition-colors space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-blue-700 text-[11px] px-2 py-0.5 bg-blue-50 rounded border border-blue-200">
                            {step.step_id}
                          </span>
                          <input
                            type="text"
                            value={step.scenario}
                            onChange={(e) => updateStep(idx, 'scenario', e.target.value)}
                            placeholder="Test Scenario Name"
                            className="px-2 py-1 border border-slate-300 rounded font-semibold text-slate-900 text-[11px] w-80"
                          />
                        </div>
                        <div className="flex items-center gap-3">
                          <label className="flex items-center gap-1 text-[11px] font-medium text-slate-600 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={step.requires_screenshot}
                              onChange={(e) => updateStep(idx, 'requires_screenshot', e.target.checked)}
                              className="rounded border-slate-300 text-blue-600"
                            />
                            <span>µ Capture</span>
                          </label>
                          {directSteps.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeStep(idx)}
                              className="text-red-500 hover:text-red-700 p-1 cursor-pointer"
                              title="Delete Step"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div>
                          <label className="text-slate-500 font-semibold block mb-0.5">Test Procedure Instructions</label>
                          <textarea
                            value={step.procedure}
                            onChange={(e) => updateStep(idx, 'procedure', e.target.value)}
                            rows={3}
                            className="w-full px-2 py-1 border border-slate-300 rounded font-mono text-[11px] leading-snug"
                          />
                        </div>
                        <div>
                          <label className="text-slate-500 font-semibold block mb-0.5">Expected Acceptance Criteria</label>
                          <textarea
                            value={step.expected_result}
                            onChange={(e) => updateStep(idx, 'expected_result', e.target.value)}
                            rows={3}
                            className="w-full px-2 py-1 border border-slate-300 rounded font-mono text-[11px] leading-snug"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-emerald-50 border border-emerald-200 text-emerald-900 p-3 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span className="text-[11px]">
                    <strong>Zero-File-Upload Flow:</strong> Steps compile directly into the test engine in memory, while a baseline GxP .docx is created in the background for executed Word report export.
                  </span>
                </div>
              </div>
            </div>
          ) : (
            /* TAB 2: AI TEMPLATE GENERATOR */
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => { setProtocolType('OQ'); setGeneratedResult(null); }}
                  className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between cursor-pointer ${
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
                  className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between cursor-pointer ${
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
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg flex items-center gap-1.5 shadow-sm active:scale-95 transition-all text-xs cursor-pointer"
                    >
                      <span>Load Protocol Into Validation Engine</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <span className="text-slate-500 italic">21 CFR Part 11 / GAMP 5 Category 4 Protocol Authoring</span>
          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 font-semibold rounded-lg shadow-2xs cursor-pointer"
            >
              Close
            </button>
            {activeTab === 'studio' ? (
              <button
                onClick={handleCompileDirect}
                disabled={isCompilingDirect}
                className="px-5 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-lg flex items-center gap-1.5 shadow-sm active:scale-95 transition-all cursor-pointer"
              >
                <PlayCircle className="w-4 h-4 text-white" />
                <span>{isCompilingDirect ? 'Compiling Studio Protocol...' : 'Compile & Launch Directly in System'}</span>
              </button>
            ) : (
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="px-4 py-1.5 bg-[#1d63dc] hover:bg-blue-600 text-white font-bold rounded-lg flex items-center gap-1.5 shadow-sm active:scale-95 transition-all cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5 fill-amber-300 text-amber-300" />
                <span>{isGenerating ? 'Drafting Protocol...' : `Generate ${protocolType} Protocol`}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
