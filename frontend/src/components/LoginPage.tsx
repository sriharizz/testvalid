import React, { useState } from 'react';
import {
  Globe,
  Link2,
  User,
  Lock,
  Building2,
  Eye,
  EyeOff,
  FolderKanban,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  ClipboardPaste,
  RotateCcw,
  Laptop,
  Layers,
  Sparkles,
  Zap,
  Server
} from 'lucide-react';
import { SimulationMode } from '../types';
import { ProductItem } from './TargetSetupBar';

interface LoginPageProps {
  products: ProductItem[];
  selectedProduct: string;
  onProductChange: (productId: string) => void;
  targetUrl: string;
  onTargetUrlChange: (url: string) => void;
  username: string;
  onUsernameChange: (val: string) => void;
  password: string;
  onPasswordChange: (val: string) => void;
  enterprise: string;
  onEnterpriseChange: (val: string) => void;
  simMode: SimulationMode;
  onSimModeChange: (mode: SimulationMode) => void;
  visibleBrowser: boolean;
  onVisibleBrowserChange: (val: boolean) => void;
  requiresApproval: boolean;
  onRequiresApprovalChange: (val: boolean) => void;
  onProceedToFolders: () => void;
  onProceedToWorkspace: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({
  products,
  selectedProduct,
  onProductChange,
  targetUrl,
  onTargetUrlChange,
  username,
  onUsernameChange,
  password,
  onPasswordChange,
  enterprise,
  onEnterpriseChange,
  simMode,
  onSimModeChange,
  visibleBrowser,
  onVisibleBrowserChange,
  requiresApproval,
  onRequiresApprovalChange,
  onProceedToFolders,
  onProceedToWorkspace,
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const [pastedFeedback, setPastedFeedback] = useState(false);

  const handleSelectProduct = (productId: string) => {
    onProductChange(productId);
    const prod = products.find((p) => p.product_id === productId);
    if (prod) {
      if (prod.base_url) onTargetUrlChange(prod.base_url);
      if (prod.default_credentials) {
        if (prod.default_credentials.username) onUsernameChange(prod.default_credentials.username);
        if (prod.default_credentials.password) onPasswordChange(prod.default_credentials.password);
        if (prod.default_credentials.enterprise) onEnterpriseChange(prod.default_credentials.enterprise);
      }
    }
  };

  const handleResetUrl = () => {
    const prod = products.find((p) => p.product_id === selectedProduct);
    onTargetUrlChange(prod?.base_url || 'https://mpv-two.vercel.app');
  };

  const handlePasteClipboard = async () => {
    try {
      if (navigator.clipboard?.readText) {
        const text = await navigator.clipboard.readText();
        if (text && text.trim().startsWith('http')) {
          onTargetUrlChange(text.trim());
          setPastedFeedback(true);
          setTimeout(() => setPastedFeedback(false), 1500);
        }
      }
    } catch {
      const el = document.getElementById('login-target-url-input');
      if (el) el.focus();
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 bg-gradient-to-b from-[#0b192c] via-[#0f2444] to-[#0b192c] text-slate-100 overflow-y-auto">
      <div className="max-w-3xl w-full bg-slate-900/90 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-md">
        
        {/* Banner Header */}
        <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-blue-800 p-6 text-white border-b border-blue-500/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3.5">
              <div className="w-12 h-12 rounded-xl bg-white/10 border border-white/20 flex items-center justify-center shadow-lg">
                <ShieldCheck className="w-7 h-7 text-cyan-300" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xl font-bold tracking-tight">Clinevo Validation Automation Platform</span>
                  <span className="px-2 py-0.5 text-[10px] font-bold bg-white/20 rounded-full tracking-wider uppercase">
                    21 CFR Part 11
                  </span>
                </div>
                <p className="text-xs text-blue-100/90 mt-0.5">
                  Automated Qualification &amp; Evidence Generation for Computer Systems Validation (CSV)
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Configuration Body */}
        <div className="p-6 space-y-6">

          {/* 1. Product Selection Grid */}
          <div>
            <label className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5 mb-2.5">
              <Globe className="w-3.5 h-3.5 text-blue-400" />
              <span>Step 1: Select Target Product</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {products.length > 0 ? (
                products.map((p) => {
                  const isSelected = selectedProduct === p.product_id;
                  return (
                    <button
                      key={p.product_id}
                      type="button"
                      onClick={() => handleSelectProduct(p.product_id)}
                      className={`p-3 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between ${
                        isSelected
                          ? 'bg-blue-600/20 border-blue-500 text-white shadow-md shadow-blue-500/10 ring-1 ring-blue-500'
                          : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-800 hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-xs">{p.name}</span>
                        {isSelected && <CheckCircle2 className="w-4 h-4 text-cyan-400" />}
                      </div>
                      <span className="text-[11px] text-slate-400 line-clamp-2 leading-tight">
                        {p.description || p.base_url}
                      </span>
                    </button>
                  );
                })
              ) : (
                <div className="text-xs text-slate-400">Loading products...</div>
              )}
            </div>
          </div>

          {/* 2. Target Application URL Pasting */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                <Link2 className="w-3.5 h-3.5 text-blue-400" />
                <span>Step 2: Target Application URL / Link</span>
              </label>
              <div className="flex items-center gap-1.5 text-xs">
                <button
                  type="button"
                  onClick={handlePasteClipboard}
                  className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-blue-400 hover:text-blue-300 text-[11px] font-medium flex items-center gap-1 transition-colors"
                >
                  <ClipboardPaste className="w-3 h-3" />
                  <span>{pastedFeedback ? 'Pasted!' : 'Paste from Clipboard'}</span>
                </button>
                <button
                  type="button"
                  onClick={handleResetUrl}
                  className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 text-[11px] font-medium flex items-center gap-1 transition-colors"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Reset Default</span>
                </button>
              </div>
            </div>
            <div className="relative">
              <input
                id="login-target-url-input"
                type="text"
                value={targetUrl}
                onChange={(e) => onTargetUrlChange(e.target.value)}
                placeholder="https://mpv-two.vercel.app"
                className="w-full bg-slate-800/90 border border-slate-700 text-emerald-300 font-mono text-xs rounded-xl pl-3 pr-10 py-2.5 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
              />
              <div className="absolute right-3 top-3">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 inline-block animate-pulse" title="Target Active" />
              </div>
            </div>
          </div>

          {/* 3. Credentials Form */}
          <div>
            <label className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5 mb-2.5">
              <User className="w-3.5 h-3.5 text-blue-400" />
              <span>Step 3: Authentication Credentials</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Username */}
              <div className="space-y-1">
                <span className="text-[11px] font-medium text-slate-400">Username</span>
                <div className="relative">
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => onUsernameChange(e.target.value)}
                    placeholder="Username"
                    className="w-full bg-slate-800/90 border border-slate-700 text-white text-xs rounded-xl pl-3 pr-3 py-2.5 focus:ring-1 focus:ring-blue-500 focus:outline-hidden"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-1">
                <span className="text-[11px] font-medium text-slate-400">Password</span>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => onPasswordChange(e.target.value)}
                    placeholder="Password"
                    className="w-full bg-slate-800/90 border border-slate-700 text-white text-xs rounded-xl pl-3 pr-9 py-2.5 focus:ring-1 focus:ring-blue-500 focus:outline-hidden"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-slate-400 hover:text-slate-200"
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Enterprise */}
              <div className="space-y-1">
                <span className="text-[11px] font-medium text-slate-400">Enterprise / Tenant</span>
                <div className="relative">
                  <input
                    type="text"
                    value={enterprise}
                    onChange={(e) => onEnterpriseChange(e.target.value)}
                    placeholder="Enterprise"
                    className="w-full bg-slate-800/90 border border-slate-700 text-white text-xs rounded-xl pl-3 pr-3 py-2.5 focus:ring-1 focus:ring-blue-500 focus:outline-hidden"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* 4. Execution Preferences */}
          <div className="pt-2 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-4 flex-wrap">
              {/* Simulation Mode */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-slate-400">Run Mode:</span>
                <div className="inline-flex rounded-lg bg-slate-800 p-0.5 border border-slate-700">
                  <button
                    type="button"
                    onClick={() => onSimModeChange('PASS')}
                    className={`px-2.5 py-1 text-[11px] font-semibold rounded-md transition-all ${
                      simMode === 'PASS' ? 'bg-emerald-600 text-white shadow-xs' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Positive (PASS)
                  </button>
                  <button
                    type="button"
                    onClick={() => onSimModeChange('FAIL')}
                    className={`px-2.5 py-1 text-[11px] font-semibold rounded-md transition-all ${
                      simMode === 'FAIL' ? 'bg-rose-600 text-white shadow-xs' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Negative Discrepancy (FAIL)
                  </button>
                </div>
              </div>

              {/* Visible Browser */}
              <label className="flex items-center gap-1.5 cursor-pointer text-[11px] text-slate-300 hover:text-white">
                <input
                  type="checkbox"
                  checked={visibleBrowser}
                  onChange={(e) => onVisibleBrowserChange(e.target.checked)}
                  className="rounded bg-slate-800 border-slate-700 text-blue-600 focus:ring-blue-500"
                />
                <Laptop className="w-3.5 h-3.5 text-blue-400" />
                <span>Launch Visible Chromium Window</span>
              </label>
            </div>
          </div>

          {/* Action CTAs */}
          <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Target link &amp; credentials validated for qualification run.</span>
            </div>

            <div className="flex items-center gap-2.5 w-full sm:w-auto">
              <button
                type="button"
                onClick={onProceedToFolders}
                className="flex-1 sm:flex-initial px-4 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2 shadow transition-all cursor-pointer"
              >
                <FolderKanban className="w-4 h-4 text-amber-400" />
                <span>Open Project Folders (OQ / PQ)</span>
                <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </button>

              <button
                type="button"
                onClick={onProceedToWorkspace}
                className="flex-1 sm:flex-initial px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-blue-600/30 transition-all cursor-pointer"
              >
                <Zap className="w-4 h-4 fill-amber-300 text-amber-300" />
                <span>Enter Validation Studio</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
};
