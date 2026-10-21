import React from 'react';
import { X, ExternalLink, Globe, Wifi, Monitor } from 'lucide-react';

interface LiveBrowserModalProps {
  isOpen: boolean;
  onClose: () => void;
  frameData: string | null;
  currentUrl: string;
  currentAction: string;
  isConnected: boolean;
}

export const LiveBrowserModal: React.FC<LiveBrowserModalProps> = ({
  isOpen,
  onClose,
  frameData,
  currentUrl,
  currentAction,
  isConnected,
}) => {
  if (!isOpen) return null;

  const targetUrl = currentUrl || 'https://mpv-two.vercel.app/login';

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl max-w-5xl w-full overflow-hidden flex flex-col max-h-[92vh]">
        {/* Browser Top Chrome */}
        <div className="bg-slate-950 px-4 py-2.5 flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <div className="flex space-x-1.5 mr-2">
              <div className="w-3 h-3 rounded-full bg-red-500/80" />
              <div className="w-3 h-3 rounded-full bg-amber-500/80" />
              <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
            </div>
            <Globe className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-xs font-semibold text-slate-200">Playwright Live Viewport Stream</span>
          </div>

          {/* URL Pill */}
          <div className="flex-1 max-w-md mx-4">
            <div className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1 text-xs text-slate-300 font-mono truncate flex items-center justify-between">
              <span className="truncate">{targetUrl}</span>
              <a
                href={targetUrl}
                target="_blank"
                rel="noreferrer"
                className="text-cyan-400 hover:text-cyan-300 ml-2 flex-shrink-0 flex items-center space-x-1"
                title="Open OnePV directly in a new browser window"
              >
                <span className="text-[10px]">Open Website</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1 text-[11px]">
              <Wifi className={`w-3.5 h-3.5 ${isConnected ? 'text-emerald-400' : 'text-slate-500'}`} />
              <span className={isConnected ? 'text-emerald-400 font-medium' : 'text-slate-500'}>
                {isConnected ? 'Live WebSocket Stream' : 'Ready'}
              </span>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Viewport Frame */}
        <div className="flex-1 bg-slate-950 flex items-center justify-center p-2 min-h-[500px] overflow-hidden">
          {frameData ? (
            <img
              src={`data:image/jpeg;base64,${frameData}`}
              alt="Live Browser Viewport"
              className="w-full h-auto max-h-[70vh] object-contain rounded-lg border border-slate-800 shadow-2xl"
            />
          ) : (
            <div className="text-center p-8 space-y-3 text-slate-500">
              <Monitor className="w-12 h-12 text-slate-700 mx-auto animate-pulse" />
              <p className="text-xs font-semibold text-slate-400">Playwright Chromium Viewport Stream</p>
              <p className="text-[11px] text-slate-500 max-w-sm mx-auto leading-relaxed">
                Click "Execute Automation Series" to stream automated browser actions live, or toggle "Visible Chromium ON" in the header to launch the browser visibly on your desktop.
              </p>
              <a
                href={targetUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 text-xs font-medium transition-colors"
              >
                <span>Launch OnePV in New Tab</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          )}
        </div>

        {/* Action Status Bar */}
        <div className="bg-slate-950 px-4 py-2 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-slate-300">Action:</span>
            <span className="text-cyan-400 font-mono text-[11px]">
              {currentAction || 'Ready for serial automated qualification'}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">1366 x 768 px</span>
        </div>
      </div>
    </div>
  );
};
