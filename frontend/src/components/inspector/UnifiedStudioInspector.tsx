import React, { useState, useEffect } from 'react';
import { Type, Layers, Music, Sliders, ChevronRight } from 'lucide-react';
import { ProjectState, CaptionItem, MotionGraphicItem, GraphicTemplate } from '../../types';
import { SubtitlesInspector } from './SubtitlesInspector';
import { GraphicsTabInspector } from './GraphicsTabInspector';
import { MusicSfxInspector } from './MusicSfxInspector';

interface UnifiedStudioInspectorProps {
  project: ProjectState;
  onUpdateProject: (updated: ProjectState) => void;
  selectedCaptionId: string | null;
  onSelectCaption: (id: string) => void;
  onUpdateCaption: (updated: CaptionItem) => void;
  onDeleteCaption: (id: string) => void;
  onDuplicateCaption?: (id: string) => void;
  onSplitCaption?: (id: string, time: number) => void;
  onAddCaption?: () => void;
  selectedGraphicId: string | null;
  onSelectGraphic: (id: string | null) => void;
  onUpdateGraphic: (updated: MotionGraphicItem) => void;
  onDeleteGraphic: (id: string) => void;
  onAddGraphic: (templateId: string, params: Record<string, any>, start?: number, end?: number, title?: string) => void;
  currentTime: number;
  onTimeSeek: (time: number) => void;
  templates: GraphicTemplate[];
  onTranscribe?: () => Promise<void>;
  isTranscribing?: boolean;
  activeLanguageView: 'english' | 'hindi';
  onToggleLanguageView: () => void;
  activeLinesMode?: 1 | 2;
  onReformatLines?: (lines: 1 | 2) => void;
  onDetectKeywords?: () => Promise<void>;
  syncStylesToAll?: boolean;
  onToggleSyncStylesToAll?: () => void;
  onApplyStyleToAll?: () => void;
  onOpenReasoningLog?: () => void;
  hasReasoningLog?: boolean;
  onAppendVideoTrack?: (videoUrl: string, title: string, duration: number, overlayText: string, instructions: string, sourceCitation?: string) => void;
  captureCurrentCanvasFrame?: () => string | null;
  prefilledOmni?: { prompt: string; cameraMotion: string; headline: string } | null;
  initialTab?: 'subtitles' | 'graphics' | 'music';
}

export const UnifiedStudioInspector: React.FC<UnifiedStudioInspectorProps> = ({
  project,
  onUpdateProject,
  selectedCaptionId,
  onSelectCaption,
  onUpdateCaption,
  onDeleteCaption,
  onDuplicateCaption,
  onSplitCaption,
  onAddCaption,
  selectedGraphicId,
  onSelectGraphic,
  onUpdateGraphic,
  onDeleteGraphic,
  onAddGraphic,
  currentTime,
  onTimeSeek,
  templates,
  onTranscribe,
  isTranscribing,
  activeLanguageView,
  onToggleLanguageView,
  activeLinesMode,
  onReformatLines,
  onDetectKeywords,
  syncStylesToAll,
  onToggleSyncStylesToAll,
  onApplyStyleToAll,
  onOpenReasoningLog,
  hasReasoningLog,
  onAppendVideoTrack,
  captureCurrentCanvasFrame,
  prefilledOmni,
  initialTab = 'subtitles'
}) => {
  const [activeTab, setActiveTab] = useState<'subtitles' | 'graphics' | 'music'>(initialTab);

  useEffect(() => {
    if (selectedGraphicId) {
      setActiveTab('graphics');
    }
  }, [selectedGraphicId]);

  return (
    <aside className="w-96 bg-white border-l border-neutral-200 flex flex-col h-full z-15 select-none shadow-xs text-neutral-900">
      {/* 3 Top-Level Tabs: Subtitles | Graphics | Music/SFX */}
      <div className="flex border-b border-neutral-200 bg-neutral-100 p-1.5 text-xs font-semibold">
        <button
          type="button"
          onClick={() => setActiveTab('subtitles')}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md transition text-xs font-semibold ${
            activeTab === 'subtitles'
              ? 'bg-white text-neutral-900 shadow-2xs border border-neutral-200'
              : 'text-neutral-500 hover:text-neutral-900'
          }`}
        >
          <Type className="h-3.5 w-3.5" />
          <span>Subtitles</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('graphics')}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md transition text-xs font-semibold ${
            activeTab === 'graphics'
              ? 'bg-white text-neutral-900 shadow-2xs border border-neutral-200'
              : 'text-neutral-500 hover:text-neutral-900'
          }`}
        >
          <Layers className="h-3.5 w-3.5" />
          <span>Graphics</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('music')}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-md transition text-xs font-semibold ${
            activeTab === 'music'
              ? 'bg-white text-neutral-900 shadow-2xs border border-neutral-200'
              : 'text-neutral-500 hover:text-neutral-900'
          }`}
        >
          <Music className="h-3.5 w-3.5" />
          <span>Music / SFX</span>
        </button>
      </div>

      {/* Tab Panels */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {activeTab === 'subtitles' && (
          <SubtitlesInspector
            project={project}
            selectedCaptionId={selectedCaptionId}
            onSelectCaption={onSelectCaption}
            onUpdateCaption={onUpdateCaption}
            onDeleteCaption={onDeleteCaption}
            onDuplicateCaption={onDuplicateCaption}
            onSplitCaption={onSplitCaption}
            onAddCaption={onAddCaption}
            onTimeSeek={onTimeSeek}
            onTranscribe={onTranscribe}
            isTranscribing={isTranscribing}
            activeLanguageView={activeLanguageView}
            onToggleLanguageView={onToggleLanguageView}
            activeLinesMode={activeLinesMode}
            onReformatLines={onReformatLines}
            onDetectKeywords={onDetectKeywords}
            syncStylesToAll={syncStylesToAll}
            onToggleSyncStylesToAll={onToggleSyncStylesToAll}
            onApplyStyleToAll={onApplyStyleToAll}
            currentTime={currentTime}
          />
        )}

        {activeTab === 'graphics' && (
          <GraphicsTabInspector
            project={project}
            selectedGraphicId={selectedGraphicId}
            onSelectGraphic={onSelectGraphic}
            onUpdateGraphic={onUpdateGraphic}
            onDeleteGraphic={onDeleteGraphic}
            onAddGraphic={onAddGraphic}
            currentTime={currentTime}
            onTimeSeek={onTimeSeek}
            templates={templates}
            onOpenReasoningLog={onOpenReasoningLog}
            hasReasoningLog={hasReasoningLog}
            onAppendVideoTrack={onAppendVideoTrack}
            captureCurrentCanvasFrame={captureCurrentCanvasFrame}
            prefilledOmni={prefilledOmni}
            onUpdateProject={onUpdateProject}
          />
        )}

        {activeTab === 'music' && (
          <MusicSfxInspector
            project={project}
            onUpdateProject={onUpdateProject}
            currentTime={currentTime}
          />
        )}
      </div>
    </aside>
  );
};
