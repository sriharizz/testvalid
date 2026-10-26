import React, { useState, useRef } from 'react';
import {
  Zap,
  Eye,
  FileText,
  Download,
  BarChart3,
  ChevronDown,
  Layers,
  LogOut,
  ShieldCheck,
  CheckCircle2
} from 'lucide-react';
import { ProtocolSession, SimulationMode } from '../types';

interface TopHeaderBarProps {
  session: ProtocolSession | null;
  selectedProduct?: string;
  onProductChange?: (productId: string) => void;
  products?: { product_id: string; name: string }[];
  targetUrl?: string;
  username?: string;
  isExecuting: boolean;
  onExecute: () => void;
  onOpenLiveBrowser: () => void;
  onDownloadDocx: () => void;
  onDownloadEvidence?: () => void;
  onOpenSummaryModal?: () => void;
  onLogout?: () => void;
}

export const TopHeaderBar: React.FC<TopHeaderBarProps> = ({
  session,
  selectedProduct = 'onepv',
  products = [],
  targetUrl,
  username = 'sirihari.banda',
  isExecuting,
  onExecute,
  onOpenLiveBrowser,
  onDownloadDocx,
  onDownloadEvidence,
  onOpenSummaryModal,
  onLogout,
}) => {
  const [exportDropdownOpen, setExportDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const prodObj = products.find((p) => p.product_id === selectedProduct);
  const productName = prodObj?.name || (selectedProduct === 'signal' ? 'Clinevo Signal' : selectedProduct === 'custom' ? 'Custom Target' : 'Clinevo OnePV');

  const shortCode = session?.document_no
    ? session.document_no.split(' - ')[0]
    : session?.filename || 'No Protocol Loaded';

  return (
    <header className="bg-gradient-to-r from-[#0a1424] via-[#0d1c33] to-[#0a1424] text-white h-14 px-4 flex items-center justify-between shadow-md border-b border-slate-800 z-30 select-none">
      
      {/* 1. Left: Branding & Breadcrumb */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <ShieldCheck className="w-5 h-5 text-white" />
        </div>
        
        <div className="flex items-center gap-2">
          <span className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
            <span>Clinevo</span>
          </span>
          <span className="text-slate-500 font-light">/</span>
          <div className="flex items-center gap-1.5 bg-slate-800/90 border border-slate-700/80 px-2 py-0.5 rounded-lg text-xs font-semibold text-cyan-300">
            <Layers className="w-3 h-3 text-cyan-400" />
            <span>{productName}</span>
          </div>

          {session && (
            <>
              <span className="text-slate-600 font-light">/</span>
              <span className="text-xs text-slate-300 font-mono font-medium max-w-xs truncate" title={session.document_no || session.filename}>
                {shortCode}
              </span>
              <span className="text-[10px] bg-blue-500/20 text-blue-300 border border-blue-500/30 px-1.5 py-0.2 rounded font-bold">
                {session.total_steps || session.steps.length} Steps
              </span>
            </>
          )}
        </div>
      </div>

      {/* 2. Center: GxP Status Pill */}
      <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900/80 border border-slate-700/60 text-[11px] text-slate-300">
        <span className="w-2 h-2 rounded-full bg-emerald-400" />
        <span className="font-medium">21 CFR Part 11 Electronic Validation</span>
      </div>

      {/* 3. Right: Clean, Uncluttered Actions */}
      <div className="flex items-center space-x-2">
        
        {/* Live Browser Stream */}
        <button
          type="button"
          onClick={onOpenLiveBrowser}
          className="bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer"
          title="Watch real-time live browser automation stream"
        >
          <Eye className="w-3.5 h-3.5 text-blue-400" />
          <span>Live View</span>
        </button>

        {/* Primary Run Validation Button */}
        <button
          type="button"
          onClick={onExecute}
          disabled={!session || isExecuting}
          className={`font-semibold px-4 py-1.5 rounded-lg text-xs flex items-center space-x-1.5 shadow-sm transition-all cursor-pointer ${
            !session
              ? 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
              : isExecuting
              ? 'bg-blue-800 text-blue-200 cursor-not-allowed animate-pulse'
              : 'bg-[#1d63dc] hover:bg-blue-500 text-white shadow-blue-500/20 active:scale-95'
          }`}
          title={!session ? 'Select a protocol from the left folder sidebar to execute' : 'Run serial Playwright validation'}
        >
          <Zap className="w-3.5 h-3.5 fill-amber-300 text-amber-300" />
          <span>{isExecuting ? 'Automating...' : 'Run Validation'}</span>
        </button>

        {/* Executive Summary Button */}
        <button
          type="button"
          onClick={onOpenSummaryModal}
          disabled={!session}
          className={`font-semibold px-3 py-1.5 rounded-lg text-xs flex items-center space-x-1.5 transition-colors border cursor-pointer ${
            !session
              ? 'bg-slate-800/80 text-slate-500 border-slate-700/80 cursor-not-allowed'
              : 'bg-amber-600 hover:bg-amber-500 text-white border-amber-500/80 shadow-xs'
          }`}
          title="View Executive Summary &amp; AI Root-Cause Diagnostic Report"
        >
          <BarChart3 className="w-3.5 h-3.5 text-amber-200" />
          <span className="hidden sm:inline">Executive Summary</span>
        </button>

        {/* Unified Export Documents Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setExportDropdownOpen(!exportDropdownOpen)}
            disabled={!session}
            className={`font-semibold px-3 py-1.5 rounded-lg text-xs flex items-center space-x-1.5 transition-colors border cursor-pointer ${
              !session
                ? 'bg-slate-800/80 text-slate-500 border-slate-700/80 cursor-not-allowed'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
            }`}
            title="Download executed reports"
          >
            <Download className="w-3.5 h-3.5 text-emerald-400" />
            <span className="hidden sm:inline">Export</span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </button>

          {exportDropdownOpen && session && (
            <div className="absolute right-0 top-10 w-60 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-1.5 z-50 text-xs animate-in fade-in slide-in-from-top-1">
              <button
                type="button"
                onClick={() => {
                  onDownloadDocx();
                  setExportDropdownOpen(false);
                }}
                className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-slate-800 text-slate-200 flex items-center gap-2 transition-colors cursor-pointer"
              >
                <FileText className="w-4 h-4 text-blue-400 shrink-0" />
                <div>
                  <div className="font-semibold text-white">Executed Protocol (.docx)</div>
                  <div className="text-[10px] text-slate-400">Primary Word doc with Table 6 sign-off</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => {
                  if (onDownloadEvidence) onDownloadEvidence();
                  setExportDropdownOpen(false);
                }}
                className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-slate-800 text-slate-200 flex items-center gap-2 transition-colors cursor-pointer mt-0.5"
              >
                <Download className="w-4 h-4 text-emerald-400 shrink-0" />
                <div>
                  <div className="font-semibold text-white">Evidence Dossier (.docx)</div>
                  <div className="text-[10px] text-slate-400">Timestamped &amp; watermarked screenshots</div>
                </div>
              </button>
            </div>
          )}
        </div>

        {/* User Profile / Logout */}
        {onLogout && (
          <button
            type="button"
            onClick={onLogout}
            className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-400 hover:text-white transition-colors cursor-pointer ml-1"
            title="Log Out &amp; Change Target Environment"
          >
            <LogOut className="w-3.5 h-3.5 text-rose-400" />
          </button>
        )}

      </div>
    </header>
  );
};
