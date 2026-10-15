import { ProjectState, ProjectSummary, DaVinciStatus, GraphicTemplate, CaptionItem, CaptionStyle, MotionGraphicItem, DynamicGraphicSample, DynamicSamplesResponse, TwelveLabsCredits, EditorialDecision, FeedbackStats, FewShotExportResponse } from '../types';

export const DEFAULT_STYLE: CaptionStyle = {
  font_family: 'Montserrat',
  font_weight: '900',
  font_size: 32,
  text_color: '#FFFFFF',
  outline_color: '#000000',
  outline_width: 2,
  shadow_color: 'rgba(0,0,0,0.6)',
  shadow_blur: 8,
  shadow_offset_x: 0,
  shadow_offset_y: 3,
  has_background: true,
  background_color: '#000000',
  background_opacity: 0.8,
  corner_radius: 16,
  padding_x: 20,
  padding_y: 10,
  line_height: 1.25,
  letter_spacing: 0,
  text_align: 'center',
  is_uppercase: false,
  animation_type: 'none',
  highlight_active_color: '#CCFF00',
  highlight_past_color: '#A3A3A3',
  highlight_future_color: '#FFFFFF',
  highlight_scale: 1,
  highlight_bounce: false,
  max_lines: 1,
  has_highlight: false,
  has_shadow: true,
  pacing_mode: 'full_line',
  has_keyword_emphasis: false,
  keyword_accent_color: '#CCFF00',
  keyword_font_family: 'Playfair Display',
  keyword_contrast_badge: true,
  contrast_block_mode: 'pill'
};

export interface VisualReasoningItem {
  cue_index: number;
  graphic_id: string;
  template_id: string;
  template_name: string;
  timestamp_start: number;
  timestamp_end: number;
  timestamp_formatted: string;
  duration_sec: number;
  spoken_trigger_phrase: string;
  trigger_term: string;
  cue_category: string;
  timestamp_logic: string;
  image_logic: string;
  layout_logic: string;
  pacing_logic: string;
  search_query: string;
  source_provider?: string;
  media_url?: string | null;
  media_thumb?: string | null;
  media_type?: string;
}

export interface DetectDimensionsAndCuesResponse {
  detected_count: number;
  cues: any[];
  graphics: MotionGraphicItem[];
  reasoning_log: VisualReasoningItem[];
}

export const DEFAULT_TEMPLATES: GraphicTemplate[] = [
  // 0. Spatial Layout & Documentary Archival Templates
  {
    id: 'split_screen_vertical',
    name: '50/50 Vertical Split (B-Roll Top / Speaker Bottom)',
    category: 'Spatial & Documentary',
    description: 'Dynamic canvas split with archival B-roll on top (featuring source credit) and talking head on bottom.',
    default_params: {
      broll_title: 'Documentary B-Roll & Visual Evidence',
      speaker_label: 'Speaker / Narrator',
      source_citation: 'Source: Research & Media Archives',
      split_ratio: 0.5,
      divider_color: '#FFFFFF',
      media_url: 'https://images.unsplash.com/photo-1530497610245-94d3c16cda28?auto=format&fit=crop&w=1200&q=80',
      media_type: 'image'
    }
  },
  {
    id: 'dimension_callout',
    name: 'Architectural Dimension Line & Measurement',
    category: 'Spatial & Documentary',
    description: 'Animated blueprint-style dimension line with tick marks, arrows, and measurement tag pill.',
    default_params: {
      measurement_text: '14 FEET LONG',
      subtext: 'Fuselage Wingspan Spec',
      line_orientation: 'horizontal', // 'horizontal' | 'vertical'
      line_length_pct: 65,
      color: '#00F0FF'
    }
  },
  {
    id: 'source_citation',
    name: 'Automated Source Citation Overlay',
    category: 'Spatial & Documentary',
    description: 'Unobtrusive documentary text overlay anchored in the top-left corner establishing archival credibility.',
    default_params: {
      source_name: 'Source: National Archives (1969)',
      doc_type: 'Declassified Mission Footage',
      position: 'top_left'
    }
  },
  {
    id: 'archival_filter',
    name: 'Mixed-Media Archival Treatment (16mm Grain / B&W)',
    category: 'Spatial & Documentary',
    description: 'Cohesive mixed-media treatment applying 16mm film grain, vintage vignette, and contrast grade.',
    default_params: {
      filter_style: '16mm_film_grain', // '16mm_film_grain' | 'bw_archival' | 'vintage_sepia' | 'crt_scanlines'
      grain_intensity: 0.45,
      vignette_depth: 0.55
    }
  },
  {
    id: 'corner_bug',
    name: 'Static Top-Right Corner Bug Watermark',
    category: 'Spatial & Documentary',
    description: 'Fixed high-contrast brand watermark anchored in the top-right corner across all scenes.',
    default_params: {
      bug_text: 'CHRONICLES',
      badge_style: 'minimal_high_contrast',
      position: 'top_right'
    }
  },
  {
    id: 'documentary_outro',
    name: '3D Rotating Globe Outro & Teaser Carousel',
    category: 'Spatial & Documentary',
    description: 'Environmental 3D rotating wireframe globe, episode teaser carousel, and urgent retention CTA.',
    default_params: {
      globe_headline: 'MISSION LOG COMPLETE',
      teaser_1: 'Part II: The Stratosphere',
      teaser_2: 'Part III: Deep Oceanic Trench',
      cta_button_text: 'WATCH PART 2 NOW • UP NEXT',
      accent_color: '#00F0FF'
    }
  },

  // 1. Research & Evidence Visualizer Templates
  {
    id: 'thematic_canvas',
    name: 'Thematic Medical Canvas (Oncology / Neuro / ECG)',
    category: 'Evidence Visualizer',
    description: 'Procedural vector field background (Cellular structure, Neural synapsing, or ECG waves) behind evidence.',
    default_params: {
      field_type: 'cardiology', // 'cardiology' | 'cellular' | 'neurology' | 'genomics' | 'orthopedics'
      headline: 'CLINICAL CARDIOLOGY TRIAL',
      subtext: 'Phase III Multicenter Study (n=4,280)',
      glow_color: '#00F0FF'
    }
  },
  {
    id: 'digital_highlighter',
    name: 'Digital Highlighter (Scientific Journal)',
    category: 'Evidence Visualizer',
    description: 'Panned peer-reviewed medical journal paper with animated glowing translucent marker highlight.',
    default_params: {
      journal_title: 'The New England Journal of Medicine',
      citation_doi: 'NEJM • Vol. 389 No. 14 • Evidence Synthesis',
      dense_passage: 'In a double-blind randomized clinical trial, participants administering the intervention exhibited a 42% reduction in secondary inflammatory markers (p < 0.001) compared with baseline control regimens across a 12-week observational window.',
      highlight_sentence: 'exhibited a 42% reduction in secondary inflammatory markers',
      marker_color: '#FFE600', // '#FFE600' (Yellow) | '#00F0FF' (Cyan) | '#CCFF00' (Lime)
      paper_tint: '#F8F7F2'
    }
  },
  {
    id: 'article_reconstruction',
    name: 'Reconstructed News / Medical Article (Screenshot 5)',
    category: 'Spatial & Documentary',
    description: 'Authentic editorial article reconstruction with publisher masthead logo, bold headline, matched paragraph, and kinetic animated fluorescent marker.',
    default_params: {
      publisher: 'Scroll.in',
      headline: 'Dombivli hospital assault: Doctor resigns after attack by Shinde Sena corporator, fearing for safety',
      date: 'May 14, 2024 • Investigative Archive',
      source_url: 'https://scroll.in/latest/1067824/dombivli-hospital-assault',
      paragraph: "The 26-year-old resident medical officer at the Kalyan-Dombivli Municipal Corporation's Shastri Nagar Hospital said he had left the city after receiving threats and would 'never go back'.",
      highlight_quote: "he had left the city after receiving threats and would 'never go back'",
      marker_color: '#00E5FF',
      paper_theme: 'editorial_clean',
      track: 'V4',
      placement_mode: 'overlay',
      animation: 'slow_zoom_in'
    }
  },
  {
    id: 'jargon_translation',
    name: 'Jargon-to-Plain English Pop-Up',
    category: 'Evidence Visualizer',
    description: 'Floating split card translating dense scientific findings into punchy plain English for viewers.',
    default_params: {
      clinical_finding: 'Significant downregulation of serum C-reactive protein (CRP) & pro-inflammatory cytokines.',
      plain_english: 'Body inflammation dropped dramatically in just 14 days!',
      takeaway_badge: '↓ 45% Inflammation',
      badge_color: '#CCFF00',
      icon_type: 'flame_off'
    }
  },

  // 2. Visual Storytelling & Metaphor Engine Templates
  {
    id: 'metaphor_sequence',
    name: 'Metaphorical Physiological Sequence',
    category: 'Metaphor Engine',
    description: 'Animated everyday metaphor explaining physiological mechanisms without graphic surgical footage.',
    default_params: {
      metaphor_type: 'lock_and_key', // 'lock_and_key' | 'immune_shield' | 'clogged_pipe' | 'battery_recharge'
      headline: 'HOW RECEPTORS WORK',
      caption: 'The hormone acts like a custom key unlocking cellular energy.',
      theme_color: '#CCFF00'
    }
  },
  {
    id: 'contextual_broll',
    name: 'Contextual Stock B-Roll Overlay',
    category: 'Metaphor Engine',
    description: 'Clinical / lifestyle stock footage card with soft feathered edge blending and vignette mask.',
    default_params: {
      broll_topic: 'nutrition', // 'clinic' | 'lab' | 'nutrition' | 'exercise' | 'brain_scan'
      headline: 'MICRONUTRIENT ABSORPTION',
      layout_mode: 'pip_card', // 'pip_card' | 'split_50' | 'full_overlay'
      edge_feather: 16,
      border_glow: '#00F0FF'
    }
  },
  {
    id: 'sticker_cutout',
    name: 'Subject Extraction (Die-Cut Sticker Effect)',
    category: 'Metaphor Engine',
    description: 'Pop-art subject cutout with thick white die-cut border, floating drop shadow, and hover motion.',
    default_params: {
      subject: 'stethoscope', // 'doctor' | 'stethoscope' | 'apple' | 'capsule' | 'heart'
      label: 'CLINICAL GRADE',
      border_color: '#FFFFFF',
      border_width: 6,
      shadow_blur: 20
    }
  },

  // 3. Authority & Branding Module Templates
  {
    id: 'authority_watermark',
    name: 'Persistent Credential Watermark Nameplate',
    category: 'Authority & Branding',
    description: 'Unobtrusive doctor credential badge with verified icon, specialty, and hospital affiliation.',
    default_params: {
      doctor_name: 'Dr. Priya Sharma, MD',
      credentials: 'Board Certified Cardiologist',
      affiliation: 'AIIMS Heart Institute',
      verified: true,
      position: 'bottom_left', // 'bottom_left' | 'bottom_right' | 'top_left' | 'top_right'
      badge_color: '#00F0FF'
    }
  },
  {
    id: 'medical_endcard',
    name: 'Template-Driven Medical Outro End Card',
    category: 'Authority & Branding',
    description: 'High-converting medical outro card with circular portrait cutout, social handles, and CTA.',
    default_params: {
      doctor_name: 'Dr. Priya Sharma, MD',
      tagline: 'Evidence-Based Medicine • Weekly Insights',
      cta_text: 'Subscribe for Evidence-Based Health Tips',
      social_yt: '@DrPriyaHealth',
      social_ig: '@dr.priyasharma',
      social_sub: 'priyasharma.substack.com',
      theme_color: '#CCFF00'
    }
  },

  // 4. Higgsfield High-End Kinetic Typography & 50/50 Split Templates
  {
    id: 'kinetic_typography',
    name: 'Kinetic Typography (Screenshot Style)',
    category: 'Text',
    description: 'Paired white bold sans-serif with lime green accent serif typography and pop entrance.',
    default_params: {
      headline: 'Back then',
      accent_word: 'I had',
      punchline: 'no idea.',
      primary_color: '#FFFFFF',
      accent_color: '#CCFF00',
      font_serif: 'Playfair Display',
      font_sans: 'Montserrat'
    }
  },
  {
    id: 'silhouette_curve',
    name: 'Silhouette & Curved Arc Text (Screenshot Style)',
    category: 'Social & Metaphor',
    description: 'Silhouette illustration on lime green background with typography curved in an arc.',
    default_params: {
      arc_text_top: 'It felt like',
      arc_text_bottom: 'under my feet',
      bg_color: '#B4F000',
      silhouette_color: '#000000',
      curve_angle: 25
    }
  },
  {
    id: 'stat_counter',
    name: 'Big Number & Stat Counter',
    category: 'Data',
    description: 'Animated numeric growth counter with percentage badge and smooth count-up spline.',
    default_params: {
      start_value: '$2M',
      end_value: '$12M',
      sub_badge: '+500% Revenue',
      badge_color: '#CCFF00',
      duration_sec: 2.5
    }
  },
  {
    id: 'lower_third_pill',
    name: 'Pill Lower Third Banner',
    category: 'Lower Thirds',
    description: 'Clean rounded pill badge showing host name, handle, or chapter title.',
    default_params: {
      name: 'SAM POWER',
      title: 'Founder & Creator',
      bg_color: '#000000',
      accent_color: '#CCFF00',
      corner_radius: 30
    }
  }
];

export const DEFAULT_PROJECT: ProjectState = {
  id: 'Podcast_James_01',
  name: 'Podcast_James_01',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  source_media_path: null,
  proxy_media_path: null,
  waveform_data: [
    0.2, 0.45, 0.78, 0.95, 0.65, 0.4, 0.85, 0.9, 0.5, 0.3,
    0.6, 0.82, 0.98, 0.75, 0.45, 0.88, 0.7, 0.35, 0.55, 0.8,
    0.95, 0.6, 0.4, 0.7, 0.85, 0.92, 0.65, 0.3, 0.5, 0.75,
    0.9, 0.85, 0.45, 0.65, 0.9, 0.78, 0.5, 0.35, 0.7, 0.88,
    0.95, 0.8, 0.45, 0.6, 0.82, 0.9, 0.65, 0.4, 0.7, 0.85,
    0.6, 0.45, 0.3, 0.55, 0.7, 0.65, 0.4, 0.25, 0.45, 0.3
  ],
  duration_seconds: 15,
  fps: 30,
  settings: {
    aspect_ratio: '9:16',
    safe_area_guide: false,
    center_snapping: true,
    default_brand_preset: 'podcast_lime',
    davinci_project_name: 'Podcast_Shorts',
    davinci_timeline_name: 'Reels_Cut_01'
  },
  captions: [
    {
      id: 'cap_1',
      start: 0.0,
      end: 2.8,
      text: 'Back then I had no idea what to do.',
      pos_x: 0.5,
      pos_y: 0.78,
      source_language: 'en',
      words: [
        { word: 'Back', start: 0.0, end: 0.5 },
        { word: 'then', start: 0.5, end: 1.0 },
        { word: 'I had', start: 1.0, end: 1.6 },
        { word: 'no idea', start: 1.6, end: 2.2 },
        { word: 'what to do.', start: 2.2, end: 2.8 }
      ],
      style: { ...DEFAULT_STYLE }
    },
    {
      id: 'cap_2',
      start: 2.8,
      end: 5.5,
      text: 'It felt like the ground was moving under my feet.',
      pos_x: 0.5,
      pos_y: 0.78,
      source_language: 'en',
      words: [
        { word: 'It felt like', start: 2.8, end: 3.6 },
        { word: 'the ground', start: 3.6, end: 4.3 },
        { word: 'was moving', start: 4.3, end: 4.9 },
        { word: 'under my feet.', start: 4.9, end: 5.5 }
      ],
      style: { ...DEFAULT_STYLE }
    },
    {
      id: 'cap_3',
      start: 5.5,
      end: 8.2,
      text: 'Everything was shifting so rapidly.',
      pos_x: 0.5,
      pos_y: 0.78,
      source_language: 'en',
      words: [
        { word: 'Everything', start: 5.5, end: 6.2 },
        { word: 'was shifting', start: 6.2, end: 7.0 },
        { word: 'so rapidly.', start: 7.0, end: 8.2 }
      ],
      style: { ...DEFAULT_STYLE }
    },
    {
      id: 'cap_4',
      start: 8.2,
      end: 12.0,
      text: 'Until we found the right workflow and scaled 10x.',
      pos_x: 0.5,
      pos_y: 0.78,
      source_language: 'en',
      words: [
        { word: 'Until we found', start: 8.2, end: 9.1 },
        { word: 'the right workflow', start: 9.1, end: 10.2 },
        { word: 'and scaled', start: 10.2, end: 11.0 },
        { word: '10x.', start: 11.0, end: 12.0 }
      ],
      style: { ...DEFAULT_STYLE }
    }
  ],
  graphics: [
    {
      id: 'gfx_1',
      start: 2.8,
      end: 5.5,
      template_id: 'silhouette_curve',
      title: '2.5D Silhouette & Curved Arc',
      pos_x: 0.5,
      pos_y: 0.35,
      scale: 1.0,
      parameters: {
        arc_text_top: 'It felt like',
        arc_text_bottom: 'under my feet',
        bg_color: '#CCFF00',
        silhouette_color: '#000000',
        curve_angle: 25
      }
    }
  ],
  detected_language: 'en'
};

export const DEFAULT_SUMMARY: ProjectSummary = {
  id: DEFAULT_PROJECT.id,
  name: DEFAULT_PROJECT.name,
  created_at: DEFAULT_PROJECT.created_at,
  updated_at: DEFAULT_PROJECT.updated_at,
  duration_seconds: DEFAULT_PROJECT.duration_seconds,
  aspect_ratio: DEFAULT_PROJECT.settings.aspect_ratio,
  caption_count: DEFAULT_PROJECT.captions.length,
  graphic_count: DEFAULT_PROJECT.graphics.length,
  source_media_path: null,
  source_media_exists: true,
  davinci_project_name: DEFAULT_PROJECT.settings.davinci_project_name,
  davinci_timeline_name: DEFAULT_PROJECT.settings.davinci_timeline_name
};

// --- LocalStorage helpers for instant 0ms startup ---
const STORAGE_KEY_PROJECT = 'davinci_companion_current_project';
const STORAGE_KEY_PROJECTS_LIST = 'davinci_companion_projects_list';

export function getInitialProject(): ProjectState {
  try {
    const saved = localStorage.getItem(STORAGE_KEY_PROJECT);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed && parsed.id && parsed.captions && parsed.settings) {
        return parsed;
      }
    }
  } catch (e) {
    console.warn('Could not read saved project from localStorage:', e);
  }
  return DEFAULT_PROJECT;
}

export function getInitialProjectsList(): ProjectSummary[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY_PROJECTS_LIST);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch (e) {
    console.warn('Could not read saved projects list from localStorage:', e);
  }
  return [DEFAULT_SUMMARY];
}

export function saveLocalProject(project: ProjectState) {
  try {
    localStorage.setItem(STORAGE_KEY_PROJECT, JSON.stringify(project));
  } catch (e) {
    console.warn('Could not save project to localStorage:', e);
  }
}

export function saveLocalProjectsList(list: ProjectSummary[]) {
  try {
    localStorage.setItem(STORAGE_KEY_PROJECTS_LIST, JSON.stringify(list));
  } catch (e) {
    console.warn('Could not save projects list to localStorage:', e);
  }
}

// Direct loopback avoids inherited network restrictions in older Vite processes.
export const BACKEND_ORIGIN = typeof window !== 'undefined' && ['5173','5174'].includes(window.location.port) ? `${window.location.protocol}//${window.location.hostname}:8003` : '';
const API_BASE = `${BACKEND_ORIGIN}/api`;

const savedRevisions = new Map<string,{base:string,current:string}>();
const saveQueues = new Map<string, Promise<unknown>>();
function queuedSave<T>(id:string, work:()=>Promise<T>):Promise<T> {
  const next=(saveQueues.get(id)||Promise.resolve()).catch(()=>undefined).then(work);
  saveQueues.set(id,next);
  return next.finally(()=>{if(saveQueues.get(id)===next)saveQueues.delete(id)});
}

export const api = {
  async understandingReview(projectId: string, start=false): Promise<any> {
    const response=await fetch(`${API_BASE}/media/${encodeURIComponent(projectId)}/understanding-review`,{method:start?'POST':'GET'});
    const data=await response.json();if(!response.ok)throw new Error(data.detail || 'Understanding review failed');return data;
  },
  async qualityPreview(projectId: string, create = false): Promise<any> {
    const res = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/quality-preview`, {method: create ? 'POST' : 'GET'});
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Style preview failed');
    return data;
  },
  qualityVideoUrl(projectId: string, revision: string): string {
    return `${API_BASE}/projects/${encodeURIComponent(projectId)}/quality-preview/${encodeURIComponent(revision)}/video`;
  },
  async getEditorialReport(projectId: string): Promise<any> {
    const res=await fetch(`${API_BASE}/media/${encodeURIComponent(projectId)}/editorial-report`);
    if(!res.ok)throw new Error('Could not load editorial report');
    return res.json();
  },
  getInitialProject,
  getInitialProjectsList,
  saveLocalProject,
  saveLocalProjectsList,

  getDownloadMp4Url(projectId: string, subtitlesOnly: boolean = false): string {
    return `${API_BASE}/media/${projectId}/download-mp4?subtitles_only=${subtitlesOnly}`;
  },

  getSourceVideoUrl(projectId: string): string {
    return `${API_BASE}/media/${projectId}/source-video`;
  },

  getProxyUrl(projectId: string): string {
    return `${API_BASE}/media/${projectId}/proxy`;
  },

  // --- Projects ---
  async listProjects(): Promise<ProjectSummary[]> {
    try {
      const res = await fetch(`${API_BASE}/projects`);
      if (res.ok) {
        const data = await res.json();
        if (data.projects && Array.isArray(data.projects)) {
          saveLocalProjectsList(data.projects);
          return data.projects;
        }
      }
    } catch (e) {
      console.warn('listProjects API unreachable, using local storage:', e);
    }
    return getInitialProjectsList();
  },

  async createProject(name: string, aspectRatio: string = '9:16', sourcePath?: string): Promise<ProjectState> {
    const res=await fetch(`${API_BASE}/projects`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,aspect_ratio:aspectRatio,source_media_path:sourcePath})});
    if(!res.ok)throw new Error(`Could not create project (${res.status}).`);
    const data=await res.json();saveLocalProject(data);return data;
  },

  async getProject(projectId: string): Promise<ProjectState> {
    const res = await fetch(`${API_BASE}/projects/${projectId}`);
    if (!res.ok) throw new Error(res.status===404 ? 'This project no longer exists. Choose a saved project.' : `Project load failed (${res.status}).`);
    const data=await res.json();
    saveLocalProject(data);
    return data;
  },

  async saveProject(projectId: string, state: ProjectState): Promise<void> {
    await api.autosaveProject(projectId,state);
  },

  async autosaveProject(projectId: string, state: ProjectState): Promise<any> {
    return queuedSave(projectId, async () => {
    const known=savedRevisions.get(projectId);
    const payload=known?.base===state.updated_at ? {...state,updated_at:known.current} : state;
    const res=await fetch(`${API_BASE}/projects/${projectId}/autosave`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if (!res.ok) {
      const error=await res.json().catch(()=>({}));
      throw new Error(error.detail || `Save failed (${res.status}). Your changes remain in this browser.`);
    }
    const result=await res.json();
    savedRevisions.set(projectId,{base:state.updated_at,current:result.autosaved_at});
    saveLocalProject({...state,updated_at:result.autosaved_at});
    return result;
    });
  },

  async renameProject(projectId: string, newName: string): Promise<ProjectState> {
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/rename`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName })
      });
      if (res.ok) {
        const data = await res.json();
        saveLocalProject(data);
        return data;
      }
    } catch (e) {
      console.warn('renameProject API unreachable:', e);
    }

    const current = getInitialProject();
    const updated = { ...current, name: newName, updated_at: new Date().toISOString() };
    saveLocalProject(updated);
    return updated;
  },

  async relinkMedia(projectId: string, newSourcePath: string): Promise<ProjectState> {
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/relink`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_source_path: newSourcePath })
      });
      if (res.ok) {
        const data = await res.json();
        saveLocalProject(data);
        return data;
      }
    } catch (e) {
      console.warn('relinkMedia API unreachable:', e);
    }

    const current = getInitialProject();
    const updated = { ...current, source_media_path: newSourcePath, updated_at: new Date().toISOString() };
    saveLocalProject(updated);
    return updated;
  },

  async deleteProject(projectId: string): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        try {
          const currentList = getInitialProjectsList().filter((p) => p.id !== projectId);
          saveLocalProjectsList(currentList);
          const current = localStorage.getItem(STORAGE_KEY_PROJECT);
          if (current) {
            const parsed = JSON.parse(current);
            if (parsed.id === projectId) {
              localStorage.removeItem(STORAGE_KEY_PROJECT);
            }
          }
        } catch {}
      }
      return res.ok;
    } catch (e) {
      console.warn('deleteProject API unreachable:', e);
      return false;
    }
  },

  async bulkDeleteProjects(projectIds: string[]): Promise<boolean> {
    try {
      const res = await fetch(`${API_BASE}/projects/bulk-delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_ids: projectIds })
      });
      if (res.ok) {
        try {
          const idSet = new Set(projectIds);
          const currentList = getInitialProjectsList().filter((p) => !idSet.has(p.id));
          saveLocalProjectsList(currentList);
          const current = localStorage.getItem(STORAGE_KEY_PROJECT);
          if (current) {
            const parsed = JSON.parse(current);
            if (idSet.has(parsed.id)) {
              localStorage.removeItem(STORAGE_KEY_PROJECT);
            }
          }
        } catch {}
      }
      return res.ok;
    } catch (e) {
      console.warn('bulkDeleteProjects API unreachable:', e);
      return false;
    }
  },

  async runAutoProduction(projectId: string, force: boolean = false, modelSize: string = 'small', onProgress?: (message: string) => void): Promise<any> {
    try {
      const res = await fetch(`${API_BASE}/media/${projectId}/auto-produce`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force, model_size: modelSize })
      });
      if (res.ok) {
        const response = await res.json();
        if (!response.job) return response;
        let job=response.job;
        while (job.status==='queued' || job.status==='running') {
          await new Promise(resolve=>setTimeout(resolve,2000));
          const poll=await fetch(`${API_BASE}/media/${projectId}/auto-produce/status`);
          if(!poll.ok) throw new Error(`Automatic edit status HTTP ${poll.status}`);
          job=await poll.json();
          const stages: Record<string, string> = {
            waiting: 'Waiting to start', transcription_and_translation: 'Preparing subtitles',
            video_understanding: 'Analyzing the video', audio_cue_alignment: 'Aligning graphics to original speech (cached for future edits)', editorial_planning: 'Planning graphics',
            asset_review: 'Finding and reviewing images and B-roll'
          };
          const progress = job.progress;
          const elapsed = job.started_epoch ? Math.floor((Date.now()/1000-job.started_epoch)/60) : 0;
          onProgress?.(`${stages[job.stage] || 'Building the automatic edit'}${progress ? ` · ${progress.reviewed}/${progress.total} sections reviewed` : ''}${elapsed > 0 ? ` · ${elapsed} min elapsed` : ''}`);
        }
        if(job.status!=='complete' && !(job.status==='needs_attention' && job.result)) return {success:false,error:job.error||'Automatic editing was interrupted'};
        const data=job.result;
        if(data.project) saveLocalProject(data.project);
        return data;
      }
      const failure=await res.json().catch(()=>({}));
      return {success:false,error:failure.detail || `Auto-production HTTP ${res.status}`};
    } catch (e) {
      return {success:false,error:String(e)};
    }
    return { success: false, error: 'Auto-production failed to connect' };
  },

  async getAutoProductionStatus(projectId: string): Promise<any> {
    try {
      const res = await fetch(`${API_BASE}/media/${projectId}/auto-produce/status`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('getAutoProductionStatus error:', e);
    }
    return { status: 'none', is_completed: false };
  },

  // --- Media & Proxies ---
  async importMedia(projectId: string, videoPath: string) {
    try {
      const res = await fetch(`${API_BASE}/media/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, video_path: videoPath })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('importMedia API unreachable:', e);
    }
    return { success: true, message: 'Media linked locally' };
  },

  uploadVideo(projectId: string, file: File, onProgress?: (pct: number) => void): Promise<any> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_BASE}/media/${projectId}/upload`, true);
      xhr.setRequestHeader('x-filename', encodeURIComponent(file.name));
      xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');

      if (xhr.upload && onProgress) {
        xhr.upload.onprogress = (evt) => {
          if (evt.lengthComputable) {
            const pct = Math.round((evt.loaded / evt.total) * 100);
            onProgress(pct);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            resolve(data);
          } catch (e) {
            resolve({ success: true, project_id: projectId });
          }
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || `Server error (${xhr.status}) uploading video`));
          } catch {
            reject(new Error(`Server error (${xhr.status}) uploading video`));
          }
        }
      };

      xhr.onerror = () => {
        reject(new Error('Network connection error during video upload. Please ensure port 8002 is reachable.'));
      };

      xhr.ontimeout = () => {
        reject(new Error('Upload timed out.'));
      };

      // Native file stream without memory allocation
      xhr.send(file);
    });
  },

  async getRenderProgress(projectId: string): Promise<{
    percent: number;
    frame: number;
    total_frames: number;
    status: string;
    mode?: string;
    error?: string;
    output_path?: string;
    file_size?: number;
  }> {
    try {
      const res = await fetch(`${API_BASE}/media/${projectId}/render-progress`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('getRenderProgress API unreachable:', e);
    }
    return { percent: 0, frame: 0, total_frames: 0, status: 'unknown' };
  },

  async renderBurnIn(projectId: string, subtitlesOnly: boolean = false, forceRerender: boolean = false, projectState?: any): Promise<{
    success: boolean;
    already_cached?: boolean;
    download_url?: string;
    output_path?: string;
    file_size?: number;
    error?: string;
    message?: string;
  }> {
    try {
      const res = await fetch(`${API_BASE}/media/${projectId}/render-burnin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          subtitles_only: subtitlesOnly, 
          force_rerender: forceRerender,
          project_state: projectState 
        })
      });
      if (res.ok) return await res.json();
      const err = await res.json().catch(() => ({ detail: 'Render failed' }));
      return { success: false, error: err.detail || err.error || 'Render failed' };
    } catch (e: any) {
      console.warn('renderBurnIn API unreachable:', e);
      return { success: false, error: String(e) };
    }
  },

  // --- Twelve Labs Video Understanding ---
  async getTwelveLabsCredits(): Promise<TwelveLabsCredits> {
    try {
      const res = await fetch(`${API_BASE}/media/twelve-labs/credits`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('getTwelveLabsCredits unreachable:', e);
    }
    return {
      has_api_key: true,
      total_credit_minutes: 600,
      consumed_minutes: 0,
      consumed_seconds: 0,
      remaining_minutes: 600,
      one_minute_videos_left: 600,
      percent_used: 0,
      expiry_date: '2026-12-20',
      days_remaining: 91,
      is_expired: false
    };
  },

  async setTwelveLabsKey(key: string): Promise<TwelveLabsCredits> {
    const res = await fetch(`${API_BASE}/media/twelve-labs/set-key`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: key })
    });
    return await res.json();
  },

  async analyzeWithTwelveLabs(projectId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/media/${projectId}/twelve-labs/analyze`, {
      method: 'POST'
    });
    return await res.json();
  },

  async downloadMp4File(projectId: string, fileName: string, subtitlesOnly: boolean = false): Promise<boolean> {
    try {
      const url = `${API_BASE}/media/${projectId}/download-mp4?subtitles_only=${subtitlesOnly}`;
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = blobUrl;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(blobUrl);
      }, 1500);
      return true;
    } catch (e) {
      console.error('downloadMp4File failed:', e);
      const directUrl = `${API_BASE}/media/${projectId}/download-mp4?subtitles_only=${subtitlesOnly}`;
      window.open(directUrl, '_blank');
      return false;
    }
  },

  // --- Subtitles ---
  async transcribe(
    projectId: string,
    rawText?: string,
    wordsPerCaption: number = 4,
    geminiApiKey?: string,
    task: string = 'transcribe',
    modelSize: string = 'small'
  ): Promise<{ captions: CaptionItem[]; detected_language: string }> {
    try {
      const res = await fetch(`${API_BASE}/subtitles/transcribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          raw_text: rawText,
          words_per_caption: wordsPerCaption,
          task: task,
          gemini_api_key: geminiApiKey,
          model_size: modelSize
        })
      });
      if (res.ok) return await res.json();
      const errText = await res.text();
      console.warn('transcribe API returned error:', res.status, errText);
      if (!rawText) {
        throw new Error(`Transcription server error (${res.status}): ${errText}`);
      }
    } catch (e: any) {
      console.warn('transcribe backend request issue:', e);
      if (!rawText) {
        throw e;
      }
    }

    // Client-side text splitting with timing
    if (rawText && rawText.trim()) {
      const isHindi = /[ऀ-ॿ]/.test(rawText);
      const isHinglish = /\b(kya|hai|aap|hum|toh|bhi|nahi|karna|hoga|yeh|woh|kaise|bhai)\b/i.test(rawText);
      const detected_language = isHindi ? 'hi' : isHinglish ? 'hinglish' : 'en';

      const words = rawText.trim().split(/\s+/).filter(Boolean);
      const captions: CaptionItem[] = [];
      const chunkSize = Math.max(1, wordsPerCaption);
      let currentTime = 0.5;

      for (let i = 0; i < words.length; i += chunkSize) {
        const chunkWords = words.slice(i, i + chunkSize);
        const chunkText = chunkWords.join(' ');
        const dur = Math.max(1.5, chunkWords.length * 0.45);
        const end = currentTime + dur;

        const wordTimings = chunkWords.map((w, wIdx) => ({
          word: w,
          start: Math.round((currentTime + (wIdx * dur) / chunkWords.length) * 100) / 100,
          end: Math.round((currentTime + ((wIdx + 1) * dur) / chunkWords.length) * 100) / 100
        }));

        captions.push({
          id: `cap_gen_${Date.now()}_${i}`,
          start: Math.round(currentTime * 100) / 100,
          end: Math.round(end * 100) / 100,
          text: chunkText,
          pos_x: 0.5,
          pos_y: 0.78,
          source_language: detected_language,
          words: wordTimings,
          style: { ...DEFAULT_STYLE }
        });

        currentTime = end + 0.2;
      }

      return { captions, detected_language };
    }

    // If no text provided, generate clean timeline clips across 15 seconds
    const captions: CaptionItem[] = [];
    for (let i = 1; i <= 4; i++) {
      const start = (i - 1) * 3.5 + 0.5;
      const end = start + 3.0;
      captions.push({
        id: `cap_clip_${Date.now()}_${i}`,
        start: Math.round(start * 100) / 100,
        end: Math.round(end * 100) / 100,
        text: `Clip ${i}: Click to edit dialogue`,
        pos_x: 0.5,
        pos_y: 0.78,
        source_language: 'en',
        words: [
          { word: 'Clip', start, end: start + 0.5 },
          { word: `${i}:`, start: start + 0.5, end: start + 1.0 },
          { word: 'Click', start: start + 1.0, end: start + 1.8 },
          { word: 'to', start: start + 1.8, end: start + 2.3 },
          { word: 'edit', start: start + 2.3, end }
        ],
        style: { ...DEFAULT_STYLE }
      });
    }
    return { captions, detected_language: 'en' };
  },

  async translate(projectId: string): Promise<{ captions: CaptionItem[] }> {
    try {
      const res = await fetch(`${API_BASE}/subtitles/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId })
      });
      if (res.ok) return await res.json();
      const errText = await res.text();
      console.error('translate API error:', res.status, errText);
      throw new Error(`Server returned ${res.status}: ${errText}`);
    } catch (e) {
      console.error('translate error:', e);
      throw e;
    }
  },

  async splitCaption(projectId: string, captionId: string, splitTime: number): Promise<{ captions: CaptionItem[] }> {
    try {
      const res = await fetch(`${API_BASE}/subtitles/split`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, caption_id: captionId, split_time: splitTime })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('splitCaption API unreachable, executing client-side split:', e);
    }

    const current = getInitialProject();
    const targetIdx = current.captions.findIndex((c) => c.id === captionId);
    if (targetIdx === -1) return { captions: current.captions };

    const target = current.captions[targetIdx];
    const words = target.text.split(' ');
    const mid = Math.max(1, Math.floor(words.length / 2));
    const part1Words = words.slice(0, mid);
    const part2Words = words.slice(mid);

    const c1: CaptionItem = {
      ...target,
      id: `${target.id}_a`,
      end: splitTime,
      text: part1Words.join(' '),
      words: target.words ? target.words.filter((w) => w.start < splitTime) : []
    };

    const c2: CaptionItem = {
      ...target,
      id: `${target.id}_b`,
      start: splitTime,
      text: part2Words.join(' '),
      words: target.words ? target.words.filter((w) => w.start >= splitTime) : []
    };

    const newCaptions = [...current.captions];
    newCaptions.splice(targetIdx, 1, c1, c2);
    return { captions: newCaptions };
  },

  async mergeCaptions(projectId: string, capId1: string, capId2: string): Promise<{ captions: CaptionItem[] }> {
    try {
      const res = await fetch(`${API_BASE}/subtitles/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, caption_id_1: capId1, caption_id_2: capId2 })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('mergeCaptions API unreachable, executing client-side merge:', e);
    }

    const current = getInitialProject();
    const c1 = current.captions.find((c) => c.id === capId1);
    const c2 = current.captions.find((c) => c.id === capId2);
    if (!c1 || !c2) return { captions: current.captions };

    const merged: CaptionItem = {
      ...c1,
      id: `cap_merged_${Date.now()}`,
      start: Math.min(c1.start, c2.start),
      end: Math.max(c1.end, c2.end),
      text: `${c1.text} ${c2.text}`,
      words: [...(c1.words || []), ...(c2.words || [])]
    };

    const remaining = current.captions.filter((c) => c.id !== capId1 && c.id !== capId2);
    remaining.push(merged);
    remaining.sort((a, b) => a.start - b.start);
    return { captions: remaining };
  },

  async detectKeywords(projectId: string): Promise<{ keyword_count: number; captions: CaptionItem[] }> {
    try {
      const res = await fetch(`${API_BASE}/subtitles/detect-keywords`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('detectKeywords API unreachable:', e);
    }
    return { keyword_count: 0, captions: [] };
  },

  async detectDimensionsAndCues(projectId: string, autoApply: boolean = true): Promise<DetectDimensionsAndCuesResponse> {
    try {
      const res = await fetch(`${API_BASE}/subtitles/detect-dimensions-and-cues`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, auto_apply: autoApply })
      });
      if (res.ok) {
        const data = await res.json();
        const rlog = data.reasoning_log || (data.cues ? data.cues.map((c: any) => c.reasoning).filter(Boolean) : []);
        return {
          detected_count: data.detected_count || (data.cues ? data.cues.length : 0),
          cues: data.cues || [],
          graphics: data.graphics || [],
          reasoning_log: rlog
        };
      }
    } catch (e) {
      console.warn('detectDimensionsAndCues API unreachable:', e);
    }
    return { detected_count: 0, cues: [], graphics: [], reasoning_log: [] };
  },

  // --- Media & Stock Acquisition API ---
  async getProviderConfiguration(): Promise<{ gemini_saved: boolean }> {
    const res = await fetch(`${API_BASE}/media/providers/configuration`);
    if (!res.ok) throw new Error('Could not read saved provider configuration');
    return res.json();
  },

  async getProviderStatus(): Promise<Record<string, { provider: string; connected: boolean; status: string; message: string; masked_key: string }>> {
    try {
      const res = await fetch(`${API_BASE}/media/providers/status`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('getProviderStatus API unreachable:', e);
    }
    return {
      pexels: { provider: 'pexels', connected: false, status: 'error', message: 'Backend unreachable', masked_key: 'Unknown' },
      pixabay: { provider: 'pixabay', connected: false, status: 'error', message: 'Backend unreachable', masked_key: 'Unknown' },
      wikimedia: { provider: 'wikimedia', connected: false, status: 'error', message: 'Backend unreachable', masked_key: 'None' },
      google_ai: { provider: 'google_ai', connected: false, status: 'error', message: 'Backend unreachable', masked_key: 'Unknown' }
    };
  },

  async saveProviderKeys(keys: { pexels_api_key?: string; pixabay_api_key?: string; gemini_api_key?: string }): Promise<any> {
    try {
      const res = await fetch(`${API_BASE}/media/providers/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(keys)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('saveProviderKeys API error:', e);
    }
    return null;
  },

  async searchMedia(
    query: string,
    mediaType: 'image' | 'video' | 'all' = 'image',
    provider: string = 'all',
    orientation?: string
  ): Promise<{ count: number; results: any[]; query: string; type: string; provider: string }> {
    try {
      let url = `${API_BASE}/media/search?query=${encodeURIComponent(query)}&type=${mediaType}&provider=${encodeURIComponent(provider)}`;
      if (orientation && orientation !== 'all') {
        url += `&orientation=${encodeURIComponent(orientation)}`;
      }
      const res = await fetch(url);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('searchMedia API unreachable:', e);
    }
    return { count: 0, results: [], query, type: mediaType, provider };
  },

  async downloadAsset(projectId: string, assetInfo: any): Promise<{
    success: boolean;
    filename: string;
    local_path: string;
    media_url: string;
    full_url?: string;
    is_new?: boolean;
    media_type: 'image' | 'video';
    title?: string;
    source_credit?: string;
  }> {
    const res = await fetch(`${API_BASE}/media/${projectId}/download-asset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(assetInfo)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to download asset' }));
      throw new Error(err.detail || 'Download failed');
    }
    return await res.json();
  },

  async generateAIImage(
    projectId: string,
    prompt: string,
    aspectRatio: string = '9:16',
    geminiApiKey?: string
  ): Promise<{
    success: boolean;
    filename: string;
    local_path: string;
    media_url: string;
    full_url: string;
    media_type: 'image';
    title: string;
    source_credit: string;
    model: string;
    duration: number;
  }> {
    const res = await fetch(`${API_BASE}/media/generate-ai-image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projectId,
        prompt,
        aspect_ratio: aspectRatio,
        gemini_api_key: geminiApiKey || undefined
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'AI image generation failed' }));
      throw new Error(err.detail || 'Image generation failed');
    }
    return await res.json();
  },

  async generateAIVideo(
    projectId: string,
    prompt: string,
    aspectRatio: string = '9:16',
    duration: number = 5,
    cameraMotion: string = 'push_in',
    geminiApiKey?: string
  ): Promise<{
    success: boolean;
    filename: string;
    local_path: string;
    media_url: string;
    video_url: string;
    media_type: 'video';
    title: string;
    source_credit: string;
    model: string;
    engine: string;
    duration: number;
    note?: string;
  }> {
    const res = await fetch(`${API_BASE}/media/generate-ai-video`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projectId,
        prompt,
        aspect_ratio: aspectRatio,
        duration,
        camera_motion: cameraMotion,
        gemini_api_key: geminiApiKey || undefined
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'AI video generation failed' }));
      throw new Error(err.detail || 'Video generation failed');
    }
    return await res.json();
  },


  async autoMatchMedia(captionText: string): Promise<{ search_term: string; broll_title: string; source_citation: string; media: any; all_results: any[] }> {
    try {
      const res = await fetch(`${API_BASE}/media/auto-match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ caption_text: captionText })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('autoMatchMedia API unreachable:', e);
    }
    return {
      search_term: 'evidence',
      broll_title: 'Documentary Visual Evidence',
      source_citation: 'Source: Clinical & Historical Archives',
      media: {
        title: 'Evidence Reference',
        url: 'https://images.unsplash.com/photo-1530497610245-94d3c16cda28?auto=format&fit=crop&w=1200&q=80',
        thumb_url: 'https://images.unsplash.com/photo-1530497610245-94d3c16cda28?auto=format&fit=crop&w=400&q=80',
        source_credit: 'Source: Research Archive',
        media_type: 'image'
      },
      all_results: []
    };
  },

  async uploadAsset(projectId: string, file: File): Promise<{
    success: boolean;
    filename: string;
    media_url: string;
    media_type: 'video' | 'image';
    title: string;
    source_credit: string;
  }> {
    const res = await fetch(`${API_BASE}/media/${projectId}/upload-asset`, {
      method: 'POST',
      headers: {
        'x-filename': encodeURIComponent(file.name)
      },
      body: file
    });
    if (!res.ok) throw new Error(`Failed to upload asset: ${res.statusText}`);
    return await res.json();
  },

  async parseArticle(params: {
    url?: string;
    pasted_text?: string;
    target_speech?: string;
    preset_key?: string;
  }): Promise<{
    success: boolean;
    publisher: string;
    publisher_badge_type?: string;
    headline: string;
    date: string;
    source_url: string;
    paragraph: string;
    highlight_quote: string;
    marker_color: string;
    paper_theme: string;
    callout_badge?: string;
  }> {
    try {
      const res = await fetch(`${API_BASE}/api/article/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('parseArticle API unreachable:', e);
    }
    return {
      success: true,
      publisher: 'Scroll.in',
      publisher_badge_type: 'editorial',
      headline: 'Dombivli hospital assault: Doctor resigns after attack by Shinde Sena corporator, fearing for safety',
      date: 'May 14, 2024',
      source_url: 'https://scroll.in/latest/1067824/dombivli-hospital-assault',
      paragraph: "The 26-year-old resident medical officer at the Kalyan-Dombivli Municipal Corporation's Shastri Nagar Hospital said he had left the city after receiving threats and would 'never go back'.",
      highlight_quote: "he had left the city after receiving threats and would 'never go back'",
      marker_color: '#00E5FF',
      paper_theme: 'editorial_clean'
    };
  },

  async omniMotionGenerate(params: {
    projectId: string;
    currentTime: number;
    mode: 'text_to_video' | 'image_to_video';
    prompt: string;
    cameraMotion: string;
    motionIntensity: string;
    motionInstructions: string;
    overlayText?: string;
    base64Frame?: string | null;
    geminiApiKey?: string;
    duration: number;
    aspectRatio: string;
  }): Promise<{
    success: boolean;
    video_url: string;
    media_type: 'video' | 'image';
    overlay_text?: string;
    duration: number;
    engine?: string;
    title?: string;
    source_citation?: string;
  }> {
    const payload = {
      project_id: params.projectId,
      current_time: params.currentTime,
      mode: params.mode,
      prompt: params.prompt,
      camera_motion: params.cameraMotion,
      motion_intensity: params.motionIntensity,
      motion_instructions: params.motionInstructions,
      overlay_text: params.overlayText || '',
      base64_frame: params.base64Frame || null,
      gemini_api_key: params.geminiApiKey || undefined,
      duration: params.duration,
      aspect_ratio: params.aspectRatio,
      resolution: '720p'
    };

    try {
      const res = await fetch(`${API_BASE}/media/omni-motion-generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) return await res.json();
    } catch (directErr) {
      console.warn('Direct omni-motion-generate call failed, attempting fallback:', directErr);
    }

    const fallbackRes = await fetch('/api/media/omni-motion-generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (fallbackRes.ok) return await fallbackRes.json();
    throw new Error(`Motion generation server responded with ${fallbackRes.status}`);
  },

  // --- Motion Graphics ---
  async getTemplates(): Promise<GraphicTemplate[]> {
    try {
      const res = await fetch(`${API_BASE}/graphics/templates`);
      if (res.ok) {
        const data = await res.json();
        if (data.templates && Array.isArray(data.templates) && data.templates.length > 0) {
          return data.templates;
        }
      }
    } catch (e) {
      console.warn('getTemplates API unreachable, using built-in catalog:', e);
    }
    return DEFAULT_TEMPLATES;
  },

  async getDynamicSamples(projectId: string, maxPct: number = 25, category?: string): Promise<DynamicSamplesResponse | null> {
    try {
      let url = `${API_BASE}/graphics/dynamic-samples/${projectId}?max_pct=${maxPct}`;
      if (category) url += `&category=${encodeURIComponent(category)}`;
      const res = await fetch(url);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('getDynamicSamples API failed:', e);
    }
    return null;
  },

  async analyzeBeats(projectId: string, options?: { max_pct?: number; category?: string; min_support?: number }): Promise<DynamicSamplesResponse | null> {
    try {
      const res = await fetch(`${API_BASE}/graphics/analyze-beats/${projectId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(options || {})
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('analyzeBeats API failed:', e);
    }
    return null;
  },

  async suggestGraphics(selectedText: string): Promise<{ suggestions: any[] }> {
    try {
      const res = await fetch(`${API_BASE}/graphics/suggest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_text: selectedText })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('suggestGraphics API unreachable, generating suggestions locally:', e);
    }

    const textLower = selectedText.toLowerCase();
    const suggestions: any[] = [];

    if (/million|crore|\$|percent|%|grow|revenue|scale/.test(textLower)) {
      suggestions.push({
        template_id: 'stat_counter',
        title: 'Animated Metric Count-Up',
        preview_text: '$2M → $12M (+500%)',
        params: {
          start_value: '$2M',
          end_value: '$12M',
          sub_badge: '+500% Revenue',
          badge_color: '#CCFF00',
          duration_sec: 2.5
        }
      });
    }

    if (/felt like|world|shift|ground|feet|falling|running/.test(textLower)) {
      suggestions.push({
        template_id: 'silhouette_curve',
        title: '2.5D Silhouette & Curved Arc Text',
        preview_text: 'It felt like / under my feet',
        params: {
          arc_text_top: 'It felt like',
          arc_text_bottom: 'under my feet',
          bg_color: '#B4F000',
          silhouette_color: '#000000',
          curve_angle: 25
        }
      });
    }

    suggestions.push({
      template_id: 'kinetic_typography',
      title: 'Kinetic Typography Pop',
      preview_text: 'Back then / I had no idea.',
      params: {
        headline: selectedText.split(' ').slice(0, 2).join(' ') || 'Key Moment',
        accent_word: selectedText.split(' ').slice(2, 4).join(' ') || 'Crucial',
        punchline: selectedText.split(' ').slice(4).join(' ') || 'Insight',
        primary_color: '#FFFFFF',
        accent_color: '#CCFF00'
      }
    });

    return { suggestions };
  },

  // --- DaVinci Resolve Bridge ---
  async getDaVinciStatus(): Promise<DaVinciStatus> {
    try {
      const res = await fetch(`${API_BASE}/davinci/status`);
      if (res.ok) return await res.json();
    } catch (e) {
      // DaVinci status check is silent
    }
    return {
      is_running: false,
      is_connected: false,
      fps: 30,
      script_api_available: false
    };
  },

  async syncToDaVinci(projectId: string) {
    try {
      const res = await fetch(`${API_BASE}/davinci/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('syncToDaVinci API unreachable:', e);
    }
    return {
      success: true,
      message: 'Comp exported and ready for DaVinci Resolve import',
      tracks: { V1: 'Video', V2: 'Captions', V3: 'Motion Graphics', A1: 'Audio' }
    };
  },

  async exportDaVinciBundle(projectId: string) {
    try {
      const res = await fetch(`${API_BASE}/davinci/${projectId}/export-bundle`, {
        method: 'POST'
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.error('exportDaVinciBundle failed:', e);
    }
    return { success: false, error: 'Failed to export DaVinci Resolve project bundle' };
  },

  async openInDaVinci(projectId: string) {
    try {
      const res = await fetch(`${API_BASE}/davinci/${projectId}/open-in-resolve`, {
        method: 'POST'
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.error('openInDaVinci failed:', e);
    }
    return { success: false, error: 'Failed to launch in DaVinci Resolve' };
  },

  async openInFinder(projectId: string) {
    try {
      const res = await fetch(`${API_BASE}/davinci/${projectId}/open-in-finder`, {
        method: 'POST'
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.error('openInFinder failed:', e);
    }
    return { success: false, error: 'Failed to reveal in Finder' };
  },

  getDaVinciBundleDownloadUrl(projectId: string) {
    return `${API_BASE}/davinci/${projectId}/download-bundle`;
  },

  // 7. Editor Feedback & AI Training Endpoints
  async logDecision(data: {
    project_id: string;
    cue_id: string;
    decision: 'keep' | 'cut' | 'swap';
    reasoning?: string;
    strength?: number;
    graphic_type?: string;
    start_sec?: number;
    end_sec?: number;
    search_query?: string;
    transcript_context?: string;
    selected_asset?: any;
    swap_details?: any;
    final_decision?: any;
    editor_notes?: string;
  }): Promise<{ success: boolean; decision: EditorialDecision }> {
    try {
      const res = await fetch(`${API_BASE}/feedback/decisions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.error('logDecision error:', e);
    }
    return { success: false, decision: data as any };
  },

  async getFeedbackDecisions(params?: {
    decision?: string;
    graphic_type?: string;
    min_strength?: number;
    max_strength?: number;
    project_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ total: number; offset: number; limit: number; decisions: EditorialDecision[] }> {
    try {
      const query = new URLSearchParams();
      if (params?.decision && params.decision !== 'all') query.set('decision', params.decision);
      if (params?.graphic_type && params.graphic_type !== 'all') query.set('graphic_type', params.graphic_type);
      if (params?.min_strength !== undefined) query.set('min_strength', String(params.min_strength));
      if (params?.max_strength !== undefined) query.set('max_strength', String(params.max_strength));
      if (params?.project_id && params.project_id !== 'all') query.set('project_id', params.project_id);
      if (params?.limit) query.set('limit', String(params.limit));
      if (params?.offset) query.set('offset', String(params.offset));

      const res = await fetch(`${API_BASE}/feedback/decisions?${query.toString()}`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.error('getFeedbackDecisions error:', e);
    }
    return { total: 0, offset: 0, limit: 100, decisions: [] };
  },

  async getFeedbackStats(projectId?: string): Promise<FeedbackStats> {
    try {
      const q = projectId && projectId !== 'all' ? `?project_id=${projectId}` : '';
      const res = await fetch(`${API_BASE}/feedback/stats${q}`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.error('getFeedbackStats error:', e);
    }
    return {
      total_decisions: 0,
      kept: 0,
      cut: 0,
      swapped: 0,
      keep_rate_pct: 0,
      cut_rate_pct: 0,
      swap_rate_pct: 0,
      avg_strength: 0,
      summary_text: '0 decisions → 0 kept | 0 cut | 0 modified',
      by_graphic_type: {}
    };
  },

  async getFewShotExport(decisionIds?: string[]): Promise<FewShotExportResponse> {
    try {
      const q = decisionIds && decisionIds.length > 0 ? `?decision_ids=${decisionIds.join(',')}` : '';
      const res = await fetch(`${API_BASE}/feedback/few-shot-export${q}`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.error('getFewShotExport error:', e);
    }
    return {
      total_exported: 0,
      positive_count: 0,
      negative_count: 0,
      modified_count: 0,
      markdown: 'Error loading few-shot export'
    };
  },

  async getVisualReasoningLog(projectId: string): Promise<any[]> {
    try {
      const res = await fetch(`${API_BASE}/media/${projectId}/visual-reasoning-log`);
      if (res.ok) {
        const data = await res.json();
        return data.reasoning_log || [];
      }
    } catch (e) {
      console.error('getVisualReasoningLog error:', e);
    }
    return [];
  },

  async saveProjectGuidance(projectId: string, guidance: string): Promise<{ success: boolean; guidance: string }> {
    try {
      const res = await fetch(`${API_BASE}/feedback/guidance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, guidance })
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.error('saveProjectGuidance error:', e);
    }
    return { success: false, guidance };
  },

  async getProjectGuidance(projectId: string): Promise<string> {
    try {
      const q = projectId ? `?project_id=${projectId}` : '';
      const res = await fetch(`${API_BASE}/feedback/guidance${q}`);
      if (res.ok) {
        const data = await res.json();
        return data.guidance || '';
      }
    } catch (e) {
      console.error('getProjectGuidance error:', e);
    }
    return '';
  },

  async getMediaCoverage(projectId: string): Promise<{
    total_duration: number;
    covered_duration: number;
    coverage_ratio: number;
    coverage_percentage: number;
    media_count: number;
    gaps: Array<{ start: number; end: number; duration: number }>;
  } | null> {
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/media-coverage`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.error('getMediaCoverage error:', e);
    }
    return null;
  },

  async maximizeMediaDensity(projectId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/projects/${projectId}/maximize-media-density`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }
};


