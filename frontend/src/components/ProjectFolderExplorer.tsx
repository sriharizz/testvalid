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
  const productName = currentProdObj?.name || (selectedProduct === 'signal' ? 'Clinevo Signal' : selectedProduct === 'custom' ? 'Custom Target' : 'Clinevo OnePV');

  return (
    <aside className={`flex flex-col bg-white text-slate-700 border-r border-slate-200 select-none shadow-xs ${isSidebar ? 'w-72 xl:w-80 h-[calc(100vh-3.5rem)] shrink-0' : 'flex-1 p-6'}`}>
      
      {/* Hidden File Picker */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInput}
        accept=".docx"
        className="hidden"
      />

      {/* 1. Clean Product Title & Actions */}
      <div className="p-3 border-b border-slate-200 bg-slate-50/70">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-5 h-5 rounded bg-blue-50 border border-blue-200 flex items-center justify-center shrink-0">
              <Layers className="w-3 h-3 text-blue-600" />
            </div>
            <span className="text-xs font-bold text-slate-900 truncate tracking-tight">
              {productName}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 font-medium">Protocols</span>
        </div>

        {/* Clean Compact Action Buttons */}
        <div className="grid grid-cols-2 gap-1.5 mb-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="px-2 py-1.5 bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 text-slate-700 hover:text-slate-900 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-2xs"
            title="Upload any validation protocol (.docx) to test"
          >
            <Plus className="w-3 h-3 text-blue-600" />
            <span>Upload (.docx)</span>
          </button>

          <button
            type="button"
            onClick={onOpenAuthoringModal}
            className="px-2 py-1.5 bg-indigo-50/80 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 hover:text-indigo-900 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-2xs"
            title="Author OQ or PQ protocol using AI"
          >
            <Sparkles className="w-3 h-3 text-amber-500" />
            <span>Author AI</span>
          </button>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-3 h-3 text-slate-400 absolute left-2.5 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter protocols..."
            className="w-full bg-white border border-slate-200 text-slate-800 text-[11px] rounded-lg pl-7 pr-2 py-1.5 placeholder-slate-400 focus:outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors shadow-2xs"
          />
        </div>
      </div>

      {/* 2. Indented Tree View for Product Folders */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-2 bg-white">
        {folders.map((folder) => {
          const isExpanded = expandedFolderIds[folder.id] ?? true;
          const isOQ = folder.type === 'OQ';
          const isPQ = folder.type === 'PQ';

          // Filter protocols by search query AND deduplicate by document_no
          const seenDocs = new Set<string>();
          const protocols = folder.protocols
            .filter((p) => {
              if (!searchQuery) return true;
              return (
                p.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (p.document_no && p.document_no.toLowerCase().includes(searchQuery.toLowerCase()))
              );
            })
            .filter((p) => {
              const key = p.document_no || p.filename;
              if (seenDocs.has(key)) return false;
              seenDocs.add(key);
              return true;
            });

          return (
            <div key={folder.id} className="space-y-0.5">
              {/* Folder Row */}
              <button
                type="button"
                onClick={() => toggleFolder(folder.id)}
                className="w-full px-2 py-1.5 rounded-lg flex items-center justify-between text-left hover:bg-slate-50 text-slate-700 transition-colors cursor-pointer group"
              >
                <div className="flex items-center space-x-1.5 min-w-0">
                  {isExpanded ? (
                    <ChevronDown className="w-3 h-3 text-slate-400 shrink-0" />
                  ) : (
                    <ChevronRight className="w-3 h-3 text-slate-400 shrink-0" />
                  )}
                  {isExpanded ? (
                    <FolderOpen className={`w-3.5 h-3.5 shrink-0 ${isOQ ? 'text-amber-500' : isPQ ? 'text-blue-600' : 'text-slate-400'}`} />
                  ) : (
                    <Folder className={`w-3.5 h-3.5 shrink-0 ${isOQ ? 'text-amber-500' : isPQ ? 'text-blue-600' : 'text-slate-400'}`} />
                  )}
                  <span className="font-bold text-[11px] text-slate-800 truncate">
                    {folder.name}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 font-semibold bg-slate-100 px-1.5 py-0.5 rounded-full">
                  {protocols.length}
                </span>
              </button>

              {/* Protocols List in Folder */}
              {isExpanded && (
                <div className="pl-3 pr-1 space-y-1">
                  {protocols.length === 0 ? (
                    <div className="py-1.5 px-3 text-[10px] text-slate-400 italic">
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
                          className={`px-2.5 py-1.5 rounded-lg transition-all cursor-pointer flex items-center justify-between group ${
                            isActive
                              ? 'bg-blue-50/90 border border-blue-200 border-l-4 border-l-blue-600 text-blue-900 shadow-2xs font-semibold'
                              : 'hover:bg-slate-50 text-slate-600 border border-transparent hover:border-slate-200'
                          }`}
                          title={proto.filename}
                        >
                          <div className="flex items-center space-x-2 min-w-0 flex-1">
                            <FileText className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-600'}`} />
                            <div className="min-w-0 flex-1">
                              <span className={`text-[11px] block truncate leading-tight ${isActive ? 'text-blue-950 font-bold' : 'text-slate-800 font-medium group-hover:text-slate-900'}`}>
                                {proto.document_no || proto.filename}
                              </span>
                              <span className="text-[10px] text-slate-400 group-hover:text-slate-500 block truncate leading-tight mt-0.5">
                                {proto.size_kb} KB • {proto.step_count || 12} steps
                              </span>
                            </div>
                          </div>

                          {isActive && (
                            <span className="shrink-0 flex items-center gap-1 text-[9px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
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
      <div className="p-2.5 border-t border-slate-200 bg-slate-50/80 flex items-center justify-between text-xs">
        <div className="min-w-0 space-y-0.5">
          <div className="flex items-center gap-1.5 font-semibold text-slate-800 text-[11px]">
            <User className="w-3 h-3 text-blue-600 shrink-0" />
            <span className="truncate">{username}</span>
          </div>
          <div className="flex items-center gap-1 text-[10px] text-blue-600 font-mono truncate" title={targetUrl}>
            <Link2 className="w-2.5 h-2.5 shrink-0" />
            <span className="truncate">{targetUrl?.replace(/^https?:\/\//, '') || 'mpv-two.vercel.app'}</span>
          </div>
        </div>

        {onLogout && (
          <button
            type="button"
            onClick={onLogout}
            className="p-1.5 rounded-lg bg-white hover:bg-slate-100 border border-slate-200 text-slate-500 hover:text-slate-800 transition-colors cursor-pointer shadow-2xs"
            title="Log Out &amp; Switch Target Environment"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

    </aside>
  );
};
