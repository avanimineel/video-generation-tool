import {EditorialPlanPanel} from './components/modals/EditorialPlanPanel';
import React, { useState, useEffect, useRef } from 'react';
import { PanelRightClose, PanelRightOpen, Download, CheckCircle2, X, ExternalLink, FileVideo, RefreshCw, FolderOpen, Loader2 } from 'lucide-react';
import { TopNavBar } from './components/layout/TopNavBar';
import { VideoViewer } from './components/viewer/VideoViewer';
import { Timeline } from './components/timeline/Timeline';
import { UnifiedStudioInspector } from './components/inspector/UnifiedStudioInspector';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { ProjectDrawer } from './components/projects/ProjectDrawer';
import { VisualReasoningLogModal } from './components/modals/VisualReasoningLogModal';
import { EditorialFeedbackModal } from './components/modals/EditorialFeedbackModal';
import { BrandVideoModal } from './components/modals/BrandVideoModal';
import { Studio } from './components/studio/Studio';
import { api, DEFAULT_TEMPLATES, VisualReasoningItem } from './services/api';
import { ProjectState, ProjectSummary, DaVinciStatus, GraphicTemplate, CaptionItem, MotionGraphicItem, FeedbackStats } from './types';

export const App: React.FC = () => {
  const [project, setProject] = useState<ProjectState>(() => api.getInitialProject());
  const [projectsList, setProjectsList] = useState<ProjectSummary[]>(() => api.getInitialProjectsList());
  const [templates, setTemplates] = useState<GraphicTemplate[]>(() => DEFAULT_TEMPLATES);
  const [davinciStatus, setDavinciStatus] = useState<DaVinciStatus>({
    is_running: false,
    is_connected: false,
    fps: 30,
    script_api_available: false
  });

  // Visual Reasoning & Feedback State
  const [isReasoningModalOpen, setIsReasoningModalOpen] = useState<boolean>(false);
  const [visualReasoningLog, setVisualReasoningLog] = useState<VisualReasoningItem[]>([]);
  const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState<boolean>(false);
  const [feedbackStats, setFeedbackStats] = useState<FeedbackStats | null>(null);


  // Playback & Selection State
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [selectedCaptionId, setSelectedCaptionId] = useState<string | null>(() => {
    const init = api.getInitialProject();
    return init.captions.length > 0 ? init.captions[0].id : null;
  });
  const [selectedGraphicId, setSelectedGraphicId] = useState<string | null>(null);

  // UI Modals, Autosave & Rendering
  const [isProjectDrawerOpen, setIsProjectDrawerOpen] = useState<boolean>(false);
  const [saveError, setSaveError] = useState('');
  const [backendReady, setBackendReady] = useState(false);
  const [isBrandVideoOpen, setIsBrandVideoOpen] = useState(false);
  const [isStudioOpen, setIsStudioOpen] = useState(false);
  const [saveRetry, setSaveRetry] = useState(0);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isRendering, setIsRendering] = useState<boolean>(false);
  const [isSavingDaVinciProject, setIsSavingDaVinciProject] = useState<boolean>(false);
  const [davinciBundleModal, setDavinciBundleModal] = useState<any>(null);
  const [renderProgress, setRenderProgress] = useState<{
    percent: number;
    frame: number;
    total_frames: number;
    status: string;
    mode?: string;
  } | null>(null);
  const [downloadModal, setDownloadModal] = useState<{
    isOpen: boolean;
    fileName: string;
    fileSize?: number;
    subtitlesOnly: boolean;
    downloadUrl: string;
  } | null>(null);
  const [isTranscribing, setIsTranscribing] = useState<boolean>(false);
  const [isTranslating, setIsTranslating] = useState<boolean>(false);
  const [isAutoProducing, setIsAutoProducing] = useState<boolean>(false);
  const [autoProduceStatusText, setAutoProduceStatusText] = useState<string>('');
  const [activeLanguageView, setActiveLanguageView] = useState<'english' | 'hindi'>('english');
  const [syncStylesToAll, setSyncStylesToAll] = useState<boolean>(true);
  const [activeLinesMode, setActiveLinesMode] = useState<1 | 2>(1);
  const [prefilledOmni, setPrefilledOmni] = useState<{ prompt: string; cameraMotion: string; headline: string } | null>(null);
  const [isRightSidebarCollapsed, setIsRightSidebarCollapsed] = useState<boolean>(false);

  // Undo / Redo History Stack
  const [history, setHistory] = useState<ProjectState[]>(() => [api.getInitialProject()]);
  const [historyIndex, setHistoryIndex] = useState<number>(0);

  const pushHistory = (newState: ProjectState) => {
    setHistory((prev) => [...prev.slice(0, historyIndex + 1), newState]);
    setHistoryIndex((prev) => prev + 1);
  };

  const handleUndo = () => {
    if (historyIndex > 0) {
      const prev = {...history[historyIndex - 1],updated_at:project.updated_at};
      setHistoryIndex(historyIndex - 1);
      setProject(prev);
      api.saveLocalProject(prev);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const next = {...history[historyIndex + 1],updated_at:project.updated_at};
      setHistoryIndex(historyIndex + 1);
      setProject(next);
      api.saveLocalProject(next);
    }
  };

  // 1. Initial Load & Background Hydration from Backend
  useEffect(() => {
    let isMounted = true;
    const init = async () => {
      try {
        const [pList, tList, dStatus] = await Promise.all([
          api.listProjects(),
          api.getTemplates(),
          api.getDaVinciStatus()
        ]);
        if (!isMounted) return;
        if (pList && pList.length > 0) setProjectsList(pList);
        if (tList && tList.length > 0) setTemplates(tList);
        if (dStatus) setDavinciStatus(dStatus);

        if (pList && pList.length > 0) {
          const params = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
          const urlProjId = params?.get('project');
          if (urlProjId && !pList.some(p => p.id === urlProjId)) {
            setSaveError('The linked project is no longer available. Choose a project to continue.');
            setIsProjectDrawerOpen(true);
            return;
          }
          const targetId = urlProjId || pList[0].id;
          const fullProj = await api.getProject(targetId);
          if (isMounted && fullProj) {
            if (!fullProj.video_url || fullProj.video_url.startsWith('blob:')) {
              fullProj.video_url = api.getSourceVideoUrl(fullProj.id);
            }
            setProject(fullProj);
            setBackendReady(true);
            setSaveError('');
            setHistory([fullProj]);
            setHistoryIndex(0);
            if (fullProj.captions.length > 0) {
              setSelectedCaptionId(fullProj.captions[0].id);
            }
            const job=await api.getAutoProductionStatus(targetId);
            if (isMounted && (job?.status==='running' || job?.status==='queued')) {
              setIsAutoProducing(true);
              setAutoProduceStatusText('Continuing the automatic edit…');
              void api.runAutoProduction(targetId, false, 'small', setAutoProduceStatusText).then(result=>{
                if(!isMounted)return;
                if(result.project)setProject(prev=>prev?.id===targetId?{...result.project,video_url:api.getSourceVideoUrl(targetId)}:prev);
                if(!result.success)alert(result.error);
              }).finally(()=>{if(isMounted)setIsAutoProducing(false)});
            }
            const timeParam = params?.get('time');
            if (timeParam) {
              const parsedTime = parseFloat(timeParam);
              if (!isNaN(parsedTime)) {
                setCurrentTime(parsedTime);
              }
            }
          }
        }
      } catch (e) {
        setSaveError('Could not load the saved project. Browser edits are retained; reconnect before saving.');
      }
    };
    init();
    return () => {
      isMounted = false;
    };
  }, []);

  const autosaveContent=project ? JSON.stringify({...project,updated_at:""}) : "";
  // 2. Continuous Autosave (debounced 1.5s)
  useEffect(() => {
    if (!project || isAutoProducing || !backendReady) return;
    api.saveLocalProject(project);
    const timer = setTimeout(async () => {
      setIsSaving(true);
      try {
        const result=await api.autosaveProject(project.id, project);
        setSaveError('');
        setProject(prev=>prev?.id===project.id && prev.updated_at===project.updated_at ? {...prev,updated_at:result.autosaved_at,graphics:prev.graphics.map(g=>result.subject_masks?.[g.id]?{...g,parameters:{...g.parameters,subject_mask:undefined,subject_mask_error:undefined,...result.subject_masks[g.id]}}:g)} : prev);
      } catch (e) {
        setSaveError(e instanceof Error ? e.message : 'Save failed. Your changes remain in this browser.');
      } finally {
        setIsSaving(false);
      }
    }, 1500);
    return () => clearTimeout(timer);
  }, [autosaveContent, isAutoProducing, backendReady, saveRetry]);

  // Surface saved captions while the remaining edit is still processing.
  useEffect(() => {
    if (!isAutoProducing || !project?.id) return;
    const id=project.id;
    let active=true;
    const timer=setInterval(async()=>{
      try {
        const [saved,report]=await Promise.all([api.getProject(id),api.getEditorialReport(id)]);
        if (!active) return;
        if (saved?.captions?.length) setProject(prev=>prev?.id===id ? {...saved,video_url:api.getSourceVideoUrl(id)} : prev);
        if (report?.status==='running') setAutoProduceStatusText(String(report.stage).replace(/_/g,' ')+'…');
      } catch { /* Keep the last visible progress during a transient disconnect. */ }
    },5000);
    return ()=>{active=false;clearInterval(timer)};
  },[isAutoProducing,project?.id]);

  // 2B. Editorial Feedback Stats & Visual Reasoning Log Sync
  useEffect(() => {
    if (project?.id) {
      api.getFeedbackStats(project.id).then((s) => setFeedbackStats(s)).catch(() => {});
      api.getVisualReasoningLog(project.id).then((log) => {
        if (Array.isArray(log)) setVisualReasoningLog(log);
      }).catch(() => {});
    }
  }, [project?.id]);

  // 3. Playback Loop

  useEffect(() => {
    let animId: number;
    let lastTime = performance.now();

    if (project?.source_media_path || project?.video_url) return;
    const loop = (now: number) => {
      if (isPlaying && project) {
        const delta = (now - lastTime) / 1000;
        setCurrentTime((prev) => {
          const next = prev + delta;
          if (next >= (project.duration_seconds || 15)) {
            setIsPlaying(false);
            return 0;
          }
          return next;
        });
      }
      lastTime = now;
      if (isPlaying) {
        animId = requestAnimationFrame(loop);
      }
    };

    if (isPlaying) {
      lastTime = performance.now();
      animId = requestAnimationFrame(loop);
    }
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, project?.duration_seconds, project?.source_media_path, project?.video_url]);

  // Upload video handler
  const handleUploadVideo = async (file: File) => {
    if (!project?.id) {
      alert('Please select or create a project first before uploading video.');
      return;
    }
    setIsPlaying(false);
    setCurrentTime(0);
    const currentProjectId = project.id;
    setIsSaving(true);
    try {
      setAutoProduceStatusText(`Uploading ${file.name} (0%)...`);
      setIsAutoProducing(true);
      const uploadRes = await api.uploadVideo(currentProjectId, file, (pct) => {
        setAutoProduceStatusText(pct>=100 ? 'Upload received. Preparing a playable preview…' : `Uploading ${file.name} (${pct}%)...`);
      });

      // Fetch the full updated project state to guarantee all tracks, captions, settings remain intact
      let freshProject = await api.getProject(currentProjectId);
      if (!freshProject || !freshProject.id) {
        if (uploadRes?.project) {
          freshProject = uploadRes.project;
        } else {
          freshProject = {
            ...project,
            duration_seconds: uploadRes.duration_seconds || project.duration_seconds,
            name: uploadRes.name || project.name,
          };
        }
      }
      freshProject.video_url = api.getSourceVideoUrl(currentProjectId);

      setProject(freshProject);
      api.saveLocalProject(freshProject);
      pushHistory(freshProject);

      setIsAutoProducing(true);
      setIsTranscribing(true);
      setAutoProduceStatusText('Transcribing dialogue, indexing in Twelve Labs, and generating graphics...');

      (async () => {
        try {
          const autoRes = await api.runAutoProduction(currentProjectId, false, 'small', setAutoProduceStatusText);
          if (!autoRes?.success) {
            if (autoRes?.project) {
              const partial = {...autoRes.project, video_url: api.getSourceVideoUrl(currentProjectId)};
              setProject(prev => prev.id === currentProjectId ? partial : prev);
              api.saveLocalProject(partial);
              pushHistory(partial);
              if (partial.captions?.length) setSelectedCaptionId(partial.captions[0].id);
            }
            throw new Error(autoRes?.editorial_report?.errors?.join('\n') || autoRes?.error || 'Automatic editing failed');
          }
          if (autoRes?.editorial_report?.status === 'blocked') {
            setIsReasoningModalOpen(false);
            alert(autoRes.editorial_report.errors.join('\n') + '\nOpen Review automatic edit for details.');
          }
          if (autoRes && autoRes.project) {
            const fullyFormedProject: ProjectState = {
              ...autoRes.project,
              video_url: api.getSourceVideoUrl(currentProjectId)
            };
            setProject(fullyFormedProject);
            api.saveLocalProject(fullyFormedProject);
            pushHistory(fullyFormedProject);
            if (fullyFormedProject.captions && fullyFormedProject.captions.length > 0) {
              setSelectedCaptionId(fullyFormedProject.captions[0].id);
            }
          } else {
            const transRes = await api.transcribe(currentProjectId);
            if (transRes && transRes.captions && transRes.captions.length > 0) {
              const latestProj = await api.getProject(currentProjectId);
              const transcribedProject: ProjectState = {
                ...latestProj,
                video_url: api.getSourceVideoUrl(currentProjectId),
                captions: transRes.captions,
                detected_language: transRes.detected_language || latestProj.detected_language
              };
              setProject(transcribedProject);
              api.saveLocalProject(transcribedProject);
              pushHistory(transcribedProject);
              setSelectedCaptionId(transRes.captions[0].id);
            }
          }
          if (autoRes?.reasoning_log && Array.isArray(autoRes.reasoning_log)) {
            setVisualReasoningLog(autoRes.reasoning_log);
          } else {
            api.getVisualReasoningLog(currentProjectId).then(log => {
              if (Array.isArray(log)) setVisualReasoningLog(log);
            }).catch(() => {});
          }
          api.getFeedbackStats(currentProjectId).then(s => setFeedbackStats(s)).catch(() => {});
          const updatedList = await api.listProjects();
          setProjectsList(updatedList);
        } catch (uploadErr) {
          console.warn('[Upload] Auto-production notice:', uploadErr);
          alert('Automatic editing could not finish: '+String(uploadErr));
        } finally {
          setIsAutoProducing(false);
          setIsTranscribing(false);
          setAutoProduceStatusText('');
        }
      })();
    } catch (e) {
      setIsAutoProducing(false);
      setIsTranscribing(false);
      setAutoProduceStatusText('');
      console.error('Upload failed:', e);
      alert('Video upload failed: ' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setIsSaving(false);
    }
  };

  const handleBurnAndDownload = async (subtitlesOnly: boolean = true, forceRerender: boolean = false) => {
    setIsRendering(true);
    const targetFrames = Math.max(1, Math.round((project.duration_seconds || 15) * (project.fps || 30)));
    setRenderProgress({
      percent: 0,
      frame: 0,
      total_frames: targetFrames,
      status: 'starting',
      mode: subtitlesOnly ? 'subtitles_only' : 'full'
    });

    const pollTimer = setInterval(async () => {
      try {
        const prog = await api.getRenderProgress(project.id);
        if (prog && (prog.status === 'rendering' || prog.percent > 0)) {
          setRenderProgress({
            percent: prog.percent,
            frame: prog.frame,
            total_frames: prog.total_frames || targetFrames,
            status: prog.status,
            mode: prog.mode || (subtitlesOnly ? 'subtitles_only' : 'full')
          });
        }
      } catch (e) {
        // Non-blocking progress polling
      }
    }, 750);

    try {
      const res = await api.renderBurnIn(project.id, subtitlesOnly, forceRerender, project);
      clearInterval(pollTimer);

      if (res && res.success) {
        const extName = subtitlesOnly ? 'subtitled' : 'burned';
        const fileName = `${project.name}_${extName}.mp4`;
        const downloadUrl = api.getDownloadMp4Url(project.id, subtitlesOnly);

        await api.downloadMp4File(project.id, fileName, subtitlesOnly);

        setDownloadModal({
          isOpen: true,
          fileName,
          fileSize: res.file_size,
          subtitlesOnly,
          downloadUrl
        });
      } else {
        alert('Burn-in render failed: ' + (res?.error || 'Unknown error occurred.'));
      }
    } catch (e) {
      clearInterval(pollTimer);
      console.error('Render error:', e);
      alert('Burn-in render failed: ' + String(e));
    } finally {
      clearInterval(pollTimer);
      setIsRendering(false);
      setRenderProgress(null);
    }
  };

  const handleUpdateCaption = (updated: CaptionItem) => {
    setProject((prev) => {
      let updatedCaptions: CaptionItem[];
      if (syncStylesToAll) {
        updatedCaptions = prev.captions.map((c) => {
          if (c.id === updated.id) return updated;
          return {
            ...c,
            pos_x: updated.pos_x,
            pos_y: updated.pos_y,
            style: { ...updated.style }
          };
        });
      } else {
        updatedCaptions = prev.captions.map((c) => (c.id === updated.id ? updated : c));
      }

      const newProject = {
        ...prev,
        captions: updatedCaptions
      };
      pushHistory(newProject);
      api.saveProject(newProject.id, newProject).catch(() => {});
      return newProject;
    });
  };

  const handleUpdateCaptionPosition = (id: string, posX: number, posY: number, duringGraphic?: boolean) => {
    setProject((prev) => {
      let updatedCaptions: CaptionItem[];
      if (duringGraphic) {
        updatedCaptions = prev.captions.map((c) => {
          if (c.id === id || syncStylesToAll) {
            return {
              ...c,
              pos_x_during_graphic: posX,
              pos_y_during_graphic: posY
            };
          }
          return c;
        });
      } else if (syncStylesToAll) {
        updatedCaptions = prev.captions.map((c) => ({
          ...c,
          pos_x: posX,
          pos_y: posY
        }));
      } else {
        updatedCaptions = prev.captions.map((c) => (c.id === id ? { ...c, pos_x: posX, pos_y: posY } : c));
      }

      const updated = {
        ...prev,
        captions: updatedCaptions
      };
      api.saveProject(updated.id, updated).catch(() => {});
      return updated;
    });
  };

  const handleApplyStyleToAll = (sourceCaptionId?: string) => {
    setProject((prev) => {
      const targetId = sourceCaptionId || selectedCaptionId || prev.captions[0]?.id;
      const sourceCap = prev.captions.find((c) => c.id === targetId);
      if (!sourceCap) return prev;

      const newProject = {
        ...prev,
        captions: prev.captions.map((c) => ({
          ...c,
          pos_x: sourceCap.pos_x,
          pos_y: sourceCap.pos_y,
          style: { ...sourceCap.style }
        }))
      };
      pushHistory(newProject);
      api.saveProject(newProject.id, newProject).catch(() => {});
      return newProject;
    });
  };

  const handleReformatSubtitleLines = (linesMode: 1 | 2) => {
    setActiveLinesMode(linesMode);
    if (linesMode === 2 && project.captions.length > 1) {
      const rechunked: CaptionItem[] = [];
      for (let i = 0; i < project.captions.length; i += 2) {
        const c1 = project.captions[i];
        const c2 = project.captions[i + 1];

        if (c2 && (c2.start - c1.end < 2.0)) {
          const t1 = c1.translated_text || c1.text;
          const t2 = c2.translated_text || c2.text;
          rechunked.push({
            ...c1,
            id: `cap_2l_${i}_${Date.now()}`,
            end: c2.end,
            text: `${c1.text}\n${c2.text}`,
            translated_text: c1.translated_text || c2.translated_text ? `${t1}\n${t2}` : undefined,
            words: [...c1.words, ...c2.words],
            style: {
              ...c1.style,
              max_lines: 2
            }
          });
        } else {
          rechunked.push({
            ...c1,
            style: { ...c1.style, max_lines: 2 }
          });
          if (c2) {
            rechunked.push({
              ...c2,
              style: { ...c2.style, max_lines: 2 }
            });
          }
        }
      }
      const newProject = { ...project, captions: rechunked };
      setProject(newProject);
      pushHistory(newProject);
    }
  };

  const handleDetectKeywords = async () => {
    try {
      const updatedCaptions = project.captions.map((cap) => {
        const words = cap.words.map((w) => {
          const lower = w.word.toLowerCase().replace(/[^a-z0-9]/g, '');
          const isKey = ['lung', 'heart', 'liver', 'cancer', '7cm', '10cm', 'biopsy', 'surgery', 'stage', 'scan'].includes(lower);
          return {
            ...w,
            is_keyword: isKey,
            keyword_category: isKey ? ('condition' as const) : undefined
          };
        });
        return {
          ...cap,
          words,
          style: {
            ...cap.style,
            has_keyword_emphasis: true
          }
        };
      });
      const newProj = { ...project, captions: updatedCaptions };
      setProject(newProj);
      pushHistory(newProj);
    } catch (e) {
      console.error('Keyword detection error:', e);
    }
  };

  const handleSplitCaption = async (captionId: string, splitTime: number) => {
    try {
      const res = await api.splitCaption(project.id, captionId, splitTime);
      const newProject = { ...project, captions: res.captions };
      setProject(newProject);
      pushHistory(newProject);
    } catch (e) {
      const targetIdx = project.captions.findIndex((c) => c.id === captionId);
      if (targetIdx === -1) return;
      const cap = project.captions[targetIdx];
      if (!(cap.start < splitTime && splitTime < cap.end)) return;

      const words1 = cap.words.filter((w) => w.end <= splitTime || w.start < splitTime);
      const words2 = cap.words.filter((w) => w.start >= splitTime);

      const cap1: CaptionItem = {
        ...cap,
        id: `${cap.id}_a`,
        start: cap.start,
        end: splitTime,
        text: words1.map((w) => w.word).join(" ") || cap.text,
        words: words1.length > 0 ? words1 : cap.words.slice(0, Math.max(1, Math.floor(cap.words.length / 2)))
      };

      const cap2: CaptionItem = {
        ...cap,
        id: `${cap.id}_b`,
        start: splitTime,
        end: cap.end,
        text: words2.map((w) => w.word).join(" ") || cap.text,
        words: words2.length > 0 ? words2 : cap.words.slice(Math.max(1, Math.floor(cap.words.length / 2)))
      };

      const newCaptions = [...project.captions];
      newCaptions.splice(targetIdx, 1, cap1, cap2);
      const newProject = { ...project, captions: newCaptions };
      setProject(newProject);
      pushHistory(newProject);
    }
  };

  const handleDeleteCaption = (id: string) => {
    const newProject = {
      ...project,
      captions: project.captions.filter((c) => c.id !== id)
    };
    setProject(newProject);
    pushHistory(newProject);
    if (newProject.captions.length > 0) {
      setSelectedCaptionId(newProject.captions[0].id);
    } else {
      setSelectedCaptionId(null);
    }
    api.saveProject(newProject.id, newProject).catch(() => {});
  };

  const handleDuplicateCaption = (id: string) => {
    const cap = project.captions.find((c) => c.id === id);
    if (!cap) return;
    const dup: CaptionItem = {
      ...cap,
      id: `cap_dup_${Date.now()}`,
      start: cap.end + 0.1,
      end: cap.end + 0.1 + (cap.end - cap.start)
    };
    const newProject = { ...project, captions: [...project.captions, dup] };
    setProject(newProject);
    pushHistory(newProject);
    setSelectedCaptionId(dup.id);
  };

  const handleAddCaption = () => {
    const newCap: CaptionItem = {
      id: `cap_manual_${Date.now()}`,
      start: currentTime,
      end: currentTime + 2.5,
      text: 'New Spoken Dialogue',
      pos_x: 0.5,
      pos_y: 0.8,
      words: [
        { word: 'New', start: currentTime, end: currentTime + 0.6 },
        { word: 'Spoken', start: currentTime + 0.6, end: currentTime + 1.4 },
        { word: 'Dialogue', start: currentTime + 1.4, end: currentTime + 2.5 }
      ],
      style: {
        font_family: 'Inter',
        font_weight: '700',
        font_size: 30,
        text_color: '#FFFFFF',
        outline_color: '#000000',
        outline_width: 2,
        shadow_color: 'rgba(0,0,0,0.5)',
        shadow_blur: 6,
        shadow_offset_x: 0,
        shadow_offset_y: 2,
        has_background: true,
        background_color: '#000000',
        background_opacity: 0.8,
        corner_radius: 12,
        padding_x: 16,
        padding_y: 8,
        line_height: 1.2,
        letter_spacing: 0,
        text_align: 'center',
        is_uppercase: false,
        animation_type: 'none',
        highlight_active_color: '#FFFFFF',
        highlight_past_color: '#9CA3AF',
        highlight_future_color: '#D1D5DB',
        highlight_scale: 1,
        highlight_bounce: false
      },
      source_language: 'en'
    };
    const newProject = { ...project, captions: [...project.captions, newCap] };
    setProject(newProject);
    pushHistory(newProject);
    setSelectedCaptionId(newCap.id);
  };

  const handleTranscribe = async (rawText?: string, wordsPerCap: number = 4) => {
    setIsTranscribing(true);
    try {
      await api.saveProject(project.id, project).catch(() => {});
      const res = await api.transcribe(project.id, rawText, wordsPerCap, undefined, 'transcribe', 'base');
      if (res && res.captions) {
        const newProject = {
          ...project,
          captions: res.captions,
          detected_language: res.detected_language
        };
        setProject(newProject);
        api.saveLocalProject(newProject);
        pushHistory(newProject);
        if (res.captions.length > 0) {
          setSelectedCaptionId(res.captions[0].id);
        }
      }
    } catch (e) {
      console.error('Transcription error:', e);
      alert('Transcription failed: ' + String(e));
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleAddGraphic = (
    templateId: string,
    params: Record<string, any>,
    start?: number,
    end?: number,
    title?: string
  ) => {
    const s = start !== undefined ? start : currentTime;
    const isReport = templateId === 'article_reconstruction' || templateId === 'digital_highlighter';
    const defaultDur = isReport ? 5.0 : 1.0;
    const e = end !== undefined ? end : Math.min((project.duration_seconds || 15), currentTime + defaultDur);
    const tmpl = templates.find((t) => t.id === templateId);

    const isCutaway = templateId === 'cutaway_fullscreen' || templateId === 'youtube_insert';
    const isSplit = templateId === 'vertical_split_50_50' || templateId === 'split_screen_vertical';

    const newGraphic: MotionGraphicItem = {
      id: `graphic_${Date.now()}`,
      start: s,
      end: e,
      template_id: templateId,
      title: title || tmpl?.name || 'Graphic Overlay',
      parameters: {
        ...(tmpl?.default_params || {}),
        ...params
      },
      pos_x: 0.5,
      pos_y: 0.5,
      scale: 1.0,
      track: 'V3',
      placement_mode: isCutaway ? 'insert' : 'overlay',
      split_layout: isSplit ? 'split_50_50_vertical' : 'none'
    };

    const newProject = {
      ...project,
      graphics: [...project.graphics, newGraphic]
    };
    setProject(newProject);
    pushHistory(newProject);
    setSelectedGraphicId(newGraphic.id);
  };

  const handleUpdateGraphic = (updated: MotionGraphicItem) => {
    const newProject = {
      ...project,
      graphics: project.graphics.map((item) => (item.id === updated.id ? updated : item))
    };
    setProject(newProject);
    pushHistory(newProject);
  };

  const handleDeleteGraphic = (id: string) => {
    const newProject = {
      ...project,
      graphics: project.graphics.filter((g) => g.id !== id)
    };
    setProject(newProject);
    pushHistory(newProject);
    if (selectedGraphicId === id) {
      setSelectedGraphicId(null);
    }
    api.saveProject(newProject.id, newProject).catch(() => {});
  };

  const handleClearAllGraphics = () => {
    const newProject = {
      ...project,
      graphics: []
    };
    setProject(newProject);
    pushHistory(newProject);
    setSelectedGraphicId(null);
    api.saveProject(newProject.id, newProject).catch(() => {});
  };

  // Keyboard shortcut: Delete / Backspace to delete selected graphic or caption
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Delete' && e.key !== 'Backspace') return;
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.tagName === 'SELECT' ||
          target.isContentEditable)
      ) {
        return;
      }

      if (selectedGraphicId) {
        e.preventDefault();
        handleDeleteGraphic(selectedGraphicId);
      } else if (selectedCaptionId) {
        e.preventDefault();
        handleDeleteCaption(selectedCaptionId);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedGraphicId, selectedCaptionId, project]);

  const handleUpdateGraphicTiming = (id: string, newStart: number, newEnd: number) => {
    const newProject = {
      ...project,
      graphics: project.graphics.map((g) => (g.id === id ? { ...g, start: newStart, end: newEnd } : g))
    };
    setProject(newProject);
    pushHistory(newProject);
  };

  const handleUpdateCaptionTiming = (id: string, newStart: number, newEnd: number) => {
    const newProject = {
      ...project,
      captions: project.captions.map((c) => (c.id === id ? { ...c, start: newStart, end: newEnd } : c))
    };
    setProject(newProject);
    pushHistory(newProject);
  };

  const handleDeleteAudioTrack = (trackId: string) => {
    const updatedAudio = (project.audio_tracks || []).filter((t) => t.id !== trackId);
    const newProject = {
      ...project,
      audio_tracks: updatedAudio
    };
    setProject(newProject);
    pushHistory(newProject);
    api.saveProject(newProject.id, newProject).catch(() => {});
  };

  const handleSwitchProject = async (id: string) => {
    const fullProj = await api.getProject(id);
    if (fullProj) {
      if (!fullProj.video_url || fullProj.video_url.startsWith('blob:')) {
        fullProj.video_url = api.getSourceVideoUrl(fullProj.id);
      }
      setBackendReady(true); setSaveError('');
      const url=new URL(window.location.href);url.searchParams.set('project',id);url.searchParams.delete('time');window.history.replaceState({},'',url);
      setProject(fullProj);
      setHistory([fullProj]);
      setHistoryIndex(0);
      setCurrentTime(0);
      if (fullProj.captions.length > 0) {
        setSelectedCaptionId(fullProj.captions[0].id);
      }
    }
  };

  const handleCreateProject = async (name: string, ratio: '9:16' | '16:9') => {
    const newProj = await api.createProject(name, ratio);
    setBackendReady(true); setSaveError('');
    const url=new URL(window.location.href);url.searchParams.set('project',newProj.id);url.searchParams.delete('time');window.history.replaceState({},'',url);
    setProject(newProj);
    setHistory([newProj]);
    setHistoryIndex(0);
    setCurrentTime(0);
    if (newProj.captions.length > 0) {
      setSelectedCaptionId(newProj.captions[0].id);
    }
    setProjectsList(await api.listProjects());
  };

  const handleRelinkMedia = async (projectId: string, newPath: string) => {
    const updated = await api.relinkMedia(projectId, newPath);
    setProject(updated);
    setProjectsList(await api.listProjects());
  };

  const handleDeleteProject = async (projectId: string) => {
    try {
      const ok = await api.deleteProject(projectId);
      if (!ok) {
        alert('Failed to delete project from server');
        return;
      }
      const updatedList = await api.listProjects();
      setProjectsList(updatedList);
      if (projectId === project.id) {
        if (updatedList.length > 0) {
          await handleSwitchProject(updatedList[0].id);
        } else {
          await handleCreateProject('New_Project', '9:16');
        }
      }
    } catch (e) {
      console.error('Failed to delete project:', e);
      alert('Delete project failed: ' + String(e));
    }
  };

  const handleBulkDeleteProjects = async (projectIds: string[]) => {
    try {
      const ok = await api.bulkDeleteProjects(projectIds);
      if (!ok) {
        alert('Failed to delete selected projects from server');
        return;
      }
      const updatedList = await api.listProjects();
      setProjectsList(updatedList);
      if (projectIds.includes(project.id)) {
        if (updatedList.length > 0) {
          await handleSwitchProject(updatedList[0].id);
        } else {
          await handleCreateProject('New_Project', '9:16');
        }
      }
    } catch (e) {
      console.error('Bulk delete error:', e);
      alert('Bulk delete failed: ' + String(e));
    }
  };

  const handleSyncToDaVinci = async () => {
    const res = await api.syncToDaVinci(project.id);
    alert(res.message || 'Synchronized to DaVinci Resolve timeline!');
    setDavinciStatus(await api.getDaVinciStatus());
  };

  const handleSaveDaVinciProject = async () => {
    setIsSavingDaVinciProject(true);
    try {
      const res = await api.exportDaVinciBundle(project.id);
      if (res.success) {
        setDavinciBundleModal(res);
      } else {
        alert(res.error || 'Failed to save DaVinci Resolve project bundle.');
      }
    } catch (e) {
      alert('Error exporting DaVinci project bundle');
    } finally {
      setIsSavingDaVinciProject(false);
    }
  };

  const captureCanvasSnapshot = (): string | null => {
    try {
      const videoEl = document.querySelector('video') as HTMLVideoElement | null;
      if (!videoEl) return null;
      const canvas = document.createElement('canvas');
      canvas.width = videoEl.videoWidth || 720;
      canvas.height = videoEl.videoHeight || 1280;
      const ctx = canvas.getContext('2d');
      if (!ctx) return null;
      ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL('image/jpeg', 0.85);
    } catch (e) {
      return null;
    }
  };

  const handleAppendOmniVideoTrack = (
    videoUrl: string,
    title: string,
    segDuration: number,
    overlayText: string,
    instructions: string,
    sourceCitation?: string
  ) => {
    const startTime = currentTime;
    const endTime = Math.min((project.duration_seconds || 15), startTime + Math.max(3, segDuration));

    const newG: MotionGraphicItem = {
      id: `omni_video_${Date.now()}`,
      start: startTime,
      end: endTime,
      template_id: 'vertical_split_50_50',
      title: title || 'Omni Split Scene',
      parameters: {
        headline: overlayText,
        source_citation: sourceCitation || 'Generated Asset',
        media_url: videoUrl,
        media_type: 'video',
        split_ratio: 0.5
      },
      pos_x: 0.5,
      pos_y: 0.5,
      scale: 1.0,
      media_url: videoUrl,
      media_type: 'video',
      track: 'V3',
      placement_mode: 'overlay',
      split_layout: 'split_50_50_vertical'
    };
    const newProject = { ...project, graphics: [...project.graphics, newG] };
    setProject(newProject);
    pushHistory(newProject);
    api.saveProject(newProject.id, newProject).catch(() => {});
    setSelectedGraphicId(newG.id);
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-neutral-100 text-neutral-900 overflow-hidden font-sans">
      {/* 1. Top Navigation Bar */}
      <TopNavBar
        project={project}
        davinciStatus={davinciStatus}
        isSaving={isSaving}
        saveError={saveError || (!backendReady ? 'Loading saved project' : undefined)}
        isRendering={isRendering}
        renderProgress={renderProgress}
        canUndo={historyIndex > 0}
        canRedo={historyIndex < history.length - 1}
        onUndo={handleUndo}
        onRedo={handleRedo}
        onOpenProjects={() => setIsProjectDrawerOpen(true)}
        onNewProject={() => setIsProjectDrawerOpen(true)}
        onRelinkMedia={() => setIsProjectDrawerOpen(true)}
        onUploadVideo={handleUploadVideo}
        onRenameProject={async (newName) => {
          const updated = await api.renameProject(project.id, newName);
          setProject(updated);
          setProjectsList(await api.listProjects());
        }}
        onAspectRatioChange={(ratio) => {
          const newProj = {
            ...project,
            settings: { ...project.settings, aspect_ratio: ratio }
          };
          setProject(newProj);
          pushHistory(newProj);
        }}
        onSyncToDaVinci={handleSyncToDaVinci}
        onSaveDaVinciProject={handleSaveDaVinciProject}
        isSavingDaVinciProject={isSavingDaVinciProject}
        onExportComp={() => {}}
        onBurnAndDownload={handleBurnAndDownload}
        isRightSidebarCollapsed={isRightSidebarCollapsed}
        onToggleRightSidebar={() => setIsRightSidebarCollapsed((prev) => !prev)}
        onOpenFeedbackDashboard={() => setIsFeedbackModalOpen(true)}
        onOpenBrandVideo={() => setIsBrandVideoOpen(true)}
        onOpenStudio={() => setIsStudioOpen(true)}
        feedbackStats={feedbackStats}
      />


      <EditorialPlanPanel onBusy={setIsAutoProducing} projectId={project.id} onSeek={setCurrentTime} onUpdated={p=>{const next={...p,video_url:api.getSourceVideoUrl(p.id)};setProject(next);pushHistory(next)}} />
      {saveError && <div role="alert" className="px-4 py-2 bg-amber-50 border-b border-amber-200 text-amber-900 text-sm flex items-center gap-3"><span>{saveError}</span><button onClick={()=>setSaveRetry(v=>v+1)} disabled={!backendReady} className="underline">Retry save</button><button onClick={()=>setIsProjectDrawerOpen(true)} className="underline">Open projects</button></div>}
      {!isAutoProducing && project.source_media_path && <div className="px-4 py-2 text-xs bg-neutral-50 border-b text-neutral-600">Video prepared · {project.captions.length} captions · {project.captions.filter(c => /[A-Za-z0-9]/.test(c.translated_text || "")).length} English subtitle lines · {project.graphics.filter(g => !g.parameters?.retention_camera && !['caption_cover','authored_title'].includes(g.template_id)).length} added visuals{project.graphics.some(g => g.parameters?.retention_camera) ? ` · ${project.graphics.filter(g => g.parameters?.retention_camera).length} camera beats` : ''}. {(project.ai_ingestion?.errors?.length || project.ai_ingestion?.status==='needs_review') ? "Automatic editing needs attention. Open Review automatic edit for details and retry." : project.ai_ingestion?.status==='completed_with_gaps' ? `Edit finished with gaps: ${(project.ai_ingestion?.summary?.scorecard?.reasons || []).join(' ')} Open Review automatic edit for details.` : "Open Review automatic edit to inspect inserted or skipped treatments."}</div>}
      {/* 1B. AI Auto-Production Status Banner */}
      {isAutoProducing && (
        <div className="bg-neutral-900 text-white px-4 py-2 text-xs flex items-center justify-between border-b border-neutral-800 z-30">
          <div className="flex items-center gap-2.5">
            <Loader2 className="h-4 w-4 animate-spin text-neutral-300 shrink-0" />
            <span className="font-semibold">Auto-Production Active:</span>
            <span className="text-neutral-300">
              {autoProduceStatusText || 'Transcribing dialogue, analyzing video, and generating graphics...'}
            </span>
          </div>
        </div>
      )}

      {/* 2. Main Studio Workspace: Center Viewer & Right 3-Tab Inspector */}
      <div className="flex-1 min-h-0 flex overflow-hidden relative">
        {/* Center: Real-Time Video Viewer */}
        <VideoViewer
          project={project}
          currentTime={currentTime}
          isPlaying={isPlaying}
          selectedCaptionId={selectedCaptionId || (project.captions[0]?.id ?? null)}
          onTimeUpdate={(t) => setCurrentTime(t)}
          onTogglePlay={() => setIsPlaying(!isPlaying)}
          onSelectCaption={(id) => {
            setSelectedCaptionId(id);
            setSelectedGraphicId(null);
          }}
          onUpdateCaptionPosition={handleUpdateCaptionPosition}
          activeLanguageView={activeLanguageView}
          onUpdateSettings={(newSettings) => {
            const updated = { ...project, settings: newSettings };
            setProject(updated);
            pushHistory(updated);
            api.saveProject(updated.id, updated).catch(() => {});
          }}
          onUpdateGraphic={(updatedGraphic) => {
            const updated = {
              ...project,
              graphics: project.graphics.map((g) => (g.id === updatedGraphic.id ? updatedGraphic : g))
            };
            setProject(updated);
            pushHistory(updated);
            api.saveProject(updated.id, updated).catch(() => {});
          }}
        />

        {/* Right 3-Tab Inspector (Subtitles | Graphics | Music/SFX) */}
        {isRightSidebarCollapsed ? (
          <div className="w-10 bg-white border-l border-neutral-200 flex flex-col items-center py-3 z-15 select-none transition-all shadow-2xs shrink-0">
            <button
              onClick={() => setIsRightSidebarCollapsed(false)}
              className="p-1.5 rounded text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 transition"
              title="Expand Inspector"
            >
              <PanelRightOpen className="w-4 h-4" />
            </button>
            <div className="mt-8 [writing-mode:vertical-lr] text-[10px] font-bold text-neutral-400 tracking-wider">
              INSPECTOR
            </div>
          </div>
        ) : (
          <div className="relative flex shrink-0">
            <button
              onClick={() => setIsRightSidebarCollapsed(true)}
              className="absolute -left-3 top-3 z-30 bg-white hover:bg-neutral-100 text-neutral-500 hover:text-neutral-800 border border-neutral-300 rounded-full p-1 shadow-2xs transition"
              title="Collapse Inspector"
            >
              <PanelRightClose className="w-3 h-3" />
            </button>
            
            <ErrorBoundary fallbackTitle="Studio Inspector">
              <UnifiedStudioInspector
                project={project}
                onUpdateProject={(updated) => {
                  setProject(updated);
                  pushHistory(updated);
                  api.saveProject(updated.id, updated).catch(() => {});
                }}
                selectedCaptionId={selectedCaptionId}
                onSelectCaption={(id) => {
                  setSelectedCaptionId(id);
                  setSelectedGraphicId(null);
                }}
                onUpdateCaption={handleUpdateCaption}
                onDeleteCaption={handleDeleteCaption}
                onDuplicateCaption={handleDuplicateCaption}
                onSplitCaption={handleSplitCaption}
                onAddCaption={handleAddCaption}
                selectedGraphicId={selectedGraphicId}
                onSelectGraphic={(id) => {
                  setSelectedGraphicId(id);
                  if (id) setSelectedCaptionId(null);
                }}
                onUpdateGraphic={handleUpdateGraphic}
                onDeleteGraphic={handleDeleteGraphic}
                onAddGraphic={handleAddGraphic}
                currentTime={currentTime}
                onTimeSeek={(t) => setCurrentTime(t)}
                templates={templates}
                onTranscribe={handleTranscribe}
                isTranscribing={isTranscribing}
                activeLanguageView={activeLanguageView}
                onToggleLanguageView={() => setActiveLanguageView((v) => (v === 'english' ? 'hindi' : 'english'))}
                activeLinesMode={activeLinesMode}
                onReformatLines={handleReformatSubtitleLines}
                onDetectKeywords={handleDetectKeywords}
                syncStylesToAll={syncStylesToAll}
                onToggleSyncStylesToAll={() => setSyncStylesToAll((prev) => !prev)}
                onApplyStyleToAll={() => handleApplyStyleToAll(selectedCaptionId || undefined)}
                onOpenReasoningLog={() => setIsReasoningModalOpen(true)}
                hasReasoningLog={visualReasoningLog.length > 0}
                onAppendVideoTrack={handleAppendOmniVideoTrack}
                captureCurrentCanvasFrame={captureCanvasSnapshot}
                prefilledOmni={prefilledOmni}
              />
            </ErrorBoundary>
          </div>
        )}
      </div>

      {/* 3. Bottom Multi-Track Timeline (Light Theme) */}
      <Timeline
        project={project}
        currentTime={currentTime}
        selectedCaptionId={selectedCaptionId || (project.captions[0]?.id ?? null)}
        onTimeUpdate={(t) => setCurrentTime(t)}
        onSelectCaption={(id) => {
          setSelectedCaptionId(id);
          setSelectedGraphicId(null);
        }}
        onSplitCaption={handleSplitCaption}
        onUpdateCaptionTiming={handleUpdateCaptionTiming}
        onAddCaption={handleAddCaption}
        onDeleteCaption={handleDeleteCaption}
        selectedGraphicId={selectedGraphicId}
        onSelectGraphic={(id) => {
          setSelectedGraphicId(id);
          setSelectedCaptionId(null);
        }}
        onDeleteGraphic={handleDeleteGraphic}
        onClearAllGraphics={handleClearAllGraphics}
        onUpdateGraphicTiming={handleUpdateGraphicTiming}
        onDeleteAudioTrack={handleDeleteAudioTrack}
      />

      {/* 4. Project Modal Drawer with Bulk Deletion */}
      <ProjectDrawer
        isOpen={isProjectDrawerOpen}
        projects={projectsList}
        activeProjectId={project.id}
        onClose={() => setIsProjectDrawerOpen(false)}
        onSelectProject={handleSwitchProject}
        onCreateProject={handleCreateProject}
        onRelinkMedia={handleRelinkMedia}
        onDeleteProject={handleDeleteProject}
        onBulkDeleteProjects={handleBulkDeleteProjects}
      />

      {/* 5. Download Ready Modal */}
      {downloadModal?.isOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-2xs flex items-center justify-center z-50 p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-xl shadow-2xl border border-neutral-200 max-w-md w-full p-6 text-neutral-900">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="h-9 w-9 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-bold text-base text-neutral-900">Video Render Complete</h3>
                  <p className="text-xs text-neutral-500">Your MP4 is ready to use</p>
                </div>
              </div>
              <button
                onClick={() => setDownloadModal(null)}
                className="p-1 rounded text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="bg-neutral-50 rounded-lg p-3 border border-neutral-200 mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-neutral-200 text-neutral-800 rounded">
                  <FileVideo className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-xs truncate text-neutral-900">{downloadModal.fileName}</div>
                  <div className="flex items-center gap-2 mt-0.5 text-[11px] text-neutral-500 font-mono">
                    <span>{downloadModal.subtitlesOnly ? 'Subtitles Only' : 'Full Composition'}</span>
                    {downloadModal.fileSize && (
                      <>
                        <span>•</span>
                        <span>{(downloadModal.fileSize / (1024 * 1024)).toFixed(1)} MB</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={async () => {
                  await api.downloadMp4File(project.id, downloadModal.fileName, downloadModal.subtitlesOnly);
                }}
                className="flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-lg bg-neutral-900 hover:bg-black text-white font-semibold text-xs transition cursor-pointer"
              >
                <Download className="h-4 w-4" />
                <span>Save to Downloads</span>
              </button>

              <a
                href={downloadModal.downloadUrl}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-center p-2 rounded-lg border border-neutral-200 hover:bg-neutral-100 text-neutral-700 text-xs font-semibold transition"
                title="Open in new tab"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
          </div>
        </div>
      )}

      {/* 6. DaVinci Resolve Bundle Modal */}
      {davinciBundleModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-2xs flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white border border-neutral-200 rounded-xl max-w-lg w-full p-6 shadow-2xl text-neutral-900 space-y-4">
            <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-neutral-100 text-neutral-800 font-bold">
                  <FolderOpen className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-bold text-base">DaVinci Resolve Project Saved</h3>
                  <p className="text-xs text-neutral-500">Project bundle ready to open</p>
                </div>
              </div>
              <button
                onClick={() => setDavinciBundleModal(null)}
                className="text-neutral-400 hover:text-neutral-800 text-lg font-bold px-2 py-1 rounded hover:bg-neutral-100"
              >
                ✕
              </button>
            </div>

            <div className="bg-neutral-50 rounded-lg p-3 border border-neutral-200 space-y-2 text-xs font-mono">
              <div className="text-neutral-500 text-[10px] uppercase font-bold tracking-wider">Bundle Directory:</div>
              <div className="text-neutral-800 break-all select-all font-semibold bg-white p-2 rounded border border-neutral-200">
                {davinciBundleModal.bundle_dir}
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-neutral-100">
              <button
                onClick={async () => {
                  await api.openInFinder(project.id);
                }}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-neutral-100 hover:bg-neutral-200 text-neutral-800 transition"
              >
                Reveal in Finder
              </button>
              <button
                onClick={async () => {
                  await api.openInDaVinci(project.id);
                }}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-neutral-900 hover:bg-black text-white transition"
              >
                Open in Resolve
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. Reasoning Log Modal */}
      <VisualReasoningLogModal
        isOpen={isReasoningModalOpen}
        onClose={() => setIsReasoningModalOpen(false)}
        reasoningLog={visualReasoningLog}
        onSeekTime={(t) => setCurrentTime(t)}
        projectName={project.name}
        projectId={project.id}
        onOpenFeedbackDashboard={() => setIsFeedbackModalOpen(true)}
      />

      {isBrandVideoOpen && <BrandVideoModal onClose={() => setIsBrandVideoOpen(false)} />}
      {isStudioOpen && <Studio onClose={() => setIsStudioOpen(false)} />}

      {/* 8. Human-in-the-Loop AI Feedback & Training Data Modal */}
      <EditorialFeedbackModal
        project={project}
        currentTime={currentTime}
        onUpdated={p=>{setProject(p);pushHistory(p);}}
        isOpen={isFeedbackModalOpen}
        onClose={() => {
          setIsFeedbackModalOpen(false);
          api.getFeedbackStats(project.id).then((s) => setFeedbackStats(s)).catch(() => {});
        }}
        currentProjectId={project.id}
        onJumpToTime={(t) => setCurrentTime(t)}
      />
    </div>
  );
};

