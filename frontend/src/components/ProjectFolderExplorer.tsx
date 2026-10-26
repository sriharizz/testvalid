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
  Plus,
  Play,
  Layers,
  Search,
  Filter,
  ShieldCheck,
  FileCheck
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
  currentSession: ProtocolSession | null;
  onSelectProtocol: (filename: string) => void;
  onUploadFile: (file: File) => void;
  onOpenAuthoringModal: () => void;
  onProceedToWorkspace: () => void;
  isSidebar?: boolean;
}

export const ProjectFolderExplorer: React.FC<ProjectFolderExplorerProps> = ({
  currentSession,
  onSelectProtocol,
  onUploadFile,
  onOpenAuthoringModal,
  onProceedToWorkspace,
  isSidebar = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [folders, setFolders] = useState<ProjectFolder[]>([]);
  const [expandedFolderIds, setExpandedFolderIds] = useState<Record<string, boolean>>({
    oq_protocols: true,
    pq_protocols: true,
    release_ops: true,
  });
  const [filterType, setFilterType] = useState<'ALL' | 'OQ' | 'PQ' | 'OPS'>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const fetchFolders = () => {
    fetch('/api/project-folders')
      .then((res) => res.json())
      .then((data) => {
        if (data && data.folders) {
          setFolders(data.folders);
        }
      })
      .catch(() => {
        // Fallback default folders if API is loading
        setFolders([
          {
            id: 'oq_protocols',
            name: 'OQ Protocols (Operational Qualification)',
            description: 'FDS-derived operational testing and mandatory field validation',
            type: 'OQ',
            protocols: [
              {
                filename: 'CLIN-EU-VAL-OPV-1-1-OQ-036 - Operational Qualification Protocol.docx',
                size_kb: 39.1,
                protocol_type: 'OQ',
                document_no: 'CLIN-EU-VAL-OPV-1-1-OQ-036',
                step_count: 15,
              },
              {
                filename: 'CLIN-EU-VAL-OPV-1-1-OQ-036 - Manual - Registering Adverse Event Case.docx',
                size_kb: 306.8,
                protocol_type: 'OQ',
                document_no: 'CLIN-EU-VAL-OPV-1-1-OQ-036',
                step_count: 15,
              },
            ],
          },
          {
            id: 'pq_protocols',
            name: 'PQ Protocols (Performance Qualification)',
            description: 'URS-derived end-to-end clinical workflow and triage tests',
            type: 'PQ',
            protocols: [
              {
                filename: 'CLIN-EU-PAT-OPV-1-1-PQ-022 - Performance Qualification Protocol.docx',
                size_kb: 38.7,
                protocol_type: 'PQ',
                document_no: 'CLIN-EU-PAT-OPV-1-1-PQ-022',
                step_count: 12,
              },
              {
                filename: 'CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx',
                size_kb: 284.2,
                protocol_type: 'PQ',
                document_no: 'CLIN-EU-PAT-OPV-1-1-PQ-022',
                step_count: 12,
              },
            ],
          },
        ]);
      });
  };

  useEffect(() => {
    fetchFolders();
  }, []);

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

  const filteredFolders = folders.filter((f) => {
    if (filterType === 'ALL') return true;
    return f.type === filterType;
  });

  return (
    <div className={`flex flex-col ${isSidebar ? 'w-72 xl:w-80 border-r border-slate-700/80 bg-[#0c182a] text-slate-200' : 'flex-1 bg-slate-900 text-slate-100 p-6 overflow-y-auto'}`}>
      
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInput}
        accept=".docx"
        className="hidden"
      />

      {/* Header */}
      <div className={`flex items-center justify-between border-b border-slate-800 ${isSidebar ? 'p-3' : 'pb-4 mb-4'}`}>
        <div>
          <h2 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-blue-400" />
            <span>Project Folders (OQ &amp; PQ)</span>
          </h2>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Maintain validation test cases, protocols &amp; ops
          </p>
        </div>

        {!isSidebar && (
          <button
            type="button"
            onClick={onProceedToWorkspace}
            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl flex items-center gap-1.5 shadow transition-all cursor-pointer"
          >
            <span>Open in Validation Studio</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Toolbar: Upload, Author & Filter */}
      <div className={`${isSidebar ? 'p-3 space-y-2' : 'mb-4 space-y-3'}`}>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex-1 bg-[#1d63dc] hover:bg-blue-600 text-white text-xs font-semibold px-2.5 py-1.5 rounded-lg flex items-center justify-center gap-1.5 shadow transition-all cursor-pointer"
            title="Upload an executed or draft validation protocol (.docx)"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload (.docx)</span>
          </button>

          <button
            type="button"
            onClick={onOpenAuthoringModal}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-2.5 py-1.5 rounded-lg flex items-center justify-center gap-1.5 shadow transition-all cursor-pointer"
            title="Author OQ (from FDS) or PQ (from URS) with Groq AI"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            <span>Author OQ/PQ</span>
          </button>
        </div>

        {/* Search & Filter Pills */}
        <div className="flex items-center gap-1.5 text-[11px]">
          <span className="text-slate-400">Filter:</span>
          {(['ALL', 'OQ', 'PQ', 'OPS'] as const).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => setFilterType(type)}
              className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-all ${
                filterType === type
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Folder Tree List */}
      <div className="flex-1 overflow-y-auto px-3 space-y-3 pb-4">
        {filteredFolders.map((folder) => {
          const isExpanded = expandedFolderIds[folder.id] ?? true;
          const isOQ = folder.type === 'OQ';
          const isPQ = folder.type === 'PQ';

          return (
            <div key={folder.id} className="bg-slate-800/60 border border-slate-700/80 rounded-xl overflow-hidden shadow-xs">
              {/* Folder Header */}
              <button
                type="button"
                onClick={() => toggleFolder(folder.id)}
                className="w-full px-3 py-2.5 flex items-center justify-between text-left hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center space-x-2">
                  {isExpanded ? (
                    <FolderOpen className={`w-4 h-4 ${isOQ ? 'text-amber-400' : isPQ ? 'text-cyan-400' : 'text-indigo-400'}`} />
                  ) : (
                    <Folder className={`w-4 h-4 ${isOQ ? 'text-amber-400' : isPQ ? 'text-cyan-400' : 'text-indigo-400'}`} />
                  )}
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-xs text-white">{folder.name}</span>
                      <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                        isOQ ? 'bg-amber-500/20 text-amber-300' : isPQ ? 'bg-cyan-500/20 text-cyan-300' : 'bg-indigo-500/20 text-indigo-300'
                      }`}>
                        {folder.type}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400 block truncate max-w-[220px]">
                      {folder.protocols.length} protocol(s) • {folder.description}
                    </span>
                  </div>
                </div>
                {isExpanded ? <ChevronDown className="w-3.5 h-3.5 text-slate-400" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-400" />}
              </button>

              {/* Protocols in Folder */}
              {isExpanded && (
                <div className="border-t border-slate-700/60 p-1.5 space-y-1">
                  {folder.protocols.length === 0 ? (
                    <div className="p-2 text-center text-[11px] text-slate-400">
                      No protocols in this folder. Upload or author a new protocol above.
                    </div>
                  ) : (
                    folder.protocols.map((proto) => {
                      const isActive = currentSession && (
                        currentSession.filename === proto.filename ||
                        (currentSession.document_no && proto.filename.includes(currentSession.document_no))
                      );

                      return (
                        <div
                          key={proto.filename}
                          className={`p-2 rounded-lg border transition-all text-xs flex flex-col justify-between ${
                            isActive
                              ? 'bg-blue-600/20 border-blue-500 text-white shadow-xs'
                              : 'bg-slate-900/60 border-slate-700/50 hover:bg-slate-800 text-slate-300'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-1 mb-1">
                            <div className="flex items-start gap-1.5 flex-1 min-w-0">
                              <FileText className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                              <div className="min-w-0">
                                <span className="font-semibold text-[11px] block truncate leading-tight text-slate-200" title={proto.filename}>
                                  {proto.filename}
                                </span>
                                <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-0.5">
                                  <span>{proto.size_kb} KB</span>
                                  {proto.step_count && <span>• {proto.step_count} steps</span>}
                                  {proto.updated_at && <span>• {proto.updated_at}</span>}
                                </div>
                              </div>
                            </div>
                            {isActive && (
                              <span className="shrink-0 px-1.5 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 rounded text-[9px] font-bold">
                                Loaded
                              </span>
                            )}
                          </div>

                          <div className="mt-1 pt-1 border-t border-slate-700/40 flex items-center justify-end">
                            <button
                              type="button"
                              onClick={() => {
                                onSelectProtocol(proto.filename);
                                if (!isSidebar) onProceedToWorkspace();
                              }}
                              className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 transition-all cursor-pointer ${
                                isActive
                                  ? 'bg-blue-600 text-white shadow-xs'
                                  : 'bg-slate-800 hover:bg-blue-600 text-slate-300 hover:text-white'
                              }`}
                            >
                              <Play className="w-2.5 h-2.5 fill-current" />
                              <span>{isActive ? 'Active in Studio' : 'Load & Automate'}</span>
                            </button>
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

    </div>
  );
};
