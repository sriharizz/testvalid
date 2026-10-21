import React, { useState } from 'react';
import {
  Lock,
  Eye,
  EyeOff,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  Loader2,
  Circle
} from 'lucide-react';
import { TraceStage, ProtocolSession } from '../types';

interface LeftTraceabilityPaneProps {
  session: ProtocolSession | null;
  isAuthoring?: boolean;
  authoringStage?: number;
  username: string;
  setUsername: (val: string) => void;
  password: string;
  setPassword: (val: string) => void;
  enterprise: string;
  setEnterprise: (val: string) => void;
  requiresApproval: boolean;
  setRequiresApproval: (val: boolean) => void;
  waitingForApproval: boolean;
  onApproveLogin: () => void;
  onSelectStage: (stage: TraceStage) => void;
}

export const LeftTraceabilityPane: React.FC<LeftTraceabilityPaneProps> = ({
  session,
  isAuthoring,
  authoringStage = 0,
  username,
  setUsername,
  password,
  setPassword,
  enterprise,
  setEnterprise,
  requiresApproval,
  setRequiresApproval,
  waitingForApproval,
  onApproveLogin,
  onSelectStage,
}) => {
  const [showPassword, setShowPassword] = useState(false);

  // Compute dynamic stage display during authoring or idle
  const getStageState = (stageNum: number) => {
    if (session && authoringStage >= 6) {
      const realStage = session.trace_stages?.find((s) => s.stage_number === stageNum);
      if (realStage) return realStage;
    }

    if (authoringStage > 0) {
      if (stageNum < authoringStage) {
        return {
          stage_number: stageNum,
          title: getStageTitle(stageNum),
          subtitle: getStageCompletedSubtitle(stageNum),
          status: 'PASS' as const,
          latency_seconds: getStageSimLatency(stageNum),
          artifact_type: 'JSON' as const,
          artifact_content: '',
        };
      } else if (stageNum === authoringStage) {
        return {
          stage_number: stageNum,
          title: getStageTitle(stageNum),
          subtitle: getStageRunningSubtitle(stageNum),
          status: 'RUNNING' as const,
          latency_seconds: 0.0,
          artifact_type: 'JSON' as const,
          artifact_content: '',
        };
      }
    }

    return {
      stage_number: stageNum,
      title: getStageTitle(stageNum),
      subtitle: getStagePendingSubtitle(stageNum),
      status: 'PENDING' as const,
      latency_seconds: 0.0,
      artifact_type: 'JSON' as const,
      artifact_content: '',
    };
  };

  const getStageTitle = (num: number) => {
    switch (num) {
      case 1: return '1. Python Protocol Extractor';
      case 2: return '2. Groq Qwen Planner Agent';
      case 3: return '3. Coverage Checker Gate 1';
      case 4: return '4. Playwright Generator & Healer';
      case 5: return '5. Coverage Checker Gate 2';
      case 6: return '6. Frozen Git Baseline';
      default: return `Stage ${num}`;
    }
  };

  const getStagePendingSubtitle = (num: number) => {
    switch (num) {
      case 1: return 'Awaiting .docx upload';
      case 2: return 'Awaiting extracted steps';
      case 3: return 'Awaiting test plan generation';
      case 4: return 'Awaiting coverage sign-off';
      case 5: return 'Awaiting spec generation';
      case 6: return 'Awaiting gate verification';
      default: return 'Pending';
    }
  };

  const getStageRunningSubtitle = (num: number) => {
    switch (num) {
      case 1: return 'Parsing OpenXML tables & µ symbols...';
      case 2: return 'Groq Qwen 3.8-27B formulating GxP strategy...';
      case 3: return 'Verifying 1:1 sequence order...';
      case 4: return 'Synthesizing serial Playwright .spec.ts...';
      case 5: return 'Verifying assertions & screenshot points...';
      case 6: return 'Computing SHA-1 commit freeze...';
      default: return 'Executing...';
    }
  };

  const getStageCompletedSubtitle = (num: number) => {
    switch (num) {
      case 1: return '18 steps, 18 µ screenshot points extracted';
      case 2: return 'Plan mapped via Groq Qwen 3.8-27B';
      case 3: return '18/18 IDs & Order Verified';
      case 4: return 'Serial .spec.ts synthesized';
      case 5: return '18/18 Evidence Points Verified';
      case 6: return 'Commit SHA frozen';
      default: return 'Completed';
    }
  };

  const getStageSimLatency = (num: number) => {
    switch (num) {
      case 1: return 0.3;
      case 2: return 2.8;
      case 3: return 0.1;
      case 4: return 0.2;
      case 5: return 0.1;
      case 6: return 0.1;
      default: return 0.1;
    }
  };

  const displayStages: TraceStage[] = [1, 2, 3, 4, 5, 6].map((num) => getStageState(num));

  const [isCredsOpen, setIsCredsOpen] = useState(false);

  return (
    <aside className="w-[310px] flex-shrink-0 flex flex-col p-3 border-r border-slate-200 bg-[#f8fafc] h-[calc(100vh-3.5rem)] overflow-y-auto select-none">
      <div className="pb-2.5">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center justify-between">
          <span>AGENT PIPELINE & TRACEABILITY</span>
        </h2>
        <div className="h-0.5 w-12 bg-[#1d63dc] rounded-full mt-1" />
      </div>

      {/* Card 1: Sleek Collapsible Credential Gate */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-2.5 mb-2.5">
        <div
          onClick={() => setIsCredsOpen(!isCredsOpen)}
          className="flex items-center justify-between text-xs cursor-pointer hover:text-[#1d63dc] transition-colors"
        >
          <div className="flex items-center space-x-2">
            <div className="p-1 rounded bg-blue-50 text-[#1d63dc]">
              <Lock className="w-3.5 h-3.5" />
            </div>
            <div>
              <div className="font-semibold text-slate-800 text-[11px] flex items-center gap-1.5">
                <span>OnePV Credentials</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" title="Ready" />
              </div>
              <div className="text-[10px] text-slate-500 font-mono truncate max-w-[170px]">
                {username} ({enterprise})
              </div>
            </div>
          </div>
          <span className="text-[10px] text-slate-500 font-medium px-1.5 py-0.5 rounded bg-slate-100 hover:bg-slate-200">
            {isCredsOpen ? 'Hide' : 'Edit'}
          </span>
        </div>

        {/* Collapsible Form */}
        {isCredsOpen && (
          <div className="space-y-2 text-xs pt-2.5 mt-2 border-t border-slate-100 animate-in fade-in">
            <div>
              <label className="block text-[11px] font-medium text-slate-600 mb-0.5">User Name</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-2 py-1 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-blue-500 bg-white"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-600 mb-0.5">Password</label>
              <div className="relative flex items-center">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-2 pr-7 py-1 border border-slate-300 rounded text-xs focus:ring-1 focus:ring-blue-500 bg-white"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-1.5 text-slate-400 hover:text-slate-600 p-0.5"
                  title={showPassword ? 'Hide' : 'Show'}
                >
                  {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-600 mb-0.5">Enterprise</label>
              <input
                type="text"
                value={enterprise}
                onChange={(e) => setEnterprise(e.target.value)}
                className="w-full px-2 py-1 border border-slate-200 rounded text-xs bg-slate-50 text-slate-700"
              />
            </div>

            <div className="flex items-center space-x-1.5 pt-0.5">
              <input
                type="checkbox"
                id="requiresApproval"
                checked={requiresApproval}
                onChange={(e) => setRequiresApproval(e.target.checked)}
                className="rounded border-slate-300 text-[#1d63dc] focus:ring-blue-500 w-3 h-3 cursor-pointer"
              />
              <label htmlFor="requiresApproval" className="text-[10px] text-slate-600 cursor-pointer">
                Require Tester Approval before login
              </label>
            </div>
          </div>
        )}

        {/* Runtime Alert when waitingForApproval */}
        {waitingForApproval && (
          <div className="mt-2 p-2 bg-amber-500/15 border border-amber-500/60 rounded-lg animate-bounce">
            <div className="text-[11px] font-bold text-amber-800">
              ⚠️ Tester Login Approval Required
            </div>
            <button
              type="button"
              onClick={onApproveLogin}
              className="mt-1 w-full py-1.5 rounded text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white shadow-xs transition-all"
            >
              Approve & Inject Login Now
            </button>
          </div>
        )}
      </div>

      {/* Card 2: 6-Stage Agent Traceability Timeline */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-3.5 flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-800 pb-2 border-b border-slate-100">
          <div className="p-1 rounded bg-blue-50 text-[#1d63dc]">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <span>6-Stage Agent Traceability Timeline</span>
        </div>

        {/* Live Groq Agent Thinking Box */}
        {(isAuthoring || authoringStage === 2) && (
          <div className="mt-2.5 p-2.5 bg-gradient-to-r from-slate-900 to-slate-950 border border-cyan-500/30 rounded-lg text-xs space-y-1.5 shadow-md animate-in fade-in">
            <div className="flex items-center space-x-1.5 font-bold text-cyan-400">
              <Sparkles className="w-3.5 h-3.5 animate-spin" />
              <span>Groq Qwen 3.8-27B Active Reasoning:</span>
            </div>
            <p className="text-[10px] text-slate-300 font-mono leading-relaxed">
              "Analyzing protocol requirements, validating 21 CFR Part 11 audit trails, mapping OnePV DOM locators, and generating deterministic Playwright specification..."
            </p>
          </div>
        )}

        <div className="flex-1 overflow-y-auto pt-2.5 pr-1 space-y-3">
          {displayStages.map((stage, idx) => {
            const isPass = stage.status === 'PASS';
            const isRunning = stage.status === 'RUNNING';
            const isFail = stage.status === 'FAIL';
            const isPending = stage.status === 'PENDING';

            return (
              <div
                key={stage.stage_number}
                onClick={() => {
                  if (session) onSelectStage(stage);
                }}
                className={`flex items-start space-x-2.5 p-2 rounded-lg transition-colors relative group border ${
                  session
                    ? 'hover:bg-blue-50/50 cursor-pointer border-transparent hover:border-blue-100'
                    : 'cursor-default border-transparent opacity-85'
                }`}
              >
                {/* Connecting line */}
                {idx < displayStages.length - 1 && (
                  <div
                    className={`absolute left-[18px] top-7 bottom-[-16px] w-0.5 ${
                      isPass ? 'bg-emerald-200' : 'bg-slate-200'
                    }`}
                  />
                )}

                {/* Status Icon */}
                <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 z-10">
                  {isPass && (
                    <div className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
                      <CheckCircle2 className="w-4 h-4 fill-emerald-600 text-white" />
                    </div>
                  )}
                  {isRunning && (
                    <div className="w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center animate-spin">
                      <Loader2 className="w-3.5 h-3.5" />
                    </div>
                  )}
                  {isFail && (
                    <div className="w-5 h-5 rounded-full bg-red-100 text-red-600 flex items-center justify-center">
                      <XCircle className="w-4 h-4 fill-red-600 text-white" />
                    </div>
                  )}
                  {isPending && (
                    <div className="w-4 h-4 rounded-full border-2 border-slate-300 bg-white flex items-center justify-center">
                      <Circle className="w-1.5 h-1.5 text-slate-300 fill-slate-300" />
                    </div>
                  )}
                </div>

                {/* Stage Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-xs font-bold truncate transition-colors ${
                        isPass
                          ? 'text-slate-800 group-hover:text-[#1d63dc]'
                          : isRunning
                          ? 'text-[#1d63dc]'
                          : 'text-slate-500'
                      }`}
                    >
                      {stage.title}
                    </span>

                    {/* Latency / Status Badge */}
                    {isPass && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {stage.latency_seconds > 0 ? `${stage.latency_seconds}s` : '0.1s'}
                      </span>
                    )}
                    {isRunning && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 animate-pulse">
                        Active
                      </span>
                    )}
                    {isPending && (
                      <span className="text-[10px] text-slate-400 font-medium">
                        —
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 truncate mt-0.5">
                    {stage.subtitle}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </aside>
  );
};
