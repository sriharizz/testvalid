import React, { useEffect, useRef, useState, useCallback } from 'react';
import { ProtocolSession, ProtocolStep } from '../types';
import { renderAsync } from 'docx-preview';
import { ScreenshotLightboxModal, LightboxData } from './ScreenshotLightboxModal';
import {
  FileText,
  Camera,
  X,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  FileCheck2,
  Table as TableIcon,
  Scan,
  RotateCcw,
  Loader2,
} from 'lucide-react';

interface RightDocInspectorProps {
  session: ProtocolSession | null;
  rawDocxBuffer: ArrayBuffer | null;
  selectedStepId: string | null;
  onSelectStep: (stepId: string) => void;
  isExecuting?: boolean;
  onOpenLightbox?: (step: ProtocolStep, type?: 'form' | 'modal' | 'combined', overrideUrl?: string) => void;
}

export const RightDocInspector: React.FC<RightDocInspectorProps> = ({
  session,
  rawDocxBuffer,
  selectedStepId,
  onSelectStep,
  isExecuting,
  onOpenLightbox,
}) => {
  const docxContainerRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const renderedBufferRef = useRef<ArrayBuffer | null>(null);

  const [zoomLevel, setZoomLevel] = useState<number>(75);
  const [viewMode, setViewMode] = useState<'docx' | 'matrix'>('docx');
  const [isRenderingDocx, setIsRenderingDocx] = useState<boolean>(false);
  const [isMaximized, setIsMaximized] = useState<boolean>(false);
  const [lightboxState, setLightboxState] = useState<LightboxData | null>(null);

  const filename = session?.filename || 'protocol.docx';

  // 1. Auto-fit document to available container width
  const fitToWidth = useCallback(() => {
    if (!scrollContainerRef.current) return;
    const availableWidth = scrollContainerRef.current.clientWidth - 48; // padding margin
    const standardDocxWidth = 816; // Standard Word Letter/A4 page in 96 DPI
    const calculated = Math.min(125, Math.max(45, Math.floor((availableWidth / standardDocxWidth) * 100)));
    setZoomLevel(calculated);
  }, []);

  // 2. Smoothly scroll to a specific step row in the rendered Word document
  const scrollToStepRow = useCallback((stepId: string) => {
    if (!scrollContainerRef.current || !docxContainerRef.current) return;

    // Find row by data-step-id or step text
    const targetTr = docxContainerRef.current.querySelector(
      `tr[data-step-id="${stepId}"]`
    ) as HTMLTableRowElement | null;

    if (!targetTr) return;

    const container = scrollContainerRef.current;
    const containerRect = container.getBoundingClientRect();
    const rowRect = targetTr.getBoundingClientRect();

    const currentScrollTop = container.scrollTop;
    const rowRelativeTop = rowRect.top - containerRect.top + currentScrollTop;
    const targetScrollTop = Math.max(0, rowRelativeTop - container.clientHeight / 2 + rowRect.height / 2);

    container.scrollTo({
      top: targetScrollTop,
      behavior: 'smooth',
    });
  }, []);

  // 3. Update table DOM in-situ with execution details (Pass/Fail, Initials, Date, Screenshots)
  const updateDocxDomWithExecutionDetails = useCallback(() => {
    if (!docxContainerRef.current || !session) return;

    const tables = Array.from(docxContainerRef.current.querySelectorAll('table'));
    if (tables.length === 0) return;

    interface ExecTableRow {
      tr: HTMLTableRowElement;
      passFailIdx: number;
      initialsIdx: number;
    }

    const allStepRows: ExecTableRow[] = [];

    // Find ALL execution tables across the document (Table 5, Table 8, etc.)
    for (const table of tables) {
      const rows = Array.from(table.querySelectorAll('tr'));
      let headerRowIdx = -1;
      let passFailIdx = 4;
      let initialsIdx = 5;

      for (let r = 0; r < rows.length; r++) {
        const rowText = (rows[r].textContent || '').toLowerCase();
        if (
          (rowText.includes('procedure') || rowText.includes('scenario') || rowText.includes('action')) &&
          (rowText.includes('expected') || rowText.includes('result'))
        ) {
          headerRowIdx = r;
          const hCells = Array.from(rows[r].querySelectorAll('th, td'));
          hCells.forEach((c, cIdx) => {
            const ct = (c.textContent || '').toLowerCase();
            if (ct.includes('pass') || ct.includes('observed result') || ct.includes('match expected')) {
              passFailIdx = cIdx;
            } else if (ct.includes('initial') || ct.includes('date')) {
              initialsIdx = cIdx;
            }
          });
          break;
        }
      }

      // If execution table found, collect its step rows
      if (headerRowIdx !== -1) {
        for (let r = headerRowIdx + 1; r < rows.length; r++) {
          const tr = rows[r];
          const text = (tr.textContent || '').toLowerCase().trim();
          if (!text) continue;
          if (
            text.startsWith('comments') ||
            text.startsWith('deviations') ||
            text.startsWith('executed by') ||
            text.startsWith('reviewed by') ||
            text.startsWith('acceptance criteria') ||
            text.startsWith('acceptance criteria met')
          ) {
            continue;
          }
          if (tr.querySelectorAll('td').length >= 3) {
            allStepRows.push({ tr, passFailIdx, initialsIdx });
          }
        }
      }
    }

    // Fallback: if no tables found via header text, grab large tables
    if (allStepRows.length === 0) {
      for (const table of tables) {
        const rows = Array.from(table.querySelectorAll('tr'));
        if (rows.length >= 6) {
          for (let r = 1; r < rows.length; r++) {
            const tr = rows[r];
            const text = (tr.textContent || '').toLowerCase().trim();
            if (
              !text ||
              text.startsWith('comments') ||
              text.startsWith('deviations') ||
              text.startsWith('executed by') ||
              text.startsWith('reviewed by')
            ) {
              continue;
            }
            if (tr.querySelectorAll('td').length >= 3) {
              allStepRows.push({ tr, passFailIdx: 4, initialsIdx: 5 });
            }
          }
        }
      }
    }

    if (allStepRows.length === 0) return;

    // Populate each step row with execution status, initials, and results
    allStepRows.forEach(({ tr, passFailIdx, initialsIdx }, stepIdx) => {
      if (stepIdx >= session.steps.length) return;
      const step = session.steps[stepIdx];
      tr.setAttribute('data-step-id', step.step_id);

      tr.style.cursor = 'pointer';
      tr.onclick = (e) => {
        // Prevent lightbox clicks from re-selecting step
        if ((e.target as HTMLElement).tagName === 'IMG') return;
        onSelectStep(step.step_id);
      };

      // Highlight selected step row
      if (step.step_id === selectedStepId) {
        tr.style.outline = '2px solid #1d63dc';
        tr.style.backgroundColor = 'rgba(29, 99, 220, 0.08)';
      } else {
        tr.style.outline = 'none';
        if (step.status === 'QUEUED') {
          tr.style.backgroundColor = '';
        } else {
          tr.style.backgroundColor = 'rgba(248, 250, 252, 0.5)';
        }
      }

      const cells = Array.from(tr.querySelectorAll('td'));
      if (cells.length < 3) return;

      // Safe column bounds check for Pass/Fail & Initials
      const actualPfIdx =
        cells.length > passFailIdx ? passFailIdx : cells.length === 5 ? 3 : cells.length - 2;
      const actualInitIdx =
        cells.length > initialsIdx ? initialsIdx : cells.length === 5 ? 4 : cells.length - 1;

      // In-situ natural black ink Pass/Fail stamp
      if (cells.length > actualPfIdx && step.status !== 'QUEUED') {
        const passFailCell = cells[actualPfIdx];
        if (passFailCell) {
          passFailCell.style.textAlign = 'center';
          passFailCell.style.verticalAlign = 'top';

          if (step.status === 'PASS') {
            passFailCell.innerHTML = `
              <div style="font-weight: 700; color: #0f172a; font-size: 11px; font-family: Calibri, Arial, sans-serif;">Pass</div>
              <div style="font-size: 9.5px; color: #334155; margin-top: 3px; line-height: 1.25; font-family: Calibri, Arial, sans-serif;">${step.observed_result || 'Verified successfully.'}</div>
            `;
          } else if (step.status === 'FAIL') {
            passFailCell.innerHTML = `
              <div style="font-weight: 700; color: #0f172a; font-size: 11px; font-family: Calibri, Arial, sans-serif;">Fail</div>
              <div style="font-size: 9.5px; color: #334155; margin-top: 3px; line-height: 1.25; font-family: Calibri, Arial, sans-serif;">${step.observed_result || 'Assertion Failed.'}</div>
            `;
          } else if (step.status === 'BLOCKED') {
            passFailCell.innerHTML = `
              <div style="font-weight: 700; color: #0f172a; font-size: 11px; font-family: Calibri, Arial, sans-serif;">Blocked</div>
              <div style="font-size: 9.5px; color: #334155; margin-top: 3px; font-family: Calibri, Arial, sans-serif;">${step.observed_result || 'Halted'}</div>
            `;
          } else if (step.status === 'EXECUTING') {
            passFailCell.innerHTML = `
              <div style="font-weight: 600; color: #0f172a; font-size: 10px; font-family: Calibri, Arial, sans-serif; font-style: italic;">Running...</div>
            `;
          }
        }
      }

      // In-situ Initials & Date (Strict text-only sign-off per user mandate)
      if (cells.length > actualInitIdx && step.status !== 'QUEUED') {
        const initialsCell = cells[actualInitIdx];
        if (initialsCell) {
          initialsCell.style.textAlign = 'center';
          initialsCell.style.verticalAlign = 'top';
          initialsCell.innerHTML = `<div style="font-weight: 700; font-size: 10px; color: #0f172a; font-family: Calibri, Arial, sans-serif;">${step.initials_date || 'S.B. / 15-Oct-2026'}</div>`;
        }
      }
    });

    // Attach reliable event listeners to all evidence thumbnails
    const thumbs = docxContainerRef.current.querySelectorAll('.evidence-thumb');
    thumbs.forEach((thumb) => {
      (thumb as HTMLElement).onclick = (e) => {
        e.stopPropagation();
        e.preventDefault();
        const stepId = thumb.getAttribute('data-step-id');
        const type = (thumb.getAttribute('data-type') || 'form') as 'form' | 'modal' | 'combined';
        const url = thumb.getAttribute('data-url') || '';
        const targetStep = session.steps.find((s) => s.step_id === stepId);
        if (targetStep) {
          if (onOpenLightbox) {
            onOpenLightbox(targetStep, type, url);
          } else {
            setLightboxState({ step: targetStep, activeType: type, overrideUrl: url });
          }
        }
      };
    });
  }, [session, selectedStepId, onSelectStep, onOpenLightbox]);

  // 4. One-time Render of uploaded .docx (ONLY when rawDocxBuffer changes, NEVER on step clicks!)
  useEffect(() => {
    if (!rawDocxBuffer || !docxContainerRef.current || viewMode !== 'docx') {
      return;
    }

    // Skip if already rendered this exact buffer
    if (renderedBufferRef.current === rawDocxBuffer && docxContainerRef.current.children.length > 0) {
      updateDocxDomWithExecutionDetails();
      if (selectedStepId) {
        scrollToStepRow(selectedStepId);
      }
      return;
    }

    let isMounted = true;
    setIsRenderingDocx(true);
    docxContainerRef.current.innerHTML = '';

    renderAsync(rawDocxBuffer, docxContainerRef.current, undefined, {
      inWrapper: true,
      ignoreWidth: false,
      breakPages: true,
      renderHeaders: true,
      renderFooters: true,
    })
      .then(() => {
        if (!isMounted || !docxContainerRef.current) return;
        renderedBufferRef.current = rawDocxBuffer;
        setIsRenderingDocx(false);

        // Auto-fit to width on initial render
        fitToWidth();

        // Populate execution details
        updateDocxDomWithExecutionDetails();

        // Scroll to active step if one is selected
        if (selectedStepId) {
          setTimeout(() => scrollToStepRow(selectedStepId), 100);
        }
      })
      .catch((err) => {
        console.error('Error rendering uploaded .docx with docx-preview:', err);
        if (isMounted) setIsRenderingDocx(false);
      });

    return () => {
      isMounted = false;
    };
  }, [rawDocxBuffer, viewMode, fitToWidth, updateDocxDomWithExecutionDetails, scrollToStepRow, selectedStepId]);

  // 5. In-situ update and scroll when step or session changes (Instantaneous, ZERO re-rendering)
  useEffect(() => {
    if (session && docxContainerRef.current && docxContainerRef.current.children.length > 0) {
      updateDocxDomWithExecutionDetails();
      if (selectedStepId) {
        scrollToStepRow(selectedStepId);
      }
    }
  }, [session, selectedStepId, updateDocxDomWithExecutionDetails, scrollToStepRow]);

  // 6. Window resize listener for responsive fit
  useEffect(() => {
    const handleResize = () => {
      if (!isMaximized) {
        fitToWidth();
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [fitToWidth, isMaximized]);

  // 7. Lightbox global helper
  useEffect(() => {
    (window as any).__openLightbox = (url: string, stepId: string, _scenario?: string) => {
      const targetStep = session?.steps.find((s) => s.step_id === stepId);
      if (targetStep) {
        const type = url.includes('_modal') ? 'modal' : url.includes('_form') ? 'form' : 'combined';
        if (onOpenLightbox) {
          onOpenLightbox(targetStep, type, url);
        } else {
          setLightboxState({ step: targetStep, activeType: type, overrideUrl: url });
        }
      }
    };
    return () => {
      delete (window as any).__openLightbox;
    };
  }, [session, onOpenLightbox]);

  // 8. Escape key to exit fullscreen mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (lightboxState) {
          setLightboxState(null);
        } else if (isMaximized) {
          setIsMaximized(false);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMaximized, lightboxState]);

  // CASE 1: No document ingested
  if (!session) {
    return (
      <section className="flex-1 flex flex-col bg-slate-100 h-[calc(100vh-3.5rem)] overflow-hidden select-none">
        <div className="bg-white px-4 py-2 border-b border-slate-200 flex items-center justify-between shadow-xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
            ACTIVE PROTOCOL DOCUMENT INSPECTOR
          </h2>
          <span className="text-[11px] text-slate-400 font-medium">No Document Ingested</span>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-slate-50">
          <div className="w-16 h-16 rounded-2xl bg-white border border-slate-300 shadow-sm flex items-center justify-center mb-4 text-slate-400">
            <FileText className="w-8 h-8 stroke-[1.5]" />
          </div>
          <h3 className="text-sm font-bold text-slate-700">Awaiting Protocol Document Ingestion</h3>
          <p className="text-xs text-slate-500 max-w-sm mt-1.5 leading-relaxed">
            Upload your Microsoft Word validation protocol (.docx) in the top header. The exact uploaded document will be rendered and filled here in real time.
          </p>
        </div>
      </section>
    );
  }

  // Common Header & Toolbar Component
  const renderHeaderAndToolbar = () => (
    <>
      {/* Top Header & View Switcher */}
      <div className="bg-white px-4 py-2 border-b border-slate-200 flex items-center justify-between shadow-xs">
        <div className="flex items-center space-x-3 truncate">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800 truncate">
            ACTIVE PROTOCOL INSPECTOR — <span className="text-[#1d63dc]">{filename}</span>
          </h2>
          {selectedStepId && (
            <span className="text-[11px] bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded font-mono font-semibold">
              Step: {selectedStepId}
            </span>
          )}
          {isRenderingDocx && (
            <span className="flex items-center space-x-1.5 text-[11px] text-[#1d63dc] bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Rendering Document...</span>
            </span>
          )}
        </div>

        {/* View Switcher: Authentic Docx vs Synced Table Matrix */}
        <div className="flex items-center space-x-2">
          <div className="bg-slate-100 p-0.5 rounded-lg border border-slate-200 flex items-center text-xs">
            <button
              type="button"
              onClick={() => setViewMode('docx')}
              className={`px-2.5 py-1 rounded-md font-semibold flex items-center space-x-1.5 transition-all ${
                viewMode === 'docx'
                  ? 'bg-white text-[#1d63dc] shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Uploaded Word Doc</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('matrix')}
              className={`px-2.5 py-1 rounded-md font-semibold flex items-center space-x-1.5 transition-all ${
                viewMode === 'matrix'
                  ? 'bg-white text-[#1d63dc] shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Execution Matrix</span>
            </button>
          </div>
        </div>
      </div>

      {/* Toolbar: Auto-Fit, Zoom Controls, Maximize / Minimize */}
      <div className="bg-slate-100/90 border-b border-slate-200 px-3 py-1.5 flex items-center justify-between text-xs text-slate-700">
        <span className="text-[11px] font-medium text-slate-600">
          {session.total_steps} Steps Extracted | {session.total_screenshots} Evidence Points
        </span>

        {/* Zoom Controls & Maximize */}
        <div className="flex items-center space-x-1.5">
          <button
            type="button"
            onClick={fitToWidth}
            className="px-2 py-0.5 hover:bg-slate-200 text-slate-700 font-semibold rounded text-[11px] flex items-center space-x-1 border border-slate-300 shadow-2xs"
            title="Auto-Fit Document to Screen Width"
          >
            <Scan className="w-3 h-3 text-[#1d63dc]" />
            <span>Fit Width</span>
          </button>

          <div className="h-3.5 w-px bg-slate-300 mx-0.5" />

          <button
            type="button"
            onClick={() => setZoomLevel((z) => Math.max(45, z - 10))}
            className="p-1 hover:bg-slate-200 rounded text-slate-600"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-[11px] font-semibold text-slate-800 min-w-[36px] text-center font-mono">
            {zoomLevel}%
          </span>
          <button
            type="button"
            onClick={() => setZoomLevel((z) => Math.min(150, z + 10))}
            className="p-1 hover:bg-slate-200 rounded text-slate-600"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>

          <button
            type="button"
            onClick={() => setZoomLevel(100)}
            className="px-1.5 py-0.5 hover:bg-slate-200 text-slate-600 rounded text-[11px] font-mono"
            title="Reset to 100% Zoom"
          >
            100%
          </button>

          <div className="h-3.5 w-px bg-slate-300 mx-0.5" />

          {/* Maximize / Minimize Button */}
          <button
            type="button"
            onClick={() => {
              setIsMaximized((prev) => !prev);
              setTimeout(() => fitToWidth(), 150);
            }}
            className={`p-1.5 rounded transition-all flex items-center space-x-1 ${
              isMaximized
                ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-xs'
                : 'hover:bg-slate-200 text-slate-700'
            }`}
            title={isMaximized ? 'Exit Fullscreen (Esc)' : 'Expand Document to Fullscreen'}
          >
            {isMaximized ? (
              <>
                <Minimize2 className="w-3.5 h-3.5" />
                <span className="text-[11px] font-semibold">Exit Fullscreen</span>
              </>
            ) : (
              <>
                <Maximize2 className="w-3.5 h-3.5" />
                <span className="text-[11px] font-semibold">Expand</span>
              </>
            )}
          </button>
        </div>
      </div>
    </>
  );

  // Document Content View
  const renderDocumentContent = () => (
    <div
      ref={scrollContainerRef}
      className="flex-1 overflow-x-auto overflow-y-auto p-4 flex justify-center bg-slate-200/70"
    >
      {/* VIEW 1: Authentic Uploaded Word Document rendered directly via docx-preview */}
      {viewMode === 'docx' && (
        <div className="w-full flex flex-col items-center relative">
          {/* Document Wrapper with CSS zoom for laser-sharp text rendering without raster blur */}
          <div
            style={{
              zoom: `${zoomLevel}%`,
            }}
            className="docx-viewer-inner max-w-full flex flex-col items-center antialiased"
          >
            {/* docx-preview root container */}
            <div
              ref={docxContainerRef}
              className="docx-viewer"
              style={{
                fontFamily: 'Calibri, Arial, sans-serif',
                WebkitFontSmoothing: 'antialiased',
                MozOsxFontSmoothing: 'grayscale',
                textRendering: 'optimizeLegibility',
              }}
            />
          </div>
        </div>
      )}

      {/* VIEW 2: Dynamic Execution Matrix Grid */}
      {viewMode === 'matrix' && (
        <div
          style={{ zoom: `${zoomLevel}%` }}
          className="bg-white shadow-xl border border-slate-300 p-6 max-w-5xl w-full text-slate-800 rounded-sm font-sans min-h-[900px] my-2"
        >
          <div className="border-b border-slate-300 pb-3 mb-4">
            <h1 className="text-base font-bold text-slate-900">{session.title}</h1>
            <div className="flex items-center space-x-4 text-xs text-slate-600 mt-1">
              <span><b>Doc No:</b> {session.document_no}</span>
              <span><b>Version:</b> {session.version}</span>
              <span><b>Effective:</b> {session.effective_date}</span>
            </div>
          </div>

          <div className="border border-slate-300 rounded-sm overflow-hidden">
            <table className="w-full border-collapse text-left text-[11px]">
              <thead>
                <tr className="bg-[#102542] text-white font-semibold divide-x divide-slate-600 border-b border-slate-400">
                  <th className="py-2 px-2.5 w-16 text-center">Step #</th>
                  <th className="py-2 px-2.5 w-32">Scenario</th>
                  <th className="py-2 px-2.5 w-44">Procedure</th>
                  <th className="py-2 px-2.5 w-40">Expected Result</th>
                  <th className="py-2 px-2.5 w-24 text-center">Pass / Fail</th>
                  <th className="py-2 px-2.5 w-36 text-center">Initials / Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-300">
                {session.steps.map((step) => {
                  const isSelected = step.step_id === selectedStepId;
                  return (
                    <tr
                      key={step.step_id}
                      onClick={() => onSelectStep(step.step_id)}
                      className={`divide-x divide-slate-300 cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-blue-50/80 ring-2 ring-[#1d63dc] relative z-10 font-medium'
                          : 'hover:bg-slate-50'
                      }`}
                    >
                      <td className="py-2 px-2 text-center align-top font-bold text-slate-800">
                        {step.step_id}
                      </td>
                      <td className="py-2 px-2.5 align-top font-medium text-slate-900">
                        {step.scenario}
                      </td>
                      <td className="py-2 px-2.5 align-top text-slate-700">
                        {step.procedure}
                      </td>
                      <td className="py-2 px-2.5 align-top text-slate-700">
                        {step.expected_result}
                      </td>
                      <td className="py-2 px-2 text-center align-top">
                        {step.status === 'PASS' && (
                          <div style={{ fontWeight: 700, color: '#0f172a', fontSize: '11px', fontFamily: 'Calibri, Arial, sans-serif' }}>
                            Pass
                          </div>
                        )}
                        {step.status === 'FAIL' && (
                          <div style={{ fontWeight: 700, color: '#0f172a', fontSize: '11px', fontFamily: 'Calibri, Arial, sans-serif' }}>
                            Fail
                          </div>
                        )}
                        {step.status === 'BLOCKED' && (
                          <div style={{ fontWeight: 700, color: '#0f172a', fontSize: '11px', fontFamily: 'Calibri, Arial, sans-serif' }}>
                            Blocked
                          </div>
                        )}
                        {step.status === 'EXECUTING' && (
                          <div style={{ fontWeight: 600, color: '#0f172a', fontSize: '10px', fontStyle: 'italic', fontFamily: 'Calibri, Arial, sans-serif' }}>
                            Running...
                          </div>
                        )}
                        {step.status === 'QUEUED' && (
                          <span className="text-slate-400 text-xs">-</span>
                        )}
                      </td>
                      <td className="py-2 px-2 text-center align-top font-bold text-[11px] text-slate-800">
                        {step.status !== 'QUEUED' ? (
                          <span>
                            {step.initials_date || 'S.B. / 15-Oct-2026'}
                          </span>
                        ) : (
                          <span className="text-slate-400 text-xs font-normal">-</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );

  // Lightbox Modal for Full-Resolution Evidence Inspection with Interactive Zoom
  const renderLightbox = () => {
    if (!lightboxState) return null;
    return (
      <ScreenshotLightboxModal
        data={lightboxState}
        onClose={() => setLightboxState(null)}
      />
    );
  };

  // FULLSCREEN / MAXIMIZED VIEW MODAL
  if (isMaximized) {
    return (
      <div className="fixed inset-0 z-50 bg-slate-900/90 flex flex-col p-4 animate-in fade-in select-none">
        <div className="bg-white rounded-xl shadow-2xl border border-slate-300 flex-1 flex flex-col overflow-hidden">
          {renderHeaderAndToolbar()}
          {renderDocumentContent()}
        </div>
        {renderLightbox()}
      </div>
    );
  }

  // STANDARD SPLIT-PANE VIEW (Column 3)
  return (
    <section className="flex-1 flex flex-col bg-slate-200/50 h-[calc(100vh-3.5rem)] overflow-hidden select-none">
      {renderHeaderAndToolbar()}
      {renderDocumentContent()}
      {renderLightbox()}
    </section>
  );
};
