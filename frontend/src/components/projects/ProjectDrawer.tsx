import { BACKEND_ORIGIN } from '../../services/api';
import React, { useState, useRef } from 'react';
import { X, Plus, FolderOpen, Link2, Check, Clock, FileVideo, Trash2, AlertTriangle, Loader2, CheckSquare, Square } from 'lucide-react';
import { ProjectSummary } from '../../types';

interface ProjectDrawerProps {
  isOpen: boolean;
  projects: ProjectSummary[];
  activeProjectId: string;
  onClose: () => void;
  onSelectProject: (id: string) => void;
  onCreateProject: (name: string, aspectRatio: '9:16' | '16:9') => void;
  onRelinkMedia: (projectId: string, newPath: string) => void;
  onDeleteProject: (projectId: string) => Promise<void>;
  onBulkDeleteProjects?: (projectIds: string[]) => Promise<void>;
}

export const ProjectDrawer: React.FC<ProjectDrawerProps> = ({
  isOpen,
  projects,
  activeProjectId,
  onClose,
  onSelectProject,
  onCreateProject,
  onRelinkMedia,
  onDeleteProject,
  onBulkDeleteProjects
}) => {
  const [newProjectName, setNewProjectName] = useState('');
  const [aspectRatio, setAspectRatio] = useState<'9:16' | '16:9'>('9:16');
  const [relinkId, setRelinkId] = useState<string | null>(null);
  const [relinkPath, setRelinkPath] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [showBulkConfirm, setShowBulkConfirm] = useState(false);

  const lastSelection=useRef<number|null>(null);
  const dragStart=useRef<number|null>(null);
  const dragBase=useRef<Set<string>>(new Set());
  const [downloadBusy,setDownloadBusy]=useState(false);
  const [downloadError,setDownloadError]=useState('');
  async function downloadSelected(){
    setDownloadBusy(true);setDownloadError('');
    try{
      const response=await fetch(`${BACKEND_ORIGIN}/api/projects/bulk/download`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project_ids:Array.from(selectedIds)})});
      if(!response.ok){const error=await response.json();throw new Error(error.detail||'Download failed');}
      const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download='selected-projects.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);
    }catch(error){setDownloadError(String(error));}finally{setDownloadBusy(false);}
  }
  if (!isOpen) return null;

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (newProjectName.trim()) {
      onCreateProject(newProjectName.trim(), aspectRatio);
      setNewProjectName('');
      onClose();
    }
  };

  const handleRelinkSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (relinkId && relinkPath.trim()) {
      onRelinkMedia(relinkId, relinkPath.trim());
      setRelinkId(null);
      setRelinkPath('');
    }
  };

  const toggleSelect = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const index=projects.findIndex(p=>p.id===id);
    if(e.shiftKey&&lastSelection.current!==null){const lo=Math.min(index,lastSelection.current),hi=Math.max(index,lastSelection.current);setSelectedIds(prev=>new Set([...prev,...projects.slice(lo,hi+1).map(p=>p.id)]));return;}
    lastSelection.current=index;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedIds.size === projects.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(projects.map((p) => p.id)));
    }
  };

  const handleExecuteBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    setIsBulkDeleting(true);
    try {
      const idsArray = Array.from(selectedIds);
      if (onBulkDeleteProjects) {
        await onBulkDeleteProjects(idsArray);
      } else {
        for (const pid of idsArray) {
          await onDeleteProject(pid);
        }
      }
      setSelectedIds(new Set());
      setShowBulkConfirm(false);
    } finally {
      setIsBulkDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-neutral-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-neutral-200 w-full max-w-xl rounded-2xl shadow-xl overflow-hidden flex flex-col max-h-[85vh] text-neutral-900">
        {/* Header */}
        <div className="p-4 border-b border-neutral-200 flex items-center justify-between bg-neutral-50">
          <div className="flex items-center gap-2 font-semibold text-sm">
            <FolderOpen className="h-4 w-4 text-neutral-700" />
            <span>Projects</span>
          </div>
          <button
            aria-label="Close projects"
            onClick={onClose}
            className="p-1 rounded-lg text-neutral-400 hover:text-neutral-700 hover:bg-neutral-200/50 transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Create Project Bar */}
        <form onSubmit={handleCreate} className="p-3 bg-white border-b border-neutral-200 flex items-center gap-2">
          <input
            type="text"
            placeholder="New Project Name"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            className="flex-1 bg-neutral-50 border border-neutral-200 rounded-lg px-3 py-2 text-xs text-neutral-900 outline-none focus:border-neutral-400 focus:bg-white transition"
          />
          <div className="flex bg-neutral-100 rounded-lg p-0.5 border border-neutral-200 text-xs font-medium">
            <button
              type="button"
              onClick={() => setAspectRatio('9:16')}
              className={`px-2 py-1 rounded transition ${aspectRatio === '9:16' ? 'bg-white text-neutral-900 shadow-xs' : 'text-neutral-500'}`}
            >
              9:16
            </button>
            <button
              type="button"
              onClick={() => setAspectRatio('16:9')}
              className={`px-2 py-1 rounded transition ${aspectRatio === '16:9' ? 'bg-white text-neutral-900 shadow-xs' : 'text-neutral-500'}`}
            >
              16:9
            </button>
          </div>
          <button
            type="submit"
            className="px-3.5 py-2 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white font-semibold text-xs transition"
          >
            Create
          </button>
        </form>

        {/* Toolbar: Select All & Bulk Actions */}
        <div className="px-4 py-2 bg-neutral-50 border-b border-neutral-200 flex items-center justify-between text-xs text-neutral-600">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleSelectAll}
              className="flex items-center gap-1.5 hover:text-neutral-900 transition font-medium cursor-pointer"
            >
              {selectedIds.size === projects.length && projects.length > 0 ? (
                <CheckSquare className="h-3.5 w-3.5 text-neutral-900" />
              ) : (
                <Square className="h-3.5 w-3.5 text-neutral-400" />
              )}
              <span>{selectedIds.size === projects.length && projects.length > 0 ? 'Deselect All' : 'Select All'}</span>
            </button>
            <span className="text-neutral-400">|</span>
            <span className="text-neutral-500">{projects.length} Total Projects</span>
          </div>

          {selectedIds.size > 0 && (
            <button
              type="button"
              onClick={() => setShowBulkConfirm(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 font-semibold transition cursor-pointer"
            >
              <Trash2 className="h-3.5 w-3.5 text-red-600" />
              <span>Delete Selected ({selectedIds.size})</span>
            </button>
          )}
        </div>

        {downloadError&&<p role="alert" className="p-3 text-red-700">{downloadError}</p>}
        <div className="px-4 py-2 text-xs">Hold Shift and drag across project rows to select a range.
          <button disabled={!selectedIds.size||downloadBusy} onClick={downloadSelected} className="ml-2 border rounded px-2 py-1 disabled:opacity-40">{downloadBusy?'Preparing ZIP…':`Download selected (${selectedIds.size})`}</button>
        </div>
        {/* Projects List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {projects.map((p, index) => {
            const isActive = p.id === activeProjectId;
            const isSelected = selectedIds.has(p.id);
            return (
              <div
                key={p.id}
                onPointerDown={(e)=>{if(!e.shiftKey)dragStart.current=null;if(e.shiftKey){e.preventDefault();dragStart.current=index;dragBase.current=new Set(selectedIds);setSelectedIds(new Set([...selectedIds,p.id]));}}}
                onPointerEnter={(e)=>{if(dragStart.current!==null&&e.buttons===1){const lo=Math.min(index,dragStart.current),hi=Math.max(index,dragStart.current);setSelectedIds(new Set([...dragBase.current,...projects.slice(lo,hi+1).map(x=>x.id)]));}}}
                onPointerUp={()=>{dragStart.current=null;}}
                onClick={(e) => {
                  if(e.shiftKey)return;
                  onSelectProject(p.id);
                  onClose();
                }}
                className={`p-3 rounded-xl border flex items-center justify-between text-xs cursor-pointer transition ${
                  isActive
                    ? 'bg-neutral-50 border-neutral-900 ring-1 ring-neutral-900'
                    : 'bg-white hover:bg-neutral-50 border-neutral-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    aria-label={`Select project ${p.name} ${p.id}`}
                    onPointerDown={(e) => e.stopPropagation()}
                    onClick={(e) => toggleSelect(p.id, e)}
                    className="text-neutral-400 hover:text-neutral-800 transition cursor-pointer"
                  >
                    {isSelected ? (
                      <CheckSquare className="h-4 w-4 text-neutral-900" />
                    ) : (
                      <Square className="h-4 w-4" />
                    )}
                  </button>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-neutral-900 text-sm">{p.name}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-100 text-neutral-600 border border-neutral-200">
                        {p.aspect_ratio}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-neutral-500 mt-0.5">
                      <span>{p.caption_count} Captions</span>
                      <span>•</span>
                      <span>{p.duration_seconds.toFixed(0)}s</span>
                      <span>•</span>
                      <span>{p.updated_at.split('T')[0]}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onPointerDown={(e) => e.stopPropagation()}
                    onClick={(e) => {
                      e.stopPropagation();
                      setRelinkId(p.id);
                    }}
                    className="p-1.5 rounded-lg hover:bg-neutral-100 text-neutral-500 hover:text-neutral-800 transition cursor-pointer"
                    title="Relink source media path"
                  >
                    <Link2 className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onPointerDown={(e) => e.stopPropagation()}
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteConfirmId(p.id);
                    }}
                    className="p-1.5 rounded-lg hover:bg-red-50 text-neutral-400 hover:text-red-600 transition cursor-pointer"
                    title="Delete project"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                  {isActive && <Check className="h-4 w-4 text-neutral-900 stroke-[2.5]" />}
                </div>
              </div>
            );
          })}
        </div>

        {/* Single Delete Confirmation */}
        {deleteConfirmId && (
          <div className="p-4 bg-red-50 border-t border-red-200 space-y-3">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
              <div>
                <div className="text-xs font-bold text-red-950">
                  Delete Project
                </div>
                <div className="text-[11px] text-red-800 mt-0.5">
                  Delete <strong>{projects.find((p) => p.id === deleteConfirmId)?.name || deleteConfirmId}</strong>? Its files will be moved to macOS Trash.
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleteConfirmId(null)}
                disabled={isDeleting}
                className="px-3 py-1.5 rounded-lg bg-white border border-neutral-300 text-neutral-700 text-xs font-medium hover:bg-neutral-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (deleteConfirmId) {
                    setIsDeleting(true);
                    try {
                      const idToDelete = deleteConfirmId;
                      await onDeleteProject(idToDelete);
                      setSelectedIds((prev) => {
                        const next = new Set(prev);
                        next.delete(idToDelete);
                        return next;
                      });
                    } finally {
                      setIsDeleting(false);
                      setDeleteConfirmId(null);
                    }
                  }
                }}
                disabled={isDeleting}
                className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
              >
                {isDeleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                <span>Delete</span>
              </button>
            </div>
          </div>
        )}

        {/* Bulk Delete Confirmation */}
        {showBulkConfirm && (
          <div className="p-4 bg-red-50 border-t border-red-200 space-y-3">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
              <div>
                <div className="text-xs font-bold text-red-950">
                  Bulk Delete {selectedIds.size} Projects
                </div>
                <div className="text-[11px] text-red-800 mt-0.5">
                  Are you sure you want to permanently delete these {selectedIds.size} selected projects? Their files will be moved to macOS Trash.
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowBulkConfirm(false)}
                disabled={isBulkDeleting}
                className="px-3 py-1.5 rounded-lg bg-white border border-neutral-300 text-neutral-700 text-xs font-medium hover:bg-neutral-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteBulkDelete}
                disabled={isBulkDeleting}
                className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
              >
                {isBulkDeleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                <span>Delete {selectedIds.size} Projects</span>
              </button>
            </div>
          </div>
        )}

        {/* Relink Modal Sub-dialog */}
        {relinkId && (
          <form onSubmit={handleRelinkSubmit} className="p-3 bg-neutral-50 border-t border-neutral-200 space-y-2">
            <span className="text-xs font-semibold text-neutral-800">Relink Media Path</span>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="/absolute/path/to/source.mp4"
                value={relinkPath}
                onChange={(e) => setRelinkPath(e.target.value)}
                className="flex-1 bg-white border border-neutral-300 rounded-lg p-2 text-xs text-neutral-900 outline-none"
              />
              <button
                type="submit"
                className="px-3 py-1.5 rounded-lg bg-neutral-900 text-white font-semibold text-xs hover:bg-neutral-800 cursor-pointer"
              >
                Save
              </button>
              <button
                type="button"
                onClick={() => setRelinkId(null)}
                className="px-3 py-1.5 rounded-lg bg-white border border-neutral-300 text-neutral-700 text-xs cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
