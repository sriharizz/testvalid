import React, { useState } from 'react';
import {
  Globe,
  Link2,
  User,
  Lock,
  Building2,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronUp,
  ClipboardPaste,
  RotateCcw,
  Sliders,
  CheckCircle2,
  Laptop,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';
import { SimulationMode } from '../types';

export interface ProductItem {
  product_id: string;
  name: string;
  description?: string;
  base_url: string;
  default_credentials?: {
    username?: string;
    password?: string;
    enterprise?: string;
  };
}

interface TargetSetupBarProps {
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
  isExecuting: boolean;
  isAuthoring: boolean;
  sessionLoaded: boolean;
  onExecute: () => void;
}

export const TargetSetupBar: React.FC<TargetSetupBarProps> = ({
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
  isExecuting,
  isAuthoring,
  sessionLoaded,
  onExecute,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [copyFeedback, setCopyFeedback] = useState<boolean>(false);

  // Handle product selection & auto-fill defaults
  const handleSelectProduct = (productId: string) => {
    onProductChange(productId);
    const prod = products.find((p) => p.product_id === productId);
    if (prod) {
      if (prod.base_url) {
        onTargetUrlChange(prod.base_url);
      }
      if (prod.default_credentials) {
        if (prod.default_credentials.username) onUsernameChange(prod.default_credentials.username);
        if (prod.default_credentials.password) onPasswordChange(prod.default_credentials.password);
        if (prod.default_credentials.enterprise) onEnterpriseChange(prod.default_credentials.enterprise);
      }
    }
  };

  // Reset URL to selected product default
  const handleResetUrl = () => {
    const prod = products.find((p) => p.product_id === selectedProduct);
    if (prod && prod.base_url) {
      onTargetUrlChange(prod.base_url);
    } else {
      onTargetUrlChange('https://mpv-two.vercel.app');
    }
  };

  // Paste from clipboard helper
  const handlePasteFromClipboard = async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        const text = await navigator.clipboard.readText();
        if (text && text.trim().startsWith('http')) {
          onTargetUrlChange(text.trim());
          setCopyFeedback(true);
          setTimeout(() => setCopyFeedback(false), 1500);
        }
      }
    } catch {
      // Browser permission denied or clipboard empty; focus input
      const el = document.getElementById('target-url-input');
      if (el) el.focus();
    }
  };

  const selectedProdObj = products.find((p) => p.product_id === selectedProduct);

  return (
    <div className="bg-[#0f1d32] border-b border-slate-700/80 text-slate-200 transition-all select-none shadow-md">
      {/* Collapsed Header / Summary Bar */}
      <div className="px-4 py-2 flex items-center justify-between text-xs">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5 font-bold text-white">
            <Globe className="w-3.5 h-3.5 text-blue-400" />
            <span className="uppercase tracking-wider text-[11px] text-blue-300 font-semibold">Target &amp; Auth Setup:</span>
          </div>

          {/* Product Pill */}
          <div className="flex items-center gap-1 bg-slate-800/90 border border-slate-700 px-2 py-0.5 rounded-md text-[11px]">
            <span className="text-slate-400">Product:</span>
            <span className="font-semibold text-cyan-300">{selectedProdObj?.name || selectedProduct}</span>
          </div>

          {/* URL Pill */}
          <div className="flex items-center gap-1 bg-slate-800/90 border border-slate-700 px-2 py-0.5 rounded-md text-[11px] font-mono max-w-xs truncate" title={targetUrl}>
            <Link2 className="w-3 h-3 text-slate-400 shrink-0" />
            <span className="text-emerald-400 truncate">{targetUrl || 'No URL specified'}</span>
          </div>

          {/* Credential Pill */}
          <div className="flex items-center gap-1 bg-slate-800/90 border border-slate-700 px-2 py-0.5 rounded-md text-[11px]">
            <User className="w-3 h-3 text-slate-400 shrink-0" />
            <span className="text-slate-300">{username}</span>
            <span className="text-slate-500">@</span>
            <span className="text-slate-400">{enterprise}</span>
          </div>

          {/* Mode Pill */}
          <div className="flex items-center gap-1 bg-slate-800/90 border border-slate-700 px-2 py-0.5 rounded-md text-[11px]">
            <span className="text-slate-400">Mode:</span>
            <span className={simMode === 'PASS' ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
              {simMode}
            </span>
          </div>
        </div>

        {/* Toggle Expand / Collapse Button */}
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer text-xs"
          title={isExpanded ? 'Collapse Setup Bar' : 'Expand Setup Controls'}
        >
          <Sliders className="w-3 h-3 text-blue-400" />
          <span>{isExpanded ? 'Hide Setup' : 'Edit Setup'}</span>
          {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      </div>

      {/* Expanded Controls Drawer */}
      {isExpanded && (
        <div className="px-4 pb-3 pt-1 border-t border-slate-800/80 bg-slate-900/95">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-end">
            
            {/* 1. Product Selection (Col 3) */}
            <div className="lg:col-span-3 space-y-1">
              <label className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
                <Globe className="w-3 h-3 text-blue-400" />
                <span>Target Product</span>
              </label>
              <select
                value={selectedProduct}
                onChange={(e) => handleSelectProduct(e.target.value)}
                disabled={isExecuting || isAuthoring}
                className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-2.5 py-1.5 text-xs font-medium focus:ring-1 focus:ring-blue-500 focus:outline-hidden"
              >
                {products.length > 0 ? (
                  products.map((p) => (
                    <option key={p.product_id} value={p.product_id}>
                      {p.name}
                    </option>
                  ))
                ) : (
                  <>
                    <option value="onepv">Clinevo OnePV</option>
                    <option value="signal">Clinevo Signal</option>
                    <option value="1pv">1PV Enterprise Core</option>
                  </>
                )}
                <option value="custom">Custom Application</option>
              </select>
            </div>

            {/* 2. Link Pasting / Target Application URL (Col 4) */}
            <div className="lg:col-span-4 space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
                  <Link2 className="w-3 h-3 text-blue-400" />
                  <span>Target Application Link / URL</span>
                </label>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={handlePasteFromClipboard}
                    disabled={isExecuting}
                    className="text-[10px] text-blue-400 hover:text-blue-300 flex items-center gap-0.5 px-1 rounded hover:bg-slate-800 transition-colors"
                    title="Paste URL from clipboard"
                  >
                    <ClipboardPaste className="w-2.5 h-2.5" />
                    <span>{copyFeedback ? 'Pasted!' : 'Paste'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleResetUrl}
                    disabled={isExecuting}
                    className="text-[10px] text-slate-400 hover:text-slate-300 flex items-center gap-0.5 px-1 rounded hover:bg-slate-800 transition-colors"
                    title="Reset to default URL for selected product"
                  >
                    <RotateCcw className="w-2.5 h-2.5" />
                    <span>Reset</span>
                  </button>
                </div>
              </div>
              <div className="relative">
                <input
                  id="target-url-input"
                  type="text"
                  value={targetUrl}
                  onChange={(e) => onTargetUrlChange(e.target.value)}
                  disabled={isExecuting || isAuthoring}
                  placeholder="https://mpv-two.vercel.app"
                  className="w-full bg-slate-800 border border-slate-700 text-emerald-300 font-mono text-xs rounded-lg pl-2.5 pr-8 py-1.5 focus:ring-1 focus:ring-blue-500 focus:outline-hidden"
                />
                <div className="absolute right-2 top-2 text-slate-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" title="Ready to target" />
                </div>
              </div>
            </div>

            {/* 3. Login Credentials: Username & Password & Enterprise (Col 5) */}
            <div className="lg:col-span-5 grid grid-cols-3 gap-2">
              
              {/* Username */}
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
                  <User className="w-3 h-3 text-blue-400" />
                  <span>Username</span>
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => onUsernameChange(e.target.value)}
                  disabled={isExecuting || isAuthoring}
                  placeholder="Username"
                  className="w-full bg-slate-800 border border-slate-700 text-white text-xs rounded-lg px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:outline-hidden"
                />
              </div>

              {/* Password with Eye Toggle */}
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
                  <Lock className="w-3 h-3 text-blue-400" />
                  <span>Password</span>
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => onPasswordChange(e.target.value)}
                    disabled={isExecuting || isAuthoring}
                    placeholder="Password"
                    className="w-full bg-slate-800 border border-slate-700 text-white text-xs rounded-lg pl-2.5 pr-7 py-1.5 focus:ring-1 focus:ring-blue-500 focus:outline-hidden"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    tabIndex={-1}
                    className="absolute right-2 top-2 text-slate-400 hover:text-slate-200"
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Enterprise / Tenant */}
              <div className="space-y-1">
                <label className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
                  <Building2 className="w-3 h-3 text-blue-400" />
                  <span>Enterprise</span>
                </label>
                <input
                  type="text"
                  value={enterprise}
                  onChange={(e) => onEnterpriseChange(e.target.value)}
                  disabled={isExecuting || isAuthoring}
                  placeholder="Enterprise"
                  className="w-full bg-slate-800 border border-slate-700 text-white text-xs rounded-lg px-2.5 py-1.5 focus:ring-1 focus:ring-blue-500 focus:outline-hidden"
                />
              </div>

            </div>

          </div>

          {/* Bottom Execution Parameters Strip */}
          <div className="mt-2.5 pt-2 border-t border-slate-800 flex items-center justify-between text-xs flex-wrap gap-2">
            
            <div className="flex items-center gap-4 flex-wrap">
              {/* Simulation Mode Selector */}
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] text-slate-400 font-medium">Validation Run Mode:</span>
                <div className="inline-flex rounded-md shadow-xs bg-slate-800 p-0.5 border border-slate-700">
                  <button
                    type="button"
                    onClick={() => onSimModeChange('PASS')}
                    disabled={isExecuting}
                    className={`px-2 py-0.5 text-[11px] font-semibold rounded transition-all ${
                      simMode === 'PASS'
                        ? 'bg-emerald-600 text-white shadow-xs'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                    title="Normal validation flow expecting positive criteria"
                  >
                    Positive (PASS)
                  </button>
                  <button
                    type="button"
                    onClick={() => onSimModeChange('FAIL')}
                    disabled={isExecuting}
                    className={`px-2 py-0.5 text-[11px] font-semibold rounded transition-all ${
                      simMode === 'FAIL'
                        ? 'bg-rose-600 text-white shadow-xs'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                    title="Simulate negative failure / discrepancy to verify Groq AI Root-Cause Diagnostic"
                  >
                    Negative Discrepancy (FAIL)
                  </button>
                </div>
              </div>

              {/* Visible Browser Window Toggle */}
              <label className="flex items-center gap-1.5 cursor-pointer text-[11px] text-slate-300 hover:text-white transition-colors">
                <input
                  type="checkbox"
                  checked={visibleBrowser}
                  onChange={(e) => onVisibleBrowserChange(e.target.checked)}
                  disabled={isExecuting}
                  className="rounded bg-slate-800 border-slate-700 text-blue-600 focus:ring-blue-500 w-3.5 h-3.5"
                />
                <Laptop className="w-3.5 h-3.5 text-blue-400" />
                <span>Launch Visible Chromium Window</span>
              </label>

              {/* Manual Login Gate Checkbox */}
              <label className="flex items-center gap-1.5 cursor-pointer text-[11px] text-slate-300 hover:text-white transition-colors">
                <input
                  type="checkbox"
                  checked={requiresApproval}
                  onChange={(e) => onRequiresApprovalChange(e.target.checked)}
                  disabled={isExecuting}
                  className="rounded bg-slate-800 border-slate-700 text-amber-500 focus:ring-amber-500 w-3.5 h-3.5"
                />
                <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                <span>Manual Login Gate (Pause for approval)</span>
              </label>
            </div>

            {/* Quick Status Pill */}
            <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>Target configured. At completion, Executive Summary opens automatically.</span>
            </div>

          </div>

        </div>
      )}
    </div>
  );
};
