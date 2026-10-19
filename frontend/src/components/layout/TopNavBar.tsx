import React, { useState, useRef, useEffect } from "react";
import { 
  Film, FolderOpen, Plus, RefreshCw, Undo2, Redo2, 
  Tv, Sparkles, Send, CheckCircle2, Download, Upload,
  PanelRightClose, PanelRightOpen,
  ChevronDown, Layers, FileVideo, Zap, Brain, Clapperboard
} from "lucide-react";
import { ProjectState, DaVinciStatus, TwelveLabsCredits, FeedbackStats } from "../../types";

import { api } from "../../services/api";

interface TopNavBarProps {
  project: ProjectState | null;
  davinciStatus: DaVinciStatus;
  isSaving: boolean;
  saveError?: string;
  isRendering: boolean;
  renderProgress?: { percent: number; frame: number; total_frames: number; status: string; mode?: string } | null;
  canUndo: boolean;
  canRedo: boolean;
  onUndo: () => void;
  onRedo: () => void;
  onOpenProjects: () => void;
  onNewProject: () => void;
  onRelinkMedia: () => void;
  onUploadVideo: (file: File) => void;
  onRenameProject: (newName: string) => void;
  onAspectRatioChange: (ratio: "9:16" | "16:9" | "1:1") => void;
  onSyncToDaVinci: () => void;
  onSaveDaVinciProject: () => void;
  isSavingDaVinciProject?: boolean;
  onExportComp: () => void;
  onBurnAndDownload: (subtitlesOnly?: boolean, forceRerender?: boolean) => void;
  isRightSidebarCollapsed?: boolean;
  onToggleRightSidebar?: () => void;
  onOpenFeedbackDashboard?: () => void;
  onOpenBrandVideo?: () => void;
  onOpenStudio?: () => void;
  feedbackStats?: FeedbackStats | null;
}

export const TopNavBar: React.FC<TopNavBarProps> = ({
  project,
  davinciStatus,
  isSaving,
  saveError,
  isRendering,
  renderProgress,
  canUndo,
  canRedo,
  onUndo,
  onRedo,
  onOpenProjects,
  onNewProject,
  onUploadVideo,
  onRenameProject,
  onAspectRatioChange,
  onSyncToDaVinci,
  onSaveDaVinciProject,
  isSavingDaVinciProject = false,
  onBurnAndDownload,
  isRightSidebarCollapsed = false,
  onToggleRightSidebar,
  onOpenFeedbackDashboard,
  onOpenBrandVideo,
  onOpenStudio,
  feedbackStats
}) => {

  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(project?.name || "Untitled_Project");
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showTwelveLabsModal, setShowTwelveLabsModal] = useState(false);
  const [twelveLabsCredits, setTwelveLabsCredits] = useState<TwelveLabsCredits | null>(null);
  const [isAnalyzingVideo, setIsAnalyzingVideo] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const exportMenuRef = useRef<HTMLDivElement>(null);
  const twelveLabsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getTwelveLabsCredits().then((c) => setTwelveLabsCredits(c));
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target as Node)) {
        setShowExportMenu(false);
      }
      if (twelveLabsRef.current && !twelveLabsRef.current.contains(event.target as Node)) {
        setShowTwelveLabsModal(false);
      }
    };
    if (showExportMenu || showTwelveLabsModal) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showExportMenu, showTwelveLabsModal]);

  const handleNameSubmit = () => {
    setIsEditingName(false);
    if (nameInput.trim() && nameInput !== project?.name) {
      onRenameProject(nameInput.trim());
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUploadVideo(file);
    }
  };

  return (
    <header className="h-13 bg-white border-b border-neutral-200 flex items-center justify-between px-3 sm:px-4 z-20 select-none text-neutral-900 shrink-0">
      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/webm"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Left: App Logo, Projects & Video Upload */}
      <div className="flex items-center gap-2 sm:gap-3">
        <div className="flex items-center gap-2 font-bold text-sm tracking-tight text-neutral-900 mr-1">
          <div className="h-6 w-6 rounded bg-neutral-900 flex items-center justify-center text-white">
            <Film className="h-3.5 w-3.5 stroke-[2.2]" />
          </div>
          <span className="hidden sm:inline font-semibold">Studio</span>
        </div>

        {/* Project Selector / Creator */}
        <div className="flex items-center gap-1 bg-neutral-100 rounded-lg p-0.5 border border-neutral-200">
          <button
            onClick={onOpenProjects}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-white text-neutral-800 hover:bg-neutral-50 border border-neutral-200/80 shadow-2xs transition"
            title="Open or manage projects"
          >
            <FolderOpen className="h-3.5 w-3.5 text-neutral-700" />
            <span>Projects</span>
          </button>
          
          <button
            onClick={onNewProject}
            className="p-1 rounded-md text-neutral-500 hover:text-neutral-900 hover:bg-white transition"
            title="Create new project"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Project Name Editable Field */}
        <div className="flex items-center gap-2 ml-1">
          {isEditingName ? (
            <input
              type="text"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onBlur={handleNameSubmit}
              onKeyDown={(e) => e.key === "Enter" && handleNameSubmit()}
              autoFocus
              className="bg-white text-xs font-semibold text-neutral-900 px-2 py-1 rounded border border-neutral-400 outline-none shadow-2xs"
            />
          ) : (
            <span
              onClick={() => {
                setNameInput(project?.name || "");
                setIsEditingName(true);
              }}
              className="text-xs font-semibold text-neutral-800 hover:text-black cursor-pointer px-2 py-1 rounded hover:bg-neutral-100 transition"
              title="Click to rename project"
            >
              {project?.name || "Loading..."}
            </span>
          )}

          {/* Upload Video Button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-white hover:bg-neutral-50 text-neutral-700 hover:text-neutral-900 text-xs font-semibold transition border border-neutral-200 shadow-2xs"
            title="Upload source MP4 video"
          >
            <Upload className="h-3.5 w-3.5 text-neutral-700" />
            <span className="hidden md:inline">Upload Video</span>
          </button>

          {/* Autosave Status Indicator */}
          <div className="flex items-center gap-1 text-[11px] text-neutral-500 font-mono ml-1">
            {saveError ? <span className="text-amber-800" title={saveError}>Not saved</span> : isSaving ? (
              <span className="flex items-center gap-1 text-amber-700">
                <RefreshCw className="h-3 w-3 animate-spin" /> Saving...
              </span>
            ) : (
              <span className="flex items-center gap-1 text-emerald-700 font-medium">
                <CheckCircle2 className="h-3 w-3" /> Saved
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Center: Aspect Ratio & Undo/Redo */}
      <div className="flex items-center gap-3">
        <div className="flex items-center bg-neutral-100 rounded-md p-0.5 border border-neutral-200 text-xs">
          <button
            onClick={() => onAspectRatioChange("9:16")}
            className={`px-2 py-0.5 rounded text-xs ${
              project?.settings.aspect_ratio === "9:16"
                ? "bg-white text-neutral-900 font-semibold shadow-2xs border border-neutral-200"
                : "text-neutral-600 hover:text-neutral-900"
            }`}
          >
            9:16
          </button>
          <button
            onClick={() => onAspectRatioChange("16:9")}
            className={`px-2 py-0.5 rounded text-xs ${
              project?.settings.aspect_ratio === "16:9"
                ? "bg-white text-neutral-900 font-semibold shadow-2xs border border-neutral-200"
                : "text-neutral-600 hover:text-neutral-900"
            }`}
          >
            16:9
          </button>
        </div>

        {/* Undo / Redo */}
        <div className="flex items-center gap-0.5">
          <button
            onClick={onUndo}
            disabled={!canUndo}
            className="p-1 rounded text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100 disabled:opacity-30 transition"
            title="Undo"
          >
            <Undo2 className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onRedo}
            disabled={!canRedo}
            className="p-1 rounded text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100 disabled:opacity-30 transition"
            title="Redo"
          >
            <Redo2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Right: Export & Integrations */}
      <div className="flex items-center gap-2">
        {/* DaVinci Connection Status Badge */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
            davinciStatus.is_connected
              ? "bg-emerald-50 text-emerald-700 border-emerald-300"
              : "bg-neutral-100 text-neutral-600 border-neutral-200"
          }`}
          title={
            davinciStatus.is_connected
              ? `Connected to DaVinci timeline: ${davinciStatus.timeline_name || "Active"}`
              : "DaVinci Resolve not detected. Compositions and SRT will export locally."
          }
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              davinciStatus.is_connected ? "bg-emerald-500 animate-pulse" : "bg-neutral-400"
            }`}
          />
          <Tv className="h-3 w-3" />
          <span className="hidden md:inline">
            {davinciStatus.is_connected ? "Resolve Live" : "Resolve Standalone"}
          </span>
        </div>

        {/* Studio: films made in one go by AI, then fully editable */}
        {onOpenStudio && (
          <button
            onClick={onOpenStudio}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-semibold transition shadow-2xs bg-neutral-900 hover:bg-neutral-800 text-white border-neutral-900"
            title="Studio: make an editable film from a website or an idea"
          >
            <Clapperboard className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Studio</span>
          </button>
        )}

        {/* Brand film from a website */}
        {onOpenBrandVideo && (
          <button
            onClick={onOpenBrandVideo}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-semibold transition shadow-2xs bg-white hover:bg-neutral-50 text-neutral-900 border-neutral-200"
            title="Make a brand film from a website"
          >
            <Clapperboard className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Brand film</span>
          </button>
        )}

        {/* AI Editorial Feedback & Training Button */}
        {onOpenFeedbackDashboard && (
          <button
            onClick={onOpenFeedbackDashboard}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-semibold transition shadow-2xs bg-purple-50 hover:bg-purple-100 text-purple-900 border-purple-200"
            title="Open Human-In-The-Loop AI Feedback & Training Hub"
          >
            <Brain className="h-3.5 w-3.5 text-purple-700" />
            <span className="hidden sm:inline">Feedback</span>
            <span className="bg-purple-200/80 text-purple-900 px-1.5 py-0.2 rounded text-[10px] font-mono font-bold">
              {feedbackStats ? feedbackStats.total_decisions : "Hub"}
            </span>
          </button>
        )}

        {/* Twelve Labs Credits & Status */}
        <div className="relative" ref={twelveLabsRef}>
          <button
            onClick={() => setShowTwelveLabsModal((prev) => !prev)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium transition shadow-2xs bg-neutral-50 hover:bg-neutral-100 text-neutral-800 border-neutral-200"
            title="Twelve Labs Video Understanding Credits"
          >
            <Zap className="h-3.5 w-3.5 text-neutral-700" />
            <span className="hidden sm:inline font-mono">12Labs</span>
            <span className="bg-neutral-200 text-neutral-800 px-1 py-0.2 rounded text-[10px] font-mono font-medium">
              {twelveLabsCredits ? `${twelveLabsCredits.one_minute_videos_left} left` : "600m left"}
            </span>
          </button>


          {/* Twelve Labs Credit Meter Popover */}
          {showTwelveLabsModal && twelveLabsCredits && (
            <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl shadow-xl border border-neutral-200 p-4 z-50 text-neutral-900 animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between border-b border-neutral-100 pb-3 mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-neutral-100 text-neutral-700">
                    <Zap className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="font-bold text-xs text-neutral-950">Twelve Labs Video Intelligence</div>
                    <div className="text-[10px] font-mono text-neutral-500">Marengo 3.0 Multimodal Index</div>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-[9px] font-mono font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Active
                </span>
              </div>

              {/* Progress Bar of Consumed Allowance */}
              <div className="space-y-1.5 mb-3">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-neutral-500">Indexed Consumption</span>
                  <span className="font-semibold text-neutral-800">
                    {twelveLabsCredits.consumed_minutes} / {twelveLabsCredits.total_credit_minutes} min ({twelveLabsCredits.percent_used}%)
                  </span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-neutral-100 overflow-hidden border border-neutral-200">
                  <div
                    className="h-full bg-neutral-800 rounded-full transition-all duration-500"
                    style={{ width: `${Math.max(3, twelveLabsCredits.percent_used)}%` }}
                  />
                </div>
              </div>

              {/* Key Highlights Grid */}
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-2.5">
                  <div className="text-[10px] font-mono text-neutral-500 uppercase font-medium">1-Min Videos Left</div>
                  <div className="text-lg font-bold text-neutral-900 font-mono mt-0.5">
                    {twelveLabsCredits.one_minute_videos_left}
                  </div>
                  <div className="text-[9px] text-neutral-500 font-mono mt-0.5">
                    {twelveLabsCredits.remaining_minutes} min remaining
                  </div>
                </div>

                <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-2.5">
                  <div className="text-[10px] font-mono text-neutral-500 uppercase font-medium">Validity</div>
                  <div className="text-xs font-bold text-neutral-900 font-mono mt-1">
                    {twelveLabsCredits.expiry_date}
                  </div>
                  <div className="text-[9px] text-neutral-500 font-mono font-medium mt-1">
                    {twelveLabsCredits.days_remaining} days left
                  </div>
                </div>
              </div>

              {/* Video Analysis Action */}
              <div className="space-y-2 pt-1 border-t border-neutral-100">
                <button
                  disabled={isAnalyzingVideo || !project?.id}
                  onClick={async () => {
                    if (!project?.id) return;
                    setIsAnalyzingVideo(true);
                    try {
                      const res = await api.analyzeWithTwelveLabs(project.id);
                      if (res && res.success) {
                        alert(`Video indexed with Twelve Labs!\nAsset ID: ${res.asset_id || res.task_id || 'Ready'}\nStatus: ${res.status || 'Ready'}`);
                        const updated = await api.getTwelveLabsCredits();
                        setTwelveLabsCredits(updated);
                      } else {
                        alert(res?.error || "Twelve Labs indexing could not be completed.");
                      }
                    } catch (e) {
                      alert("Twelve Labs error: " + String(e));
                    } finally {
                      setIsAnalyzingVideo(false);
                    }
                  }}
                  className="w-full py-2 px-3 rounded-lg bg-neutral-900 hover:bg-black text-white font-medium text-xs flex items-center justify-center gap-1.5 transition shadow-2xs disabled:opacity-50"
                >
                  {isAnalyzingVideo ? (
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  <span>{isAnalyzingVideo ? "Indexing in Twelve Labs..." : "Analyze Video with 12Labs"}</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Sync to DaVinci */}
        <button
          onClick={onSyncToDaVinci}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-neutral-50 hover:bg-neutral-100 text-neutral-800 border border-neutral-200 transition"
          title="Send tracks, subtitles, and Fusion comps directly into DaVinci Resolve timeline"
        >
          <Send className="h-3.5 w-3.5 text-neutral-700" />
          <span className="hidden lg:inline">Sync Resolve</span>
        </button>

        {/* Save as DaVinci Project Bundle */}
        <button
          onClick={onSaveDaVinciProject}
          disabled={isSavingDaVinciProject}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-white hover:bg-neutral-50 text-neutral-800 border border-neutral-300 transition shadow-2xs disabled:opacity-50"
          title="Save complete project as DaVinci Resolve bundle"
        >
          {isSavingDaVinciProject ? (
            <RefreshCw className="h-3.5 w-3.5 animate-spin text-neutral-600" />
          ) : (
            <FolderOpen className="h-3.5 w-3.5 text-neutral-700" />
          )}
          <span className="hidden sm:inline">Save DaVinci Project</span>
        </button>

        {/* Export / Burn Video Dropdown */}
        {isRendering ? (
          <div className="flex items-center gap-2 px-3 py-1 rounded-md bg-neutral-100 border border-neutral-300 text-neutral-900 text-xs font-semibold">
            <RefreshCw className="h-3.5 w-3.5 animate-spin text-neutral-700" />
            <span>
              {renderProgress?.percent != null && renderProgress.percent > 0
                ? `Rendering ${renderProgress.percent}%`
                : "Encoding MP4..."}
            </span>
          </div>
        ) : (
          <div className="relative flex items-center" ref={exportMenuRef}>
            <div className="inline-flex rounded-md shadow-2xs">
              <button
                onClick={() => onBurnAndDownload(false, false)}
                className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-l-md bg-neutral-900 hover:bg-black text-white transition"
                title="Export complete video with subtitles and graphics"
              >
                <Download className="h-3.5 w-3.5 stroke-[2.2]" />
                <span>Export MP4</span>
              </button>
              <button
                onClick={() => setShowExportMenu((prev) => !prev)}
                className="px-1.5 py-1 text-xs font-semibold rounded-r-md bg-neutral-900 hover:bg-black text-white border-l border-neutral-700 transition"
                title="Export options"
              >
                <ChevronDown className="h-3.5 w-3.5 stroke-[2.2]" />
              </button>
            </div>

            {/* Dropdown Menu */}
            {showExportMenu && (
              <div className="absolute right-0 top-full mt-1.5 w-64 bg-white rounded-lg shadow-xl border border-neutral-200 p-1.5 z-50 text-neutral-900 animate-in fade-in zoom-in-95 duration-100">
                <button
                  onClick={() => {
                    setShowExportMenu(false);
                    onBurnAndDownload(true, false);
                  }}
                  className="w-full flex items-start gap-2 p-2 rounded hover:bg-neutral-50 text-left transition group"
                >
                  <FileVideo className="h-4 w-4 text-neutral-600 mt-0.5" />
                  <div>
                    <div className="text-xs font-semibold text-neutral-900">Subtitles Only MP4</div>
                    <div className="text-[10px] text-neutral-500">Video with burned-in subtitles only</div>
                  </div>
                </button>

                <button
                  onClick={() => {
                    setShowExportMenu(false);
                    onBurnAndDownload(false, false);
                  }}
                  className="w-full flex items-start gap-2 p-2 rounded hover:bg-neutral-50 text-left transition group mt-0.5"
                >
                  <Layers className="h-4 w-4 text-neutral-600 mt-0.5" />
                  <div>
                    <div className="text-xs font-semibold text-neutral-900">Full Comp MP4</div>
                    <div className="text-[10px] text-neutral-500">Subtitles, graphics, B-roll, and splits</div>
                  </div>
                </button>
              </div>
            )}
          </div>
        )}

        {/* Right Inspector Toggle */}
        {onToggleRightSidebar && (
          <button
            onClick={onToggleRightSidebar}
            className={`p-1.5 rounded-md border transition ml-1 ${
              isRightSidebarCollapsed 
                ? 'bg-neutral-100 hover:bg-neutral-200 text-neutral-800 border-neutral-300' 
                : 'text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100 border-transparent'
            }`}
            title={isRightSidebarCollapsed ? "Expand Inspector" : "Collapse Inspector"}
          >
            {isRightSidebarCollapsed ? <PanelRightOpen className="h-4 w-4" /> : <PanelRightClose className="h-4 w-4" />}
          </button>
        )}
      </div>
    </header>
  );
};
