/**
 * Gemini Omni Motion Graphics Generator (Node.js)
 * 
 * Model: gemini-omni-1.1-flash
 * Protocol: Google Gemini Interactions API / @google/genai SDK
 * 
 * Features:
 * 1. Takes HTML5 Canvas snapshot (base64 PNG) as <FIRST_FRAME> starting anchor
 * 2. Enforces strict verbatim text rendering (zero paraphrasing/hallucination)
 * 3. Configures portrait 9:16 reel aspect ratio, duration (3-10s), and resolution (720p/1080p)
 * 4. Downloads generated video asset and returns metadata for multi-track timeline placement
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta";
const DEFAULT_MODEL = "gemini-omni-1.1-flash";

/**
 * Strict System Instruction enforcing verbatim text rendering
 */
export const OMNI_VERBATIM_SYSTEM_INSTRUCTION = `
You are an ultra-high-precision motion graphics and medical visualizer engine powered by Gemini Omni 1.1 Flash.

CRITICAL DIRECTIVE FOR TEXT RENDERING:
1. Render all overlay text, typography, subtitles, and labels EXACTLY as provided in quotes.
2. DO NOT alter, paraphrase, summarize, reword, or substitute any word.
3. Every single letter, casing, spacing, and punctuation mark must match verbatim.
4. Typography must be rendered with high contrast, sharp geometric kerning, and modern broadcast documentary aesthetics.
5. If medical terminology or scientific data is provided (e.g. "PULMONARY TISSUE", "94% REMISSION RATE"), display it prominently without distortion.
`.trim();

/**
 * Helper to upload a base64 image or buffer to the Gemini Files API
 */
async function uploadFrameToFilesApi(base64Data, apiKey) {
  const cleanBase64 = base64Data.replace(/^data:image\/\w+;base64,/, "");
  const buffer = Buffer.from(cleanBase64, "base64");
  const numBytes = buffer.length;
  const mimeType = "image/png";

  const initRes = await fetch(`${GEMINI_API_ENDPOINT}/upload/v1beta/files`, {
    method: "POST",
    headers: {
      "x-goog-api-key": apiKey,
      "X-Goog-Upload-Protocol": "resumable",
      "X-Goog-Upload-Command": "start",
      "X-Goog-Upload-Header-Content-Length": String(numBytes),
      "X-Goog-Upload-Header-Content-Type": mimeType,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      file: { display_name: `canvas_frame_${Date.now()}.png` }
    })
  });

  if (!initRes.ok) {
    const errText = await initRes.text();
    throw new Error(`Failed to initiate Files API upload (${initRes.status}): ${errText}`);
  }

  const uploadUrl = initRes.headers.get("x-goog-upload-url");
  if (!uploadUrl) {
    throw new Error("Files API did not return an upload URL");
  }

  const uploadRes = await fetch(uploadUrl, {
    method: "POST",
    headers: {
      "Content-Length": String(numBytes),
      "X-Goog-Upload-Offset": "0",
      "X-Goog-Upload-Command": "upload, finalize"
    },
    body: buffer
  });

  if (!uploadRes.ok) {
    const errText = await uploadRes.text();
    throw new Error(`Failed to upload frame bytes (${uploadRes.status}): ${errText}`);
  }

  const fileInfo = await uploadRes.json();
  return {
    uri: fileInfo.file.uri,
    mimeType: fileInfo.file.mimeType || mimeType,
    name: fileInfo.file.name
  };
}

/**
 * Main function to generate an Omni Motion Graphic video chunk
 */
export async function generateOmniMotionGraphic({
  base64Frame,
  overlayText = "",
  motionInstructions = "",
  duration = 5,
  aspectRatio = "9:16",
  resolution = "720p",
  outputPath = null,
  apiKey = process.env.GEMINI_API_KEY
}) {
  if (!apiKey) {
    throw new Error("GEMINI_API_KEY environment variable or parameter is required.");
  }

  const durationInt = Math.max(3, Math.min(10, Math.round(duration || 5)));
  const validatedAspect = aspectRatio === "16:9" ? "16:9" : "9:16";
  const validatedRes = ["360p", "720p", "1080p", "4k"].includes(resolution) ? resolution : "720p";

  console.log(`[Gemini Omni] Starting generation with model: ${DEFAULT_MODEL}`);
  console.log(`[Gemini Omni] Aspect Ratio: ${validatedAspect} | Duration: ${durationInt}s | Resolution: ${validatedRes}`);

  const inputParts = [];

  // 1. Upload Canvas Snapshot as First Frame anchor
  if (base64Frame) {
    console.log("[Gemini Omni] Uploading canvas snapshot to Gemini Files API...");
    const uploadedFile = await uploadFrameToFilesApi(base64Frame, apiKey);
    console.log(`[Gemini Omni] Canvas snapshot uploaded successfully: ${uploadedFile.uri}`);

    inputParts.push({
      type: "image",
      uri: uploadedFile.uri,
      mime_type: uploadedFile.mimeType
    });
  }

  // 2. Build Prompt with <FIRST_FRAME> tag and strict verbatim text instructions
  let constructedPrompt = "";
  if (base64Frame) {
    constructedPrompt += "<FIRST_FRAME> ";
  }

  constructedPrompt += motionInstructions.trim();

  if (overlayText && overlayText.trim()) {
    constructedPrompt += ` Render the following overlay text VERBATIM on screen with high-contrast broadcast typography: \"${overlayText.trim()}\". Keep typography clean, razor-sharp, and perfectly legible.`;
  }

  inputParts.push({
    type: "text",
    text: constructedPrompt
  });

  // 3. Configure Interactions API payload
  const requestPayload = {
    model: DEFAULT_MODEL,
    system_instruction: OMNI_VERBATIM_SYSTEM_INSTRUCTION,
    input: inputParts,
    response_format: {
      type: "video",
      delivery: "uri",
      aspect_ratio: validatedAspect,
      duration: `${durationInt}s`,
      resolution: validatedRes
    }
  };

  console.log("[Gemini Omni] Submitting request to Interactions API...");
  const interactionRes = await fetch(`${GEMINI_API_ENDPOINT}/interactions`, {
    method: "POST",
    headers: {
      "x-goog-api-key": apiKey,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(requestPayload)
  });

  if (!interactionRes.ok) {
    const errText = await interactionRes.text();
    throw new Error(`Gemini Omni generation failed (${interactionRes.status}): ${errText}`);
  }

  const interactionData = await interactionRes.json();
  const interactionId = interactionData.id || interactionData.interaction?.id;
  console.log(`[Gemini Omni] Interaction Created: ${interactionId}`);

  const outputVideo =
    interactionData.output_video ||
    interactionData.interaction?.output_video ||
    interactionData.outputs?.find((o) => o.type === "video");

  const videoUri = outputVideo?.uri;
  if (!videoUri) {
    throw new Error(
      "Gemini Omni response did not contain a valid video URI. Payload: " +
        JSON.stringify(interactionData)
    );
  }

  console.log(`[Gemini Omni] Video generated successfully. Source URI: ${videoUri}`);

  // 4. Download generated video to local disk if outputPath is provided
  let savedLocalPath = null;
  if (outputPath) {
    const destDir = path.dirname(outputPath);
    if (!fs.existsSync(destDir)) {
      fs.mkdirSync(destDir, { recursive: true });
    }

    console.log(`[Gemini Omni] Downloading generated video to: ${outputPath}...`);
    const downloadRes = await fetch(videoUri, {
      headers: { "x-goog-api-key": apiKey }
    });

    if (!downloadRes.ok) {
      throw new Error(`Failed to download video file: ${downloadRes.statusText}`);
    }

    const arrayBuffer = await downloadRes.arrayBuffer();
    fs.writeFileSync(outputPath, Buffer.from(arrayBuffer));
    savedLocalPath = outputPath;
    console.log(`[Gemini Omni] Video saved locally to: ${savedLocalPath}`);
  }

  return {
    success: true,
    interaction_id: interactionId,
    video_url: videoUri,
    local_path: savedLocalPath,
    duration: durationInt,
    aspect_ratio: validatedAspect,
    overlay_text: overlayText,
    prompt: constructedPrompt
  };
}

// CLI Execution Support
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const sampleFramePath = process.argv[2];
  const overlay = process.argv[3] || "PULMONARY VASCULATURE";
  const instructions =
    process.argv[4] ||
    "Macro push-in to alveolar capillary network with glowing cyan telemetry nodes.";

  if (!process.env.GEMINI_API_KEY) {
    console.error("Error: GEMINI_API_KEY environment variable is required.");
    process.exit(1);
  }

  let base64 = null;
  if (sampleFramePath && fs.existsSync(sampleFramePath)) {
    base64 = fs.readFileSync(sampleFramePath).toString("base64");
  }

  const outDest = path.join(__dirname, `../projects/omni_preview_${Date.now()}.mp4`);

  generateOmniMotionGraphic({
    base64Frame: base64,
    overlayText: overlay,
    motionInstructions: instructions,
    duration: 5,
    aspectRatio: "9:16",
    resolution: "720p",
    outputPath: outDest
  })
    .then((result) => {
      console.log("Gemini Omni Generation Result:", result);
    })
    .catch((err) => {
      console.error("Execution Error:", err);
      process.exit(1);
    });
}
