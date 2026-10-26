import React, { useRef, useState, useEffect } from 'react';
import {
  Upload,
  Sparkles,
  BarChart3,
  Zap,
  Download,
  Eye,
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  FileText
} from 'lucide-react';
import { ProtocolSession, SimulationMode } from '../types';

interface TopHeaderBarProps {
  session: ProtocolSession | null;
  simMode: SimulationMode;
  onSimModeChange: (mode: SimulationMode) => void;
  visibleBrowser: boolean;
  onVisibleBrowserChange: (val: boolean) => void;
  onUploadFile: (file: File, productId?: string) => void;
  onLoadSample: (filename: string, productId?: string) => void;
  onExecute: () => void;
  onOpenLiveBrowser: () => void;
  onDownloadDocx: () => void;
  onDownloadEvidence?: () => void;
  onOpenAuthoringModal?: () => void;
  onOpenSummaryModal?: () => void;
  isExecuting: boolean;
  isAuthoring?: boolean;
  selectedProduct?: string;
  onProductChange?: (productId: string) => void;
  products?: { product_id: string; name: string }[];
}

export const TopHeaderBar: React.FC<TopHeaderBarProps> = ({
  session,
  simMode,
  onSimModeChange,
  visibleBrowser,
  onVisibleBrowserChange,
  onUploadFile,
  onLoadSample,
  onExecute,
  onOpenLiveBrowser,
  onDownloadDocx,
  onDownloadEvidence,
  onOpenAuthoringModal,
  onOpenSummaryModal,
  isExecuting,
  isAuthoring,
  selectedProduct: propSelectedProduct,
  onProductChange: propOnProductChange,
  products: propProducts,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [samples, setSamples] = useState<{ filename: string; size_kb: number }[]>([]);
  const [internalProducts, setInternalProducts] = useState<{ product_id: string; name: string }[]>([]);
  const [internalSelectedProduct, setInternalSelectedProduct] = useState<string>("onepv");

  const effectiveProducts = (propProducts && propProducts.length > 0) ? propProducts : internalProducts;
  const effectiveProduct = propSelectedProduct || internalSelectedProduct;

  const handleProductSelect = (pId: string) => {
    if (propOnProductChange) propOnProductChange(pId);
    setInternalSelectedProduct(pId);
  };

  useEffect(() => {
    fetch('/api/products')
      .then((res) => res.json())
      .then((data) => {
        if (data && data.products) setInternalProducts(data.products);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch('/api/list-sample-protocols')
      .then((res) => res.json())
      .then((data) => {
        if (data && data.protocols) setSamples(data.protocols);
      })
      .catch(() => {});
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUploadFile(e.target.files[0], effectiveProduct);
    }
  };

  const totalSteps = session?.total_steps;
  const mapped = session?.coverage_mapped;
  const skipped = session?.coverage_skipped;

  return (
    <header className="bg-gradient-to-r from-[#0b192c] via-[#102542] to-[#0b192c] text-white h-14 px-4 flex items-center justify-between shadow-md border-b border-slate-800 z-30 select-none">
      {/* Left: Branding */}
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <svg
            className="w-5 h-5 text-white"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.04Z" />
            <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.04Z" />
          </svg>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-bold text-base md:text-lg tracking-tight text-white flex items-center gap-1.5">
            <span>Clinevo</span>
            <span className="text-slate-400 font-normal">—</span>
          </span>
          <select
            value={effectiveProduct}
            onChange={(e) => handleProductSelect(e.target.value)}
            disabled={isAuthoring || isExecuting}
            className="bg-slate-800/90 hover:bg-slate-700/90 border border-slate-700 text-white font-semibold text-xs rounded-lg px-2.5 py-1 focus:outline-hidden focus:ring-1 focus:ring-blue-500 cursor-pointer transition-colors shadow-xs"
            title="Select target product for validation"
          >
            {effectiveProducts.length > 0 ? (
              effectiveProducts.map((p) => (
                <option key={p.product_id} value={p.product_id} className="bg-slate-900 text-white">
                  {p.name}
                </option>
              ))
            ) : (
              <option value="onepv">OnePV</option>
            )}
          </select>
          <span className="font-medium text-xs text-slate-300 hidden xl:inline">Portal</span>
        </div>
      </div>

      {/* Center: Upload & Simulation Controls */}
      <div className="flex items-center space-x-2.5">
        {/* Author OQ/PQ Button */}
        <button
          type="button"
          onClick={onOpenAuthoringModal}
          disabled={isAuthoring || isExecuting}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-2.5 py-1.5 rounded-lg text-xs flex items-center space-x-1.5 shadow-xs transition-colors border border-indigo-400/40 mr-2"
          title="Prepare OQ (from FDS) or PQ (from URS) validation protocols automatically"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-300" />
          <span>Author OQ / PQ</span>
        </button>

        {/* Compact Upload Button + Dropdown */}
        <div className="relative flex items-center">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".docx"
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isAuthoring || isExecuting}
            className={`font-semibold px-3 py-1.5 rounded-l-lg text-xs flex items-center space-x-1.5 shadow-xs transition-all border-r border-blue-500/40 ${
              isAuthoring
                ? 'bg-blue-800 text-blue-200 animate-pulse'
                : 'bg-[#1d63dc] hover:bg-blue-600 text-white'
            }`}
            title="Upload your own OnePV validation protocol (.docx)"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>{isAuthoring ? 'Ingesting...' : 'Upload Protocol (.docx)'}</span>
          </button>
          <button
            type="button"
            onClick={() => setDropdownOpen(!dropdownOpen)}
            disabled={isAuthoring || isExecuting}
            className="bg-[#1d63dc] hover:bg-blue-600 text-white px-2 py-1.5 rounded-r-lg text-xs shadow-xs transition-colors"
            title="Choose from existing protocols"
          >
            <ChevronDown className="w-3 h-3" />
          </button>

          {dropdownOpen && (
            <div className="absolute left-0 top-9 w-64 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl p-2 z-50 animate-in fade-in slide-in-from-top-1 text-xs">
              <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider px-2 py-1 border-b border-slate-800">
                Sample Protocols
              </div>
              <div className="py-1 space-y-0.5">
                {samples.map((s) => (
                  <button
                    key={s.filename}
                    type="button"
                    onClick={() => {
                      onLoadSample(s.filename, effectiveProduct);
                      setDropdownOpen(false);
                    }}
                    className="w-full text-left px-2 py-1.5 rounded hover:bg-slate-800 text-slate-200 transition-colors flex flex-col"
                  >
                    <span className="font-medium truncate">{s.filename}</span>
                    <span className="text-[10px] text-slate-400">{s.size_kb} KB</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>

      {/* Right: Actions, Live View, Coverage & Download */}
      <div className="flex items-center space-x-2">
        {/* Live Browser Drawer Button */}
        <button
          type="button"
          onClick={onOpenLiveBrowser}
          className="bg-slate-900/90 hover:bg-slate-800 border border-slate-700 text-slate-200 px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors"
          title="Watch real-time live browser stream"
        >
          <Eye className="w-3.5 h-3.5 text-blue-400" />
          <span>Live View</span>
        </button>

        {/* Primary Execute Button */}
        <button
          type="button"
          onClick={onExecute}
          disabled={!session || isExecuting || isAuthoring}
          className={`font-semibold px-3.5 py-1.5 rounded-lg text-xs flex items-center space-x-1.5 shadow-sm transition-all ${
            !session
              ? 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
              : isExecuting
              ? 'bg-blue-800 text-blue-200 cursor-not-allowed animate-pulse'
              : 'bg-[#1d63dc] hover:bg-blue-500 text-white hover:shadow-blue-500/25 active:scale-95'
          }`}
          title={!session ? 'Upload a validation protocol to execute' : 'Run validation automation'}
        >
          <Zap className="w-3.5 h-3.5 fill-amber-300 text-amber-300" />
          <span>{isExecuting ? 'Automating...' : 'Run Validation'}</span>
        </button>


                {/* Executive Summary Button */}
        <button
          type="button"
          onClick={onOpenSummaryModal}
          disabled={!session}
          className={`font-semibold px-2.5 py-1.5 rounded-lg text-xs flex items-center space-x-1.5 shadow-xs transition-colors border ${
            !session
              ? 'bg-slate-800 text-slate-500 border-slate-700 cursor-not-allowed'
              : 'bg-amber-600 hover:bg-amber-500 text-white border-amber-500/80 shadow-amber-500/20'
          }`}
          title="View AI-Powered Executive Validation Summary & Root-Cause Analysis"
        >
          <BarChart3 className="w-3.5 h-3.5 text-amber-200" />
          <span>Executive Summary</span>
        </button>

        {/* Download Executed Protocol */}
        <button
          type="button"
          onClick={onDownloadDocx}
          disabled={!session}
          className={`font-semibold px-2.5 py-1.5 rounded-lg text-xs flex items-center space-x-1.5 shadow-xs transition-colors border ${
            !session
              ? 'bg-slate-800 text-slate-500 border-slate-700 cursor-not-allowed'
              : 'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500/80'
          }`}
          title="Download the primary executed .docx protocol (Lightweight, results only)"
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Protocol (.docx)</span>
        </button>

        {/* Download Companion Evidence Dossier */}
        <button
          type="button"
          onClick={onDownloadEvidence}
          disabled={!session}
          className={`font-semibold px-2.5 py-1.5 rounded-lg text-xs flex items-center space-x-1.5 shadow-xs transition-colors border ${
            !session
              ? 'bg-slate-800 text-slate-500 border-slate-700 cursor-not-allowed'
              : 'bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-500/80'
          }`}
          title="Download the dedicated companion evidence document with watermarked screenshots"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Evidence Dossier (.docx)</span>
        </button>
      </div>
    </header>
  );
};
