import React, { useState, useEffect, useRef } from 'react';
import {
  Folder,
  FolderOpen,
  FileText,
  Upload,
  Sparkles,
  ChevronRight,
  ChevronDown,
  CheckCircle2,
  Clock,
  Play,
  Layers,
  Search,
  Filter,
  ShieldCheck,
  User,
  LogOut,
  Globe,
  Link2
} from 'lucide-react';
import { ProtocolSession } from '../types';

export interface ProtocolFileItem {
  filename: string;
  size_kb: number;
  protocol_type?: 'OQ' | 'PQ' | 'OPS';
  document_no?: string;
  updated_at?: string;
  step_count?: number;
}

export interface ProjectFolder {
  id: string;
  name: string;
  description: string;
  type: 'OQ' | 'PQ' | 'OPS';
  protocols: ProtocolFileItem[];
}

interface ProjectFolderExplorerProps {
  selectedProduct: string;
  onProductChange?: (productId: string) => void;
  products?: { product_id: string; name: string }[];
  targetUrl?: string;
  username?: string;
  currentSession: ProtocolSession | null;
  onSelectProtocol: (filename: string) => void;
  onUploadFile: (file: File) => void;
  onOpenAuthoringModal: () => void;
  onProceedToWorkspace?: () => void;
  onLogout?: () => void;
  isSidebar?: boolean;
}

export const ProjectFolderExplorer: React.FC<ProjectFolderExplorerProps> = ({
  selectedProduct,
  onProductChange,
  products = [],
  targetUrl,
  username = 'sirihari.banda',
  currentSession,
  onSelectProtocol,
  onUploadFile,
  onOpenAuthoringModal,
  onProceedToWorkspace,
  onLogout,
  isSidebar = true,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [folders, setFolders] = useState<ProjectFolder[]>([]);
  const [expandedFolderIds, setExpandedFolderIds] = useState<Record<string, boolean>>({});
  const [searchQuery, setSearchQuery] = useState<string>('');

  const fetchFolders = () => {
    fetch(`/api/project-folders?product_id=${encodeURIComponent(selectedProduct)}`)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.folders) {
          setFolders(data.folders);
          // Auto-expand all folders for this product
          const exp: Record<string, boolean> = {};
          data.folders.forEach((f: ProjectFolder) => {
            exp[f.id] = true;
          });
          setExpandedFolderIds(exp);
        }
      })
      .catch((err) => console.error('Failed to fetch project folders:', err));
  };

  useEffect(() => {
    fetchFolders();
  }, [selectedProduct]);

  const toggleFolder = (folderId: string) => {
    setExpandedFolderIds((prev) => ({
      ...prev,
      [folderId]: !prev[folderId],
    }));
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUploadFile(e.target.files[0]);
    }
  };

  const currentProdObj = products.find((p) => p.product_id === selectedProduct);
  const productName = currentProdObj?.name || (selectedProduct === 'signal' ? 'Clinevo Signal' : selectedProduct === '1pv' ? '1PV Enterprise Core' : 'Clinevo OnePV');

  return (
    <aside className={`flex flex-col bg-[#0b1424] text-slate-200 border-r border-slate-800 select-none ${isSidebar ? 'w-72 xl:w-80 h-[calc(100vh-3.5rem)] shrink-0' : 'flex-1 p-6'}`}>
      
      {/* Hidden File Picker */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInput}
        accept=".docx"
        className="hidden"
      />

      {/* 1. Sidebar Header: Product Identity & Hierarchy */}
      <div className="p-3.5 border-b border-slate-800/90 bg-slate-900/60">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-6 h-6 rounded-lg bg-blue-600/30 border border-blue-500/40 flex items-center justify-center shrink-0">
              <Layers className="w-3.5 h-3.5 text-blue-400" />
            </div>
            <span className="text-xs font-bold text-white truncate tracking-tight">
              {productName}
            </span>
          </div>
          <span className="text-[10px] font-semibold text-slate-400 bg-slate-800 border border-slate-700 px-1.5 py-0.5 rounded">
            Folders
          </span>
        </div>

        {/* Search Filter */}
        <div className="relative mt-2">
          <Search className="w-3 h-3 text-slate-400 absolute left-2.5 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search protocols &amp; test cases..."
            className="w-full bg-slate-950/80 border border-slate-700/80 text-white text-[11px] rounded-lg pl-7 pr-2.5 py-1.5 placeholder-slate-500 focus:outline-hidden focus:border-blue-500"
          />
        </div>

        {/* Quick Folder Actions */}
        <div className="grid grid-cols-2 gap-1.5 mt-2.5">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="px-2 py-1.5 bg-[#1d63dc] hover:bg-blue-600 text-white rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1.5 shadow-xs transition-colors cursor-pointer"
            title="Upload an executed or blank .docx protocol into this product folder"
          >
            <Upload className="w-3 h-3" />
            <span>Upload (.docx)</span>
          </button>

          <button
            type="button"
            onClick={onOpenAuthoringModal}
            className="px-2 py-1.5 bg-indigo-600/90 hover:bg-indigo-500 text-white rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1.5 shadow-xs transition-colors border border-indigo-400/30 cursor-pointer"
            title="Author OQ or PQ protocols using AI"
          >
            <Sparkles className="w-3 h-3 text-amber-300" />
            <span>Author AI</span>
          </button>
        </div>
      </div>

      {/* 2. Folder Tree for Selected Product */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {folders.map((folder) => {
          const isExpanded = expandedFolderIds[folder.id] ?? true;
          const isOQ = folder.type === 'OQ';
          const isPQ = folder.type === 'PQ';

          // Filter protocols by search query
          const protocols = folder.protocols.filter((p) => {
            if (!searchQuery) return true;
            return p.filename.toLowerCase().includes(searchQuery.toLowerCase());
          });

          return (
            <div key={folder.id} className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
              {/* Folder Item Header */}
              <button
                type="button"
                onClick={() => toggleFolder(folder.id)}
                className="w-full px-2.5 py-2 flex items-center justify-between text-left hover:bg-slate-800/60 transition-colors"
              >
                <div className="flex items-center space-x-2 min-w-0">
                  {isExpanded ? (
                    <FolderOpen className={`w-3.5 h-3.5 shrink-0 ${isOQ ? 'text-amber-400' : isPQ ? 'text-cyan-400' : 'text-blue-400'}`} />
                  ) : (
                    <Folder className={`w-3.5 h-3.5 shrink-0 ${isOQ ? 'text-amber-400' : isPQ ? 'text-cyan-400' : 'text-blue-400'}`} />
                  )}
                  <span className="font-bold text-[11px] text-slate-200 truncate">
                    {folder.name}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <span className="text-[10px] text-slate-500 font-mono">({protocols.length})</span>
                  {isExpanded ? <ChevronDown className="w-3 h-3 text-slate-400" /> : <ChevronRight className="w-3 h-3 text-slate-400" />}
                </div>
              </button>

              {/* Protocols in Folder */}
              {isExpanded && (
                <div className="p-1 space-y-1 border-t border-slate-800/60 bg-slate-950/30">
                  {protocols.length === 0 ? (
                    <div className="py-2 px-2 text-center text-[10px] text-slate-500">
                      No protocols match search.
                    </div>
                  ) : (
                    protocols.map((proto) => {
                      const isActive = currentSession && (
                        currentSession.filename === proto.filename ||
                        (currentSession.document_no && proto.filename.includes(currentSession.document_no))
                      );

                      return (
                        <div
                          key={proto.filename}
                          onClick={() => {
                            onSelectProtocol(proto.filename);
                            if (onProceedToWorkspace) onProceedToWorkspace();
                          }}
                          className={`p-2 rounded-lg border transition-all cursor-pointer flex flex-col justify-between ${
                            isActive
                              ? 'bg-blue-600/20 border-blue-500 text-white shadow-xs'
                              : 'bg-slate-900/60 border-slate-800 hover:bg-slate-800 hover:border-slate-700 text-slate-300'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-1">
                            <div className="flex items-start gap-1.5 min-w-0">
                              <FileText className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                              <div className="min-w-0">
                                <span className="font-semibold text-[11px] block truncate leading-tight text-slate-200" title={proto.filename}>
                                  {proto.filename}
                                </span>
                                <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-0.5">
                                  <span>{proto.size_kb} KB</span>
                                  {proto.step_count && <span>• {proto.step_count} steps</span>}
                                </div>
                              </div>
                            </div>
                            {isActive ? (
                              <span className="shrink-0 px-1 py-0.2 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 rounded text-[9px] font-bold">
                                Active
                              </span>
                            ) : (
                              <Play className="w-3 h-3 text-slate-500 opacity-0 group-hover:opacity-100" />
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 3. Footer: User Identity & Target Link Pill */}
      <div className="p-3 border-t border-slate-800/90 bg-slate-900/80 flex items-center justify-between text-xs">
        <div className="min-w-0 space-y-0.5">
          <div className="flex items-center gap-1.5 font-bold text-white text-[11px]">
            <User className="w-3 h-3 text-blue-400" />
            <span className="truncate">{username}</span>
          </div>
          <div className="flex items-center gap-1 text-[10px] text-slate-400 font-mono truncate" title={targetUrl}>
            <Link2 className="w-2.5 h-2.5 text-emerald-400 shrink-0" />
            <span className="text-emerald-400 truncate">{targetUrl || 'mpv-two.vercel.app'}</span>
          </div>
        </div>

        {onLogout && (
          <button
            type="button"
            onClick={onLogout}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
            title="Log Out / Reconfigure Target Environment"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

    </aside>
  );
};
