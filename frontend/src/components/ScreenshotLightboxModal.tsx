import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ProtocolStep } from '../types';
import {
  X,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize2,
  ExternalLink,
  Download,
  FileSpreadsheet,
  CheckCircle,
  Layers,
  Camera,
} from 'lucide-react';

export interface LightboxData {
  step: ProtocolStep;
  activeType?: 'form' | 'modal' | 'combined';
  overrideUrl?: string;
}

interface ScreenshotLightboxModalProps {
  data: LightboxData | null;
  onClose: () => void;
}

export const ScreenshotLightboxModal: React.FC<ScreenshotLightboxModalProps> = ({
  data,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'form' | 'modal' | 'combined'>('form');
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [panPosition, setPanPosition] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const imgContainerRef = useRef<HTMLDivElement>(null);

  const step = data?.step;

  // Determine available screenshot options for this step
  const formUrl = step?.form_screenshot_url || (step?.screenshot_url?.includes('_form.png') ? step.screenshot_url : null);
  const modalUrl = step?.modal_screenshot_url || (step?.screenshot_url?.includes('_modal.png') ? step.screenshot_url : null);
  const combinedUrl = step?.screenshot_url;

  // Has dual screenshots?
  const hasDual = Boolean(formUrl && modalUrl);

  // Initialize active tab on open
  useEffect(() => {
    if (!data) return;
    if (data.activeType) {
      setActiveTab(data.activeType);
    } else if (hasDual) {
      setActiveTab('form');
    } else {
      setActiveTab('combined');
    }
    setZoomLevel(100);
    setPanPosition({ x: 0, y: 0 });
  }, [data, hasDual]);

  // Current active image URL
  const currentImageUrl = (() => {
    if (data?.overrideUrl && !hasDual) return data.overrideUrl;
    if (activeTab === 'form' && formUrl) return formUrl;
    if (activeTab === 'modal' && modalUrl) return modalUrl;
    if (activeTab === 'combined' && combinedUrl) return combinedUrl;
    return formUrl || modalUrl || combinedUrl || data?.overrideUrl || '';
  })();

  // Zoom helpers
  const handleZoomIn = useCallback(() => {
    setZoomLevel((prev) => Math.min(prev + 25, 350));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoomLevel((prev) => Math.max(prev - 25, 50));
  }, []);

  const handleResetZoom = useCallback(() => {
    setZoomLevel(100);
    setPanPosition({ x: 0, y: 0 });
  }, []);

  const handleFitToScreen = useCallback(() => {
    setZoomLevel(85);
    setPanPosition({ x: 0, y: 0 });
  }, []);

  // Double click toggles between fit & 175% zoom
  const handleDoubleClick = () => {
    if (zoomLevel > 110) {
      handleResetZoom();
    } else {
      setZoomLevel(175);
    }
  };

  // Mouse wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      setZoomLevel((prev) => Math.min(prev + 15, 350));
    } else {
      setZoomLevel((prev) => Math.max(prev - 15, 50));
    }
  };

  // Mouse drag pan
  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoomLevel <= 100) return;
    setIsDragging(true);
    dragStartRef.current = {
      x: e.clientX - panPosition.x,
      y: e.clientY - panPosition.y,
    };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPanPosition({
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Keyboard navigation
  useEffect(() => {
    if (!data) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === '+' || e.key === '=') {
        handleZoomIn();
      } else if (e.key === '-' || e.key === '_') {
        handleZoomOut();
      } else if (e.key === '0') {
        handleResetZoom();
      } else if (e.key === 'ArrowRight' && hasDual) {
        setActiveTab((prev) => (prev === 'form' ? 'modal' : 'form'));
        setPanPosition({ x: 0, y: 0 });
      } else if (e.key === 'ArrowLeft' && hasDual) {
        setActiveTab((prev) => (prev === 'modal' ? 'form' : 'modal'));
        setPanPosition({ x: 0, y: 0 });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [data, hasDual, onClose, handleZoomIn, handleZoomOut, handleResetZoom]);

  if (!data || !step) return null;

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-black/85 backdrop-blur-xs flex items-center justify-center p-3 sm:p-5 select-none animate-in fade-in duration-150"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl max-w-6xl w-full flex flex-col h-[92vh] overflow-hidden"
      >
        {/* Header Bar */}
        <div className="bg-[#0b192c] text-white px-5 py-3 border-b border-slate-800 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center space-x-3 truncate">
            <div className="p-2 bg-blue-600/20 text-cyan-400 rounded-lg border border-cyan-500/30">
              <Camera className="w-4 h-4" />
            </div>
            <div className="truncate">
              <div className="flex items-center space-x-2">
                <span className="font-mono font-bold text-xs bg-slate-800 px-2 py-0.5 rounded text-cyan-300 border border-slate-700">
                  {step.step_id}
                </span>
                <span className="text-xs font-semibold text-slate-200 truncate">
                  {step.scenario}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 truncate mt-0.5">
                {step.procedure}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <a
              href={currentImageUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-all text-xs flex items-center space-x-1"
              title="Open Full Resolution in New Tab"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Full Size</span>
            </a>
            <a
              href={currentImageUrl}
              download={`${step.step_id}_${activeTab}.png`}
              className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-all text-xs flex items-center space-x-1"
              title="Download Screenshot"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Save</span>
            </a>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-red-900/60 text-slate-400 hover:text-red-200 transition-all cursor-pointer ml-1"
              title="Close (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Toolbar: Screenshot Switcher Tabs & Zoom Controls */}
        <div className="bg-slate-950 px-5 py-2.5 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 flex-shrink-0">
          {/* Individual Screenshot Selector Tabs */}
          {hasDual ? (
            <div className="flex items-center bg-slate-900 p-1 rounded-xl border border-slate-700/80">
              <button
                type="button"
                onClick={() => {
                  setActiveTab('form');
                  setPanPosition({ x: 0, y: 0 });
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all cursor-pointer ${
                  activeTab === 'form'
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>1. Form Populated State</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('modal');
                  setPanPosition({ x: 0, y: 0 });
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all cursor-pointer ${
                  activeTab === 'modal'
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                <CheckCircle className="w-3.5 h-3.5" />
                <span>2. Confirmation Dialog</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setActiveTab('combined');
                  setPanPosition({ x: 0, y: 0 });
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all cursor-pointer ${
                  activeTab === 'combined'
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30 font-bold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Composite View</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span>Step Evidence Screenshot</span>
            </div>
          )}

          {/* Interactive Zoom Controls */}
          <div className="flex items-center space-x-2 bg-slate-900 px-3 py-1 rounded-xl border border-slate-700/80 text-xs">
            <span className="text-slate-400 text-[11px] font-medium mr-1">Zoom:</span>
            <button
              type="button"
              onClick={handleZoomOut}
              disabled={zoomLevel <= 50}
              className="p-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white disabled:opacity-40 cursor-pointer"
              title="Zoom Out (-)"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="font-mono text-cyan-300 text-xs w-12 text-center font-bold">
              {zoomLevel}%
            </span>
            <button
              type="button"
              onClick={handleZoomIn}
              disabled={zoomLevel >= 350}
              className="p-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white disabled:opacity-40 cursor-pointer"
              title="Zoom In (+)"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <div className="w-[1px] h-4 bg-slate-700 mx-1" />
            <button
              type="button"
              onClick={handleFitToScreen}
              className="px-2 py-0.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white text-[11px] font-medium cursor-pointer"
              title="Fit to Window"
            >
              <Maximize2 className="w-3 h-3 inline mr-1" />
              Fit
            </button>
            <button
              type="button"
              onClick={handleResetZoom}
              className="px-2 py-0.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white text-[11px] font-medium cursor-pointer"
              title="Reset to 100% (0)"
            >
              <RotateCcw className="w-3 h-3 inline mr-1" />
              100%
            </button>
          </div>
        </div>

        {/* Zoomable Image Viewport Canvas */}
        <div
          ref={imgContainerRef}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onDoubleClick={handleDoubleClick}
          className={`flex-1 bg-slate-950 flex items-center justify-center overflow-hidden p-4 relative ${
            zoomLevel > 100
              ? isDragging
                ? 'cursor-grabbing'
                : 'cursor-grab'
              : 'cursor-zoom-in'
          }`}
          title="Scroll to zoom in/out, drag to pan when zoomed, double-click to toggle zoom"
        >
          {currentImageUrl ? (
            <div
              style={{
                transform: `translate(${panPosition.x}px, ${panPosition.y}px) scale(${zoomLevel / 100})`,
                transition: isDragging ? 'none' : 'transform 0.15s ease-out',
                transformOrigin: 'center center',
              }}
              className="flex items-center justify-center max-w-full max-h-full"
            >
              <img
                src={currentImageUrl}
                alt={`${step.step_id} - ${activeTab}`}
                draggable={false}
                className="max-w-[90vw] max-h-[72vh] object-contain rounded-lg shadow-2xl border border-slate-800 select-none pointer-events-none"
              />
            </div>
          ) : (
            <div className="text-slate-500 text-xs font-medium">No screenshot available</div>
          )}

          {/* Quick Floating Hint Overlay */}
          <div className="absolute bottom-3 left-4 bg-slate-900/80 backdrop-blur-xs text-[11px] text-slate-400 px-3 py-1 rounded-full border border-slate-800 pointer-events-none">
            💡 Scroll wheel to zoom • Drag to pan • Double click to toggle
          </div>
        </div>

        {/* Footer Details */}
        <div className="bg-[#0b192c] px-5 py-2.5 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 flex-shrink-0">
          <div className="flex items-center space-x-3">
            <span>
              Status:{' '}
              <strong
                className={
                  step.status === 'PASS'
                    ? 'text-emerald-400'
                    : step.status === 'FAIL'
                    ? 'text-red-400'
                    : 'text-amber-400'
                }
              >
                {step.status}
              </strong>
            </span>
            <span>•</span>
            <span className="truncate max-w-md">
              Observed: <span className="text-slate-300">{step.observed_result || 'Verified'}</span>
            </span>
          </div>
          <div className="font-mono text-[11px] text-slate-400">
            Sign-off: {step.initials_date || 'S.B. / 15-Oct-2026'}
          </div>
        </div>
      </div>
    </div>
  );
};
