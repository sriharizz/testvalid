import React, { useState, useEffect, useRef } from 'react';
import {
  Folder,
  FolderOpen,
  FileText,
  Upload,
  Sparkles,
  ChevronRight,
  ChevronDown,
  Layers,
  Search,
  User,
  LogOut,
  Link2,
  CheckCircle2,
  Plus
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
  refreshTrigger?: number;
}

export const ProjectFolderExplorer: React.FC<ProjectFolderExplorerProps> = ({
  selectedProduct,
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
  refreshTrigger = 0,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [folders, setFolders] = useState<ProjectFolder[]>([]);
  const [expandedFolderIds, setExpandedFolderIds] = useState<Record<string, boolean>>({
    oq: true,
    pq: true,
    ops: false,
  });
  const [searchQuery, setSearchQuery] = useState<string>('');

  const fetchFolders = () => {
    fetch(`/api/project-folders?product_id=${encodeURIComponent(selectedProduct)}`)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.folders) {
          setFolders(data.folders);
          // Auto-expand non-empty folders
          const exp: Record<string, boolean> = {};
          data.folders.forEach((f: ProjectFolder) => {
            exp[f.id] = (f.protocols && f.protocols.length > 0) || f.type === 'OQ' || f.type === 'PQ';
          });
          setExpandedFolderIds(exp);
        }
      })
      .catch((err) => console.error('Failed to fetch project folders:', err));
  };

  useEffect(() => {
    fetchFolders();
  }, [selectedProduct, refreshTrigger]);

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
  const productName = currentProdObj?.name || (selectedProduct === 'signal' ? 'Clinevo Signal' : selectedProduct === '1pv' ? '1PV Core' : 'Clinevo OnePV');

  return (
    <aside className={`flex flex-col bg-[#0b1322] text-slate-300 border-r border-slate-800 select-none ${isSidebar ? 'w-72 xl:w-80 h-[calc(100vh-3.5rem)] shrink-0' : 'flex-1 p-6'}`}>
      
      {/* Hidden File Picker */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInput}
        accept=".docx"
        className="hidden"
      />

      {/* 1. Clean Product Title & Actions */}
      <div className="p-3 border-b border-slate-800/90 bg-slate-900/50">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-5 h-5 rounded bg-blue-500/20 border border-blue-500/40 flex items-center justify-center shrink-0">
              <Layers className="w-3 h-3 text-cyan-400" />
            </div>
            <span className="text-xs font-bold text-white truncate tracking-tight">
              {productName}
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono">Protocols</span>
        </div>

        {/* Clean Compact Action Buttons */}
        <div className="grid grid-cols-2 gap-1.5 mb-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="px-2 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-slate-600 text-slate-200 hover:text-white rounded-md text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-xs"
            title="Upload any validation protocol (.docx) to test"
          >
            <Plus className="w-3 h-3 text-cyan-400" />
            <span>Upload (.docx)</span>
          </button>

          <button
            type="button"
            onClick={onOpenAuthoringModal}
            className="px-2 py-1 bg-indigo-950/70 hover:bg-indigo-900 border border-indigo-700/60 text-indigo-200 hover:text-white rounded-md text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-xs"
            title="Author OQ or PQ protocol using AI"
          >
            <Sparkles className="w-3 h-3 text-amber-300" />
            <span>Author AI</span>
          </button>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-3 h-3 text-slate-500 absolute left-2.5 top-2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter protocols..."
            className="w-full bg-slate-950/70 border border-slate-800 text-slate-200 text-[11px] rounded-md pl-7 pr-2 py-1 placeholder-slate-500 focus:outline-hidden focus:border-blue-500 transition-colors"
          />
        </div>
      </div>

      {/* 2. Indented Tree View for Product Folders */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-2">
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
            <div key={folder.id} className="space-y-0.5">
              {/* Folder Row */}
              <button
                type="button"
                onClick={() => toggleFolder(folder.id)}
                className="w-full px-2 py-1 rounded-md flex items-center justify-between text-left hover:bg-slate-800/50 text-slate-300 transition-colors cursor-pointer group"
              >
                <div className="flex items-center space-x-1.5 min-w-0">
                  {isExpanded ? (
                    <ChevronDown className="w-3 h-3 text-slate-400 shrink-0" />
                  ) : (
                    <ChevronRight className="w-3 h-3 text-slate-400 shrink-0" />
                  )}
                  {isExpanded ? (
                    <FolderOpen className={`w-3.5 h-3.5 shrink-0 ${isOQ ? 'text-amber-400' : isPQ ? 'text-cyan-400' : 'text-slate-400'}`} />
                  ) : (
                    <Folder className={`w-3.5 h-3.5 shrink-0 ${isOQ ? 'text-amber-400' : isPQ ? 'text-cyan-400' : 'text-slate-400'}`} />
                  )}
                  <span className="font-semibold text-[11px] text-slate-200 truncate">
                    {folder.name}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 font-mono">
                  {protocols.length}
                </span>
              </button>

              {/* Protocols List in Folder */}
              {isExpanded && (
                <div className="pl-4 pr-1 space-y-0.5">
                  {protocols.length === 0 ? (
                    <div className="py-1 px-3 text-[10px] text-slate-500 italic">
                      Empty folder
                    </div>
                  ) : (
                    protocols.map((proto) => {
                      // STRICT EQUALITY: Only mark active if exact filename matches current session
                      const isActive = Boolean(currentSession && currentSession.filename === proto.filename);

                      return (
                        <div
                          key={proto.filename}
                          onClick={() => {
                            onSelectProtocol(proto.filename);
                            if (onProceedToWorkspace) onProceedToWorkspace();
                          }}
                          className={`px-2.5 py-1.5 rounded-md transition-all cursor-pointer flex items-center justify-between group ${
                            isActive
                              ? 'bg-blue-600/25 border-l-2 border-cyan-400 text-white shadow-2xs'
                              : 'hover:bg-slate-800/60 text-slate-300 border-l-2 border-transparent'
                          }`}
                          title={proto.filename}
                        >
                          <div className="flex items-center space-x-2 min-w-0 flex-1">
                            <FileText className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-cyan-300' : 'text-slate-500 group-hover:text-slate-300'}`} />
                            <div className="min-w-0 flex-1">
                              <span className={`text-[11px] block truncate leading-tight font-medium ${isActive ? 'text-white' : 'text-slate-300 group-hover:text-white'}`}>
                                {proto.document_no || proto.filename}
                              </span>
                              <span className="text-[10px] text-slate-500 block truncate leading-tight mt-0.5">
                                {proto.size_kb} KB • {proto.step_count || 12} steps
                              </span>
                            </div>
                          </div>

                          {isActive && (
                            <span className="shrink-0 flex items-center gap-1 text-[9px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/30">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              Active
                            </span>
                          )}
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

      {/* 3. Footer: Active Tester & Target Info */}
      <div className="p-2.5 border-t border-slate-800/90 bg-slate-900/60 flex items-center justify-between text-xs">
        <div className="min-w-0 space-y-0.5">
          <div className="flex items-center gap-1.5 font-semibold text-white text-[11px]">
            <User className="w-3 h-3 text-cyan-400 shrink-0" />
            <span className="truncate">{username}</span>
          </div>
          <div className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono truncate" title={targetUrl}>
            <Link2 className="w-2.5 h-2.5 shrink-0" />
            <span className="truncate">{targetUrl?.replace(/^https?:\/\//, '') || 'mpv-two.vercel.app'}</span>
          </div>
        </div>

        {onLogout && (
          <button
            type="button"
            onClick={onLogout}
            className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors cursor-pointer"
            title="Log Out &amp; Switch Target Environment"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

    </aside>
  );
};
