import { ExecutionSummaryModal, SummaryReportData } from './components/ExecutionSummaryModal';
import { ProtocolAuthoringModal } from './components/ProtocolAuthoringModal';
import React, { useState, useRef, useEffect } from 'react';
import { ProtocolSession, ProtocolStep, SimulationMode, TraceStage } from './types';
import { TopHeaderBar } from './components/TopHeaderBar';
import { MiddleSequencePane } from './components/MiddleSequencePane';
import { RightDocInspector } from './components/RightDocInspector';
import { LiveBrowserModal } from './components/LiveBrowserModal';
import { ArtifactModal } from './components/ArtifactModal';
import { ScreenshotLightboxModal, LightboxData } from './components/ScreenshotLightboxModal';
import { TargetSetupBar, ProductItem } from './components/TargetSetupBar';

export const App: React.FC = () => {
  // Protocol State: Strictly null on initial load (Zero hardcoded preloads)
  const [session, setSession] = useState<ProtocolSession | null>(null);
  const [rawDocxBuffer, setRawDocxBuffer] = useState<ArrayBuffer | null>(null);
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [isAuthoring, setIsAuthoring] = useState<boolean>(false);
  const [authoringStage, setAuthoringStage] = useState<number>(0);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [simMode, setSimMode] = useState<SimulationMode>('PASS');
  const [visibleBrowser, setVisibleBrowser] = useState<boolean>(false);

  // Lightbox Modal State
  const [lightboxData, setLightboxData] = useState<LightboxData | null>(null);

  const handleOpenLightbox = (step: ProtocolStep, type: 'form' | 'modal' | 'combined' = 'form', overrideUrl?: string) => {
    setLightboxData({
      step,
      activeType: type,
      overrideUrl,
    });
  };

  // Target Environment & Credentials States
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>('onepv');
  const [targetUrl, setTargetUrl] = useState<string>('https://mpv-two.vercel.app');

  // Fetch available products and synchronize initial target URL
  useEffect(() => {
    fetch('/api/products')
      .then((res) => res.json())
      .then((data) => {
        if (data && data.products) {
          setProducts(data.products);
          const current = data.products.find((p: ProductItem) => p.product_id === selectedProduct);
          if (current && current.base_url) {
            setTargetUrl(current.base_url);
          }
        }
      })
      .catch(() => {});
  }, []);

  // Credential Gate States
  const [username, setUsername] = useState<string>('sirihari.banda');
  const [password, setPassword] = useState<string>('Clinevo@2026');
  const [enterprise, setEnterprise] = useState<string>('Clinevo');
  const [requiresApproval, setRequiresApproval] = useState<boolean>(false);
  const [waitingForApproval, setWaitingForApproval] = useState<boolean>(false);

  // Live Viewport Stream States
  const [isLiveBrowserOpen, setIsLiveBrowserOpen] = useState<boolean>(false);
  const [frameData, setFrameData] = useState<string | null>(null);
  const [currentUrl, setCurrentUrl] = useState<string>('https://mpv-two.vercel.app/login');
  const [currentAction, setCurrentAction] = useState<string>('Ready for serial automated qualification');
  const [isWsConnected, setIsWsConnected] = useState<boolean>(false);

  // Artifact Modal
    // Executive Summary & AI RCA State
  const [summaryData, setSummaryData] = useState<SummaryReportData | null>(null);
  const [isSummaryOpen, setIsSummaryOpen] = useState<boolean>(false);

  // OQ / PQ Authoring Modal State
  const [isAuthoringModalOpen, setIsAuthoringModalOpen] = useState<boolean>(false);

  const [selectedStage, setSelectedStage] = useState<TraceStage | null>(null);

  // GxP Human Review Safety Gate
  const [humanReviewAlert, setHumanReviewAlert] = useState<{
    stepId: string;
    flagType: string;
    reason: string;
  } | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

  // Manual Protocol Upload Handler (processes the user's uploaded Word file dynamically)
  const handleUploadFile = async (file: File, productId: string = selectedProduct) => {
    setIsAuthoring(true);
    setAuthoringStage(1); // Stage 1: Extraction running
    setSession(null);
    setSelectedStepId(null);

    try {
      // 1. Read binary ArrayBuffer for direct client-side docx-preview rendering
      const buffer = await file.arrayBuffer();
      setRawDocxBuffer(buffer);

      // 2. Upload file to backend for dynamic extraction and Groq Qwen planner
      const formData = new FormData();
      formData.append('file', file);
      formData.append('product_id', productId);

      // Stage 2 indicator: Groq planning
      const timer = setTimeout(() => {
        setAuthoringStage(2);
      }, 400);

      const res = await fetch('/api/upload-protocol', {
        method: 'POST',
        body: formData,
      });

      clearTimeout(timer);

      if (!res.ok) {
        throw new Error(`Upload failed with status ${res.status}`);
      }

      const data: ProtocolSession = await res.json();

      // Step-by-step visual authoring animation so user sees queuing & progression
      setAuthoringStage(2); // Groq Planning
      await sleep(600);
      setAuthoringStage(3); // Coverage Gate 1
      await sleep(350);
      setAuthoringStage(4); // Playwright Generator
      await sleep(350);
      setAuthoringStage(5); // Coverage Gate 2
      await sleep(350);
      setAuthoringStage(6); // Git Baseline
      await sleep(250);

      setSession(data);
      // Automatically select first step so document immediately shows Step 1
      setSelectedStepId(data.steps && data.steps.length > 0 ? data.steps[0].step_id : null);
    } catch (err) {
      console.error('Failed to upload and parse protocol:', err);
    } finally {
      setIsAuthoring(false);
      setAuthoringStage(7);
    }
  };

  // Sample Protocol Selection (Dropdown option)
  const handleLoadSample = async (filename: string, productId: string = selectedProduct) => {
    setIsAuthoring(true);
    setAuthoringStage(1);
    setSession(null);
    setSelectedStepId(null);

    try {
      const formData = new FormData();
      formData.append('filename', filename);
      formData.append('product_id', productId);

      const timer = setTimeout(() => {
        setAuthoringStage(2);
      }, 400);

      const res = await fetch('/api/load-sample-protocol', {
        method: 'POST',
        body: formData,
      });

      clearTimeout(timer);

      if (!res.ok) {
        throw new Error(`Failed to load sample with status ${res.status}`);
      }

      const data: ProtocolSession = await res.json();

      // Fetch the binary .docx file from backend for docx-preview
      const rawRes = await fetch(`/api/raw-protocol/${data.session_id}`);
      if (rawRes.ok) {
        const buf = await rawRes.arrayBuffer();
        setRawDocxBuffer(buf);
      }

      // Step-by-step visual animation
      setAuthoringStage(2);
      await sleep(500);
      setAuthoringStage(3);
      await sleep(300);
      setAuthoringStage(4);
      await sleep(300);
      setAuthoringStage(5);
      await sleep(300);
      setAuthoringStage(6);
      await sleep(200);

      setSession(data);
      setSelectedStepId(data.steps && data.steps.length > 0 ? data.steps[0].step_id : null);
    } catch (err) {
      console.error('Failed to load sample protocol:', err);
    } finally {
      setIsAuthoring(false);
      setAuthoringStage(7);
    }
  };

  // Live WebSocket Connection for Real-time Execution Updates
  const setupWebSocket = (sessionId: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/session/${sessionId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsWsConnected(true);
      console.log('[WS] Connected to live session:', sessionId);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'FRAME') {
          setFrameData(msg.data);
          if (msg.url) setCurrentUrl(msg.url);
          if (msg.action) setCurrentAction(msg.action);
        } else if (msg.type === 'STEP_UPDATE' && msg.step) {
          const updatedStep: ProtocolStep = msg.step;
          setSelectedStepId(updatedStep.step_id);

          setSession((prev) => {
            if (!prev) return prev;
            return {
              ...prev,
              steps: prev.steps.map((s) => (s.step_id === updatedStep.step_id ? updatedStep : s)),
            };
          });
        } else if (msg.type === 'WAITING_FOR_LOGIN_APPROVAL') {
          setWaitingForApproval(true);
        } else if (msg.type === 'HUMAN_REVIEW_REQUIRED') {
          setHumanReviewAlert({
            stepId: msg.step_id || '',
            flagType: msg.flag_type || 'AMBIGUITY',
            reason: msg.reason || 'GxP Ambiguity detected. Human review required before taking any action or evidence.',
          });
                } else if (msg.type === 'EXECUTION_COMPLETE') {
          setIsExecuting(false);
          setWaitingForApproval(false);
          setHumanReviewAlert(null);
          if (msg.session) {
            setSession(msg.session);
          }
          // Fetch and display AI Executive Summary automatically
          const targetSid = (msg.session && msg.session.session_id) || session?.session_id;
          fetch(`/api/session-summary/${targetSid}`)
            .then((r) => r.json())
            .then((data) => {
              setSummaryData(data);
              setIsSummaryOpen(true);
            })
            .catch((e) => console.error('Summary fetch error:', e));
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      setIsWsConnected(false);
    };

    wsRef.current = ws;
  };

  // Execution Trigger
  const handleExecute = () => {
    if (!session) return;
    setIsExecuting(true);
    setWaitingForApproval(false);
    setHumanReviewAlert(null);

    // If no step currently selected, activate the first step so document is displayed
    if (!selectedStepId && session.steps && session.steps.length > 0) {
      setSelectedStepId(session.steps[0].step_id);
    }

    // Setup live WebSocket stream
    setupWebSocket(session.session_id);

    // Trigger execution API with user preferences
    fetch(`/api/execute/${session.session_id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sim_mode: simMode,
        username,
        password,
        enterprise,
        target_url: targetUrl,
        requires_approval: requiresApproval,
        headless: !visibleBrowser, // If visibleBrowser is toggled, launch visible Chromium window!
        max_steps: null,
      }),
    }).catch((err) => {
      console.error('Execution request error:', err);
      setIsExecuting(false);
    });
  };

  const handleApproveLogin = () => {
    if (!session) return;
    fetch(`/api/approve-login/${session.session_id}`, { method: 'POST' })
      .then(() => setWaitingForApproval(false))
      .catch((err) => console.error('Approve login error:', err));
  };

  const handleApproveReview = () => {
    if (!session) return;
    fetch(`/api/approve-review/${session.session_id}`, { method: 'POST' })
      .then(() => setHumanReviewAlert(null))
      .catch((err) => console.error('Approve review error:', err));
  };

  const handleHaltExecution = () => {
    if (!session) return;
    fetch(`/api/halt-execution/${session.session_id}`, { method: 'POST' })
      .then(() => {
        setHumanReviewAlert(null);
        setIsExecuting(false);
      })
      .catch((err) => console.error('Halt execution error:', err));
  };

      const handleArchiveSession = async () => {
    if (!session) return null;
    const res = await fetch(`/api/archive-session/${session.session_id}`, { method: 'POST' });
    const data = await res.json();
    if (summaryData) {
      setSummaryData({ ...summaryData, archive_status: 'ARCHIVED' });
    }
    return data;
  };

  const handleOpenSummary = () => {
    if (!session) return;
    fetch(`/api/session-summary/${session.session_id}`)
      .then((r) => r.json())
      .then((data) => {
        setSummaryData(data);
        setIsSummaryOpen(true);
      })
      .catch((e) => console.error('Summary fetch error:', e));
  };

  const handleDownloadDocx = () => {
    if (!session) return;
    window.location.href = `/api/download-executed-docx/${session.session_id}`;
  };

  const handleDownloadEvidence = () => {
    if (!session) return;
    window.location.href = `/api/download-companion-evidence-docx/${session.session_id}`;
  };

  const shortCode = session?.document_no
    ? session.document_no.split('-').slice(-2).join('-')
    : '';

  return (
    <div className="min-h-screen flex flex-col bg-slate-100 text-slate-800 font-sans select-none overflow-hidden">
      {/* 1. Full-Width Top Header Bar */}
      <TopHeaderBar
        session={session}
        simMode={simMode}
        onSimModeChange={setSimMode}
        visibleBrowser={visibleBrowser}
        onVisibleBrowserChange={setVisibleBrowser}
        onUploadFile={handleUploadFile}
        onLoadSample={handleLoadSample}
        onExecute={handleExecute}
        onOpenLiveBrowser={() => setIsLiveBrowserOpen(true)}
        onDownloadDocx={handleDownloadDocx}
        onDownloadEvidence={handleDownloadEvidence}
        onOpenAuthoringModal={() => setIsAuthoringModalOpen(true)}
        onOpenSummaryModal={handleOpenSummary}
        isExecuting={isExecuting}
        isAuthoring={isAuthoring}
        selectedProduct={selectedProduct}
        onProductChange={setSelectedProduct}
        products={products}
      />

      {/* 2. Target Environment & Credentials Setup Bar (At the beginning) */}
      <TargetSetupBar
        products={products}
        selectedProduct={selectedProduct}
        onProductChange={setSelectedProduct}
        targetUrl={targetUrl}
        onTargetUrlChange={setTargetUrl}
        username={username}
        onUsernameChange={setUsername}
        password={password}
        onPasswordChange={setPassword}
        enterprise={enterprise}
        onEnterpriseChange={setEnterprise}
        simMode={simMode}
        onSimModeChange={setSimMode}
        visibleBrowser={visibleBrowser}
        onVisibleBrowserChange={setVisibleBrowser}
        requiresApproval={requiresApproval}
        onRequiresApprovalChange={setRequiresApproval}
        isExecuting={isExecuting}
        isAuthoring={isAuthoring}
        sessionLoaded={Boolean(session)}
        onExecute={handleExecute}
      />

      {/* Manual Login Approval Gate Banner */}
      {waitingForApproval && (
        <div className="bg-amber-500 text-white px-5 py-2.5 flex items-center justify-between shadow-lg z-40 border-b border-amber-600 animate-in fade-in">
          <div className="flex items-center gap-2.5 text-sm font-semibold">
            <span className="text-lg">⚠️</span>
            <span>Manual Login Approval Gate: Browser is paused on login screen. Review credentials and proceed when ready.</span>
          </div>
          <button
            onClick={handleApproveLogin}
            className="px-4 py-1.5 bg-white text-amber-900 rounded-lg font-bold text-xs shadow hover:bg-amber-50 transition-all cursor-pointer flex items-center gap-1.5"
          >
            <span>Approve &amp; Continue Execution</span>
            <span>→</span>
          </button>
        </div>
      )}

      {/* 2. Main 2-Column Split-Screen Portal Layout */}
      <main className="flex-1 flex overflow-hidden">

        {/* Column 2: Live Test Sequence (Connected Series) */}
        <MiddleSequencePane
          steps={session?.steps || []}
          selectedStepId={selectedStepId}
          onSelectStep={(stepId) => setSelectedStepId(stepId)}
          documentShortCode={shortCode}
          isAuthoring={isAuthoring}
          onExecute={handleExecute}
          isExecuting={isExecuting}
          onOpenLightbox={handleOpenLightbox}
        />

        {/* Column 3: Active Protocol Document Inspector */}
        <RightDocInspector
          session={session}
          rawDocxBuffer={rawDocxBuffer}
          selectedStepId={selectedStepId}
          onSelectStep={(stepId) => setSelectedStepId(stepId)}
          isExecuting={isExecuting}
          onOpenLightbox={handleOpenLightbox}
        />
      </main>

      {/* Live Browser Modal / Drawer */}
      <LiveBrowserModal
        isOpen={isLiveBrowserOpen}
        onClose={() => setIsLiveBrowserOpen(false)}
        frameData={frameData}
        currentUrl={currentUrl}
        currentAction={currentAction}
        isConnected={isWsConnected}
      />

      {/* Artifact Inspector Modal */}
      <ArtifactModal
        stage={selectedStage}
        onClose={() => setSelectedStage(null)}
      />

      {/* GxP Ambiguity & Human Review Safety Gate Modal */}
      {humanReviewAlert && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border-2 border-amber-500 rounded-2xl p-6 max-w-lg w-full shadow-2xl text-white animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center shrink-0">
                <span className="text-amber-400 text-2xl font-bold">⚠️</span>
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    GxP Safety Gate
                  </span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {humanReviewAlert.stepId}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white mt-1">
                  Human Review & Discrepancy Gate
                </h3>
              </div>
            </div>

            <div className="mt-4 p-3.5 bg-slate-950/70 border border-slate-800 rounded-xl">
              <div className="text-xs text-slate-400 font-medium mb-1">Detected Discrepancy / Error:</div>
              <div className="text-sm font-medium text-amber-200">
                {humanReviewAlert.reason}
              </div>
            </div>

            <div className="mt-3 p-3 bg-blue-950/40 border border-blue-900/50 rounded-xl text-xs text-blue-200 leading-relaxed">
              <strong>GxP Mandate:</strong> Playwright automation is safely <strong>paused</strong>. The failure is recorded in the validation protocol audit log. You can halt the execution now, or acknowledge this discrepancy to dismiss blocking UI alerts and automatically continue executing subsequent steps.
            </div>

            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={handleHaltExecution}
                className="px-4 py-2 rounded-lg text-sm font-semibold bg-red-950/60 hover:bg-red-900 text-red-200 border border-red-800/80 transition-all cursor-pointer"
              >
                Halt Execution
              </button>
              <button
                type="button"
                onClick={handleApproveReview}
                className="px-5 py-2 rounded-lg text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30 transition-all cursor-pointer flex items-center gap-1.5"
              >
                <span>Acknowledge Discrepancy &amp; Continue</span>
                <span>→</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Global Interactive Zoomable Screenshot Lightbox Modal */}
      <ScreenshotLightboxModal
        data={lightboxData}
        onClose={() => setLightboxData(null)}
      />

      {/* AI-Assisted OQ/PQ Protocol Authoring Modal */}
      <ProtocolAuthoringModal
        isOpen={isAuthoringModalOpen}
        onClose={() => setIsAuthoringModalOpen(false)}
        onLoadGeneratedProtocol={(filename) => handleLoadSample(filename)}
      />

      {/* AI Executive Summary & Root-Cause Analysis Modal */}
      <ExecutionSummaryModal
        isOpen={isSummaryOpen}
        onClose={() => setIsSummaryOpen(false)}
        summary={summaryData}
        onDownloadDocx={handleDownloadDocx}
        onDownloadEvidence={handleDownloadEvidence}
        onArchive={handleArchiveSession}
      />
    </div>
  );
};

export default App;
