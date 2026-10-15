import React, { useState, useEffect } from "react";
import {
  Sparkles,
  Camera,
  RefreshCw,
  Zap,
  ZoomIn,
  RotateCw,
  MoveHorizontal,
  MoveVertical,
  Activity,
  Maximize2,
  Check,
  Film,
  Key,
  ChevronDown,
  ChevronUp,
  Image as ImageIcon,
  AlertCircle
} from "lucide-react";
import { ProjectState } from "../../types";
import { api } from "../../services/api";

interface AIMotionGraphicsPanelProps {
  currentTime: number;
  project: ProjectState;
  activeCaptionText?: string;
  onAppendVideoTrack: (videoUrl: string, title: string, duration: number, overlayText: string, instructions: string, sourceCitation?: string) => void;
  captureCurrentCanvasFrame: () => string | null;
  prefilledOmni?: { prompt: string; cameraMotion: string; headline: string } | null;
}

interface CameraMotion {
  id: string;
  label: string;
  icon: any;
  prompt: string;
}

const CAMERA_MOTIONS: CameraMotion[] = [
  {
    id: "push_in",
    label: "Push In",
    icon: ZoomIn,
    prompt: "Slow cinematic dolly push-in camera move towards subject with shallow depth of field."
  },
  {
    id: "orbit",
    label: "Orbit 360°",
    icon: RotateCw,
    prompt: "Smooth orbital arc rotation around subject with dynamic volumetric lighting and parallax depth."
  },
  {
    id: "pan",
    label: "Pan Right",
    icon: MoveHorizontal,
    prompt: "Fluid horizontal cinematic camera pan tracking across the scene with consistent momentum."
  },
  {
    id: "tilt",
    label: "Crane Up",
    icon: MoveVertical,
    prompt: "Vertical crane tilt moving upwards from low angle to reveal majestic elevated perspective."
  },
  {
    id: "macro",
    label: "Macro Dive",
    icon: Maximize2,
    prompt: "High-magnification microscopic push-in into cellular structures with glowing fluorophores."
  },
  {
    id: "handheld",
    label: "Handheld",
    icon: Activity,
    prompt: "Organic handheld documentary camera motion with authentic natural micro-shake and breathing."
  }
];

export const AIMotionGraphicsPanel: React.FC<AIMotionGraphicsPanelProps> = ({
  currentTime,
  project,
  activeCaptionText = "",
  onAppendVideoTrack,
  captureCurrentCanvasFrame,
  prefilledOmni
}) => {
  // Mode: "text_to_video" (Higgsfield New Scene) vs "image_to_video" (Animate Canvas Frame)
  const [generationMode, setGenerationMode] = useState<"text_to_video" | "image_to_video">("text_to_video");
  const [aiOutputType, setAiOutputType] = useState<"video" | "image">("video");
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [snapshotBase64, setSnapshotBase64] = useState<string | null>(null);
  const [selectedMotion, setSelectedMotion] = useState<string>("push_in");
  const [motionIntensity, setMotionIntensity] = useState<"subtle" | "cinematic" | "dynamic">("cinematic");
  const [subjectPrompt, setSubjectPrompt] = useState<string>("");
  const [overlayText, setOverlayText] = useState<string>("");
  const [durationSec, setDurationSec] = useState<number>(5);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generationStep, setGenerationStep] = useState<string>("");
  const [lastGeneratedUrl, setLastGeneratedUrl] = useState<string | null>(null);

  // Gemini API Key state
  const [geminiSaved, setGeminiSaved] = useState(false);
  const [geminiApiKey, setGeminiApiKey] = useState<string>("");
  useEffect(() => {
    localStorage.removeItem("gemini_api_key");
    api.getProviderConfiguration().then(s => setGeminiSaved(s.gemini_saved)).catch(() => {});
  }, []);
  const [showApiKeyInput, setShowApiKeyInput] = useState<boolean>(false);

  useEffect(() => {
    if (prefilledOmni) {
      if (prefilledOmni.prompt) setSubjectPrompt(prefilledOmni.prompt);
      if (prefilledOmni.cameraMotion) setSelectedMotion(prefilledOmni.cameraMotion);
      if (prefilledOmni.headline) setOverlayText(prefilledOmni.headline);
    }
  }, [prefilledOmni]);

  useEffect(() => {
    if (activeCaptionText && !overlayText && !prefilledOmni) {
      setOverlayText(String(activeCaptionText).slice(0, 40));
    }
  }, [currentTime]);

  const handleCaptureFrame = () => {
    try {
      if (typeof captureCurrentCanvasFrame === "function") {
        const frame = captureCurrentCanvasFrame();
        if (frame) setSnapshotBase64(frame);
      }
    } catch (err) {
      console.warn("Frame capture:", err);
    }
  };

  const handleApiKeyChange = (keyVal: string) => {
    setGeminiApiKey(keyVal);

  };

  const handleGenerate = async (customPrompt?: string, customType?: "video" | "image") => {
    const promptToUse = (customPrompt !== undefined ? customPrompt : subjectPrompt).trim();
    const typeToUse = customType || aiOutputType;

    if (!promptToUse && generationMode === "text_to_video") {
      alert("Please enter a scene prompt describing what you want to see (e.g. 'An Indian man coughing in a clinic').");
      return;
    }

    setIsGenerating(true);
    setGenerationError(null);
    const targetAr = project?.settings?.aspect_ratio === "16:9" ? "16:9" : "9:16";

    try {
      if (typeToUse === "image") {
        setGenerationStep("Directing Google Imagen 3 image generation...");
        const res = await api.generateAIImage(
          project.id,
          promptToUse,
          targetAr,
          geminiApiKey.trim() || undefined
        );

        if (!res || !res.media_url) {
          throw new Error("No image URL returned by Google AI");
        }

        setLastGeneratedUrl(res.media_url);
        const titleLabel = overlayText.trim() || promptToUse.slice(0, 24);
        onAppendVideoTrack(
          res.media_url,
          titleLabel,
          4.0,
          overlayText.trim() || titleLabel,
          `AI Image: ${promptToUse}`,
          res.source_credit || "Generated with Google Imagen 3"
        );
        setGenerationStep("AI Image added to timeline!");
      } else {
        // Video Generation
        setGenerationStep(geminiApiKey ? "Directing Google AI Video..." : "Generating motion scene...");
        let currentFrame: string | null = null;
        if (generationMode === "image_to_video") {
          setGenerationStep("Anchoring <FIRST_FRAME>...");
          currentFrame = snapshotBase64;
          if (!currentFrame) {
            currentFrame = captureCurrentCanvasFrame();
            setSnapshotBase64(currentFrame);
          }
        }

        const activeMotionObj = CAMERA_MOTIONS.find((m) => m.id === selectedMotion) || CAMERA_MOTIONS[0];
        const res = await api.generateAIVideo(
          project.id,
          promptToUse,
          targetAr,
          durationSec,
          selectedMotion,
          geminiApiKey.trim() || undefined
        );

        if (!res || !(res.video_url || res.media_url)) {
          throw new Error("No video URL returned by Google AI");
        }

        const generatedUrl = res.video_url || res.media_url;
        setLastGeneratedUrl(generatedUrl);
        const titleLabel = overlayText.trim() || promptToUse.slice(0, 24) || `Motion: ${activeMotionObj.label}`;
        onAppendVideoTrack(
          generatedUrl,
          titleLabel,
          res.duration || durationSec,
          overlayText.trim() || titleLabel,
          `${promptToUse} (${activeMotionObj.label})`,
          res.source_credit || "Generated with Google AI Video"
        );
        setGenerationStep("AI Video added to timeline!");
      }
      setTimeout(() => setGenerationStep(""), 3000);
    } catch (e: any) {
      console.error("Google AI generation error:", e);
      setGenerationError(e.message || String(e));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleTestImageGeneration = () => {
    const testPrompt = "A clean editorial illustration of a modern hospital room, vertical 9:16";
    setSubjectPrompt(testPrompt);
    setAiOutputType("image");
    handleGenerate(testPrompt, "image");
  };

  const handleTestVideoGeneration = () => {
    const testPrompt = "Close-up of a hospital corridor, subtle camera push-in, realistic documentary style";
    setSubjectPrompt(testPrompt);
    setAiOutputType("video");
    handleGenerate(testPrompt, "video");
  };

  return (
    <div className="p-4 space-y-3.5 text-xs text-neutral-200 select-none overflow-y-auto max-h-full font-sans">
      {/* 1. Clean Header */}
      <div className="flex items-center justify-between border-b border-neutral-800/80 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center">
            <Sparkles className="h-3.5 w-3.5 text-cyan-300" />
          </div>
          <div>
            <div className="font-semibold text-xs text-white tracking-tight flex items-center gap-1.5">
              <span>Higgsfield Director</span>
              <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/60">
                Omni Flash
              </span>
            </div>
          </div>
        </div>
        <div className="text-[10px] font-mono text-neutral-500">
          {(currentTime || 0).toFixed(2)}s
        </div>
      </div>

      {/* 2. AI Output Type: Image vs Video */}
      <div className="space-y-1">
        <div className="text-[10px] font-medium text-neutral-400">OUTPUT MEDIA TYPE</div>
        <div className="grid grid-cols-2 gap-1 p-1 bg-neutral-950 rounded-xl border border-neutral-800">
          <button
            onClick={() => setAiOutputType("image")}
            className={`py-1.5 px-2 rounded-lg text-[10px] font-medium flex items-center justify-center gap-1.5 transition-all ${
              aiOutputType === "image"
                ? "bg-cyan-500 text-black font-bold shadow"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <ImageIcon className="h-3 w-3" />
            <span>AI Image (Imagen 3)</span>
          </button>
          <button
            onClick={() => setAiOutputType("video")}
            className={`py-1.5 px-2 rounded-lg text-[10px] font-medium flex items-center justify-center gap-1.5 transition-all ${
              aiOutputType === "video"
                ? "bg-cyan-500 text-black font-bold shadow"
                : "text-neutral-400 hover:text-white"
            }`}
          >
            <Film className="h-3 w-3" />
            <span>AI Video (Motion)</span>
          </button>
        </div>
      </div>

      {/* 2b. Test Verification Presets */}
      <div className="space-y-1">
        <div className="text-[10px] font-mono text-neutral-400">PIPELINE VERIFICATION TESTS</div>
        <div className="grid grid-cols-2 gap-1">
          <button
            onClick={handleTestImageGeneration}
            disabled={isGenerating}
            className="py-1 px-1.5 rounded-lg bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 hover:border-cyan-500/50 text-[9px] font-mono text-cyan-300 transition truncate disabled:opacity-50 text-left"
            title="A clean editorial illustration of a modern hospital room, vertical 9:16"
          >
            🧪 Test AI Image
          </button>
          <button
            onClick={handleTestVideoGeneration}
            disabled={isGenerating}
            className="py-1 px-1.5 rounded-lg bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 hover:border-cyan-500/50 text-[9px] font-mono text-cyan-300 transition truncate disabled:opacity-50 text-left"
            title="Close-up of a hospital corridor, subtle camera push-in, realistic documentary style"
          >
            🧪 Test AI Video
          </button>
        </div>
      </div>

      {/* Diagnostic Error Banner */}
      {generationError && (
        <div className="p-2.5 rounded-xl bg-red-950/60 border border-red-800/80 text-red-200 text-[10px] space-y-1 animate-in fade-in">
          <div className="flex items-center gap-1.5 font-bold text-red-300">
            <AlertCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
            <span>Google AI Generation Diagnostic</span>
          </div>
          <div className="font-mono text-[9px] text-red-300/90 leading-relaxed break-words">
            {generationError}
          </div>
        </div>
      )}

      {/* 2c. Generation Mode Switch: Text vs Image-to-Video (only for video) */}
      {aiOutputType === "video" && (
        <div className="space-y-1">
          <div className="text-[10px] font-medium text-neutral-400">VIDEO SOURCE</div>
          <div className="grid grid-cols-2 gap-1 p-1 bg-neutral-950 rounded-xl border border-neutral-800">
            <button
              onClick={() => setGenerationMode("text_to_video")}
              className={`py-1.5 px-2 rounded-lg text-[10px] font-medium flex items-center justify-center gap-1.5 transition-all ${
                generationMode === "text_to_video"
                  ? "bg-neutral-800 text-cyan-300 font-semibold shadow"
                  : "text-neutral-400 hover:text-white"
              }`}
            >
              <Film className="h-3 w-3" />
              <span>New Scene (Text)</span>
            </button>
            <button
              onClick={() => {
                setGenerationMode("image_to_video");
                handleCaptureFrame();
              }}
              className={`py-1.5 px-2 rounded-lg text-[10px] font-medium flex items-center justify-center gap-1.5 transition-all ${
                generationMode === "image_to_video"
                  ? "bg-neutral-800 text-cyan-300 font-semibold shadow"
                  : "text-neutral-400 hover:text-white"
              }`}
            >
              <Camera className="h-3 w-3" />
              <span>Animate Frame</span>
            </button>
          </div>
        </div>
      )}

      {/* 3. First Frame Anchor Card (Only visible when in Image-to-Video mode) */}
      {generationMode === "image_to_video" && (
        <div className="flex items-center gap-3 p-2 bg-neutral-950 rounded-xl border border-neutral-800 animate-in fade-in duration-200">
          <div className="w-16 h-12 rounded-lg bg-neutral-900 overflow-hidden relative flex-shrink-0 border border-neutral-800 flex items-center justify-center">
            {snapshotBase64 ? (
              <img src={snapshotBase64} alt="Frame Anchor" className="w-full h-full object-cover" />
            ) : (
              <Camera className="h-4 w-4 text-neutral-600" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[10px] font-semibold text-neutral-200 flex items-center gap-1">
              <span>First Frame Anchor</span>
              <span className="text-[8px] font-mono text-cyan-400 bg-cyan-950/60 px-1 rounded">&lt;FIRST_FRAME&gt;</span>
            </div>
            <div className="text-[9px] text-neutral-400 truncate mt-0.5">
              Camera animates starting from this video frame
            </div>
          </div>
          <button
            onClick={handleCaptureFrame}
            className="p-1.5 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-neutral-400 hover:text-cyan-300 border border-neutral-800 transition-colors"
            title="Recapture current frame"
          >
            <RefreshCw className="h-3 w-3" />
          </button>
        </div>
      )}

      {/* 4. Scene Prompt Input */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[10px] font-medium text-neutral-400">
          <span>SCENE PROMPT</span>
          <span className="text-[9px] font-mono text-cyan-400">SUBJECT & ACTION</span>
        </div>
        <textarea
          value={subjectPrompt}
          onChange={(e) => setSubjectPrompt(e.target.value)}
          placeholder="e.g. An Indian man coughing bad, sitting in a medical clinic, distressed expression, cinematic volumetric lighting..."
          rows={2}
          className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-2 text-xs text-white placeholder-neutral-600 outline-none focus:border-cyan-500/50 transition-colors resize-none"
        />
      </div>

      {/* 5. Higgsfield Visual Camera Director Controls (Video Only) */}
      {aiOutputType === "video" && (
        <>
          <div className="space-y-1.5">
            <div className="text-[10px] font-medium text-neutral-400 flex items-center justify-between">
              <span>CAMERA MOVEMENT</span>
              <span className="text-[9px] text-cyan-400 font-mono">DOP CONTROL</span>
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {CAMERA_MOTIONS.map((motion) => {
                const Icon = motion.icon;
                const isSelected = selectedMotion === motion.id;
                return (
                  <button
                    key={motion.id}
                    onClick={() => setSelectedMotion(motion.id)}
                    className={`p-2 rounded-xl flex flex-col items-center justify-center gap-1.5 transition-all text-center border ${
                      isSelected
                        ? "bg-cyan-500/15 border-cyan-500/60 text-white shadow-sm ring-1 ring-cyan-500/30"
                        : "bg-neutral-900/90 border-neutral-800 hover:border-neutral-700 text-neutral-400 hover:text-neutral-200"
                    }`}
                  >
                    <Icon className={`h-4 w-4 ${isSelected ? "text-cyan-300" : "text-neutral-400"}`} />
                    <span className="text-[10px] font-medium leading-none">{motion.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 6. Motion Intensity */}
          <div className="space-y-1">
            <div className="text-[10px] font-medium text-neutral-400">MOTION INTENSITY</div>
            <div className="grid grid-cols-3 gap-1 p-1 bg-neutral-950 rounded-xl border border-neutral-800">
              {(["subtle", "cinematic", "dynamic"] as const).map((intensity) => (
                <button
                  key={intensity}
                  onClick={() => setMotionIntensity(intensity)}
                  className={`py-1 rounded-lg text-[10px] font-medium capitalize transition-all ${
                    motionIntensity === intensity
                      ? "bg-neutral-800 text-cyan-300 font-semibold shadow"
                      : "text-neutral-400 hover:text-white"
                  }`}
                >
                  {intensity}
                </button>
              ))}
            </div>
          </div>

          {/* 8. Duration Selector */}
          <div className="flex items-center justify-between pt-0.5">
            <span className="text-[10px] font-medium text-neutral-400">CLIP DURATION</span>
            <div className="flex items-center gap-1.5">
              {[3, 5, 8, 10].map((d) => (
                <button
                  key={d}
                  onClick={() => setDurationSec(d)}
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-mono transition-all ${
                    durationSec === d
                      ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold"
                      : "bg-neutral-900 border border-neutral-800 text-neutral-400 hover:text-white"
                  }`}
                >
                  {d}s
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {/* 7. On-Screen Headline (Optional) */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[10px] font-medium text-neutral-400">
          <span>ON-SCREEN HEADLINE</span>
          <span className="text-[9px] font-mono text-neutral-500">OPTIONAL</span>
        </div>
        <input
          type="text"
          value={overlayText}
          onChange={(e) => setOverlayText(e.target.value)}
          placeholder="e.g. TUBERCULOSIS ASSESSMENT"
          className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-1.5 text-xs text-white placeholder-neutral-600 outline-none focus:border-cyan-500/50 transition-colors"
        />
      </div>

      {/* 9. Collapsible Gemini API Key Settings */}
      <div className="pt-1 border-t border-neutral-800/80">
        <button
          onClick={() => setShowApiKeyInput(!showApiKeyInput)}
          className="w-full flex items-center justify-between text-[10px] text-neutral-400 hover:text-neutral-200 py-1 transition-colors"
        >
          <div className="flex items-center gap-1.5">
            <Key className="h-3 w-3 text-cyan-400" />
            <span>Gemini / Google AI Key</span>
            <span className={`text-[8px] font-mono px-1 py-0.2 rounded ${geminiApiKey ? "bg-emerald-950 text-emerald-400 border border-emerald-800" : "bg-neutral-800 text-neutral-400"}`}>
              {geminiApiKey ? "New key entered" : geminiSaved ? "Saved on backend" : "Enter Key"}
            </span>
          </div>
          {showApiKeyInput ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </button>
        {showApiKeyInput && (
          <div className="mt-1.5 space-y-1 animate-in fade-in duration-200">
            <input
              type="password"
              value={geminiApiKey}
              onChange={(e) => handleApiKeyChange(e.target.value)}
              placeholder="Optional replacement key (saved on generation)"
              className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3 py-1.5 text-xs text-white placeholder-neutral-600 outline-none focus:border-cyan-500/50 transition-colors font-mono"
            />
            <div className="text-[9px] text-neutral-500">
              When provided, visuals are generated directly via official Google Imagen 3 and Google AI endpoints.
            </div>
          </div>
        )}
      </div>

      {/* 10. Generate Button */}
      <button
        onClick={() => handleGenerate()}
        disabled={isGenerating}
        className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-xs tracking-wide shadow-lg shadow-cyan-500/10 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed mt-1 border border-white/10"
      >
        {isGenerating ? (
          <>
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            <span>{generationStep || "Generating..."}</span>
          </>
        ) : aiOutputType === "image" ? (
          <>
            <ImageIcon className="h-3.5 w-3.5 fill-white" />
            <span>Generate AI Image (Imagen 3)</span>
          </>
        ) : (
          <>
            <Zap className="h-3.5 w-3.5 fill-white" />
            <span>Generate AI Video (Motion)</span>
          </>
        )}
      </button>

      {/* 11. Success Notification */}
      {lastGeneratedUrl && !isGenerating && (
        <div className="p-2 rounded-lg bg-neutral-950 border border-cyan-800/40 flex items-center gap-2">
          <div className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-300 flex items-center justify-center flex-shrink-0">
            <Check className="h-3 w-3" strokeWidth={2.5} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[10px] font-semibold text-cyan-200">Added to Active Timeline</div>
            <div className="text-[8px] text-neutral-400 truncate">{lastGeneratedUrl}</div>
          </div>
        </div>
      )}
    </div>
  );
};
