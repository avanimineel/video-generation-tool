# Studio UI and UX context

Context for anyone changing the editor interface. This describes the shell that is actually mounted in `frontend/src/App.tsx` on `main` as of 18 November 2026. `docs/02_FRONTEND_ARCHITECTURE_AND_COMPONENTS.md` still describes an older left-rail layout, port `8002`, and a purple feedback pill. Follow this file for UI work until that older spec is rewritten.

The product goal for the shell is a light-theme documentary editor where the 9:16 preview is the largest surface, speech defines the cut, and chrome stays quiet until the editor asks for it.

## What is on screen

The mounted page is one full-viewport column:

1. **Top bar** (`TopNavBar.tsx`, `h-13`, white). Identity, project, upload, save state, aspect ratio, undo, film tools, Twelve Labs, Resolve, Export, and the inspector toggle all share this single row.
2. **Status strip** (inline in `App.tsx`). After a source file exists, a one-line census (`captions`, English lines, added visuals, camera beats) plus a Review button. While auto-produce runs, a dark banner replaces that quiet strip.
3. **Center row.** `VideoViewer` takes the remaining width. The inspector is `w-80` when open and a `w-10` rail labeled INSPECTOR when closed.
4. **Timeline** (`Timeline.tsx`). `h-[168px]` when open, `h-8` when collapsed.

`LeftSidebar.tsx` is about 1,900 lines and is not imported by `App.tsx`. It still contains medical topic buckets and an API-key form. The live editor does not show it.

A second product opens on top of this shell. The black **Studio** button mounts `components/studio/Studio.tsx`, a full-screen film maker (website or idea, Claude or Gemini, its own preview iframe and timeline). **Brand film** opens `BrandVideoModal` beside it. The wordmark in the top bar is also “Studio”.

## Decisions already implemented

Keep these. They are the current hierarchy, not leftovers.

- Light chrome: `bg-white`, `bg-neutral-100`, `border-neutral-200`, `text-neutral-900`. Saturated color belongs on the picture (captions, splits, graphics), not on the tool chrome. Timeline track tints (amber, cyan, violet, emerald, indigo) are the exception.
- Preview dominance. The inspector starts collapsed when the viewport is under 1000px tall or under 1440px wide. The choice is stored in `localStorage` as `studio.inspectorCollapsed`.
- The timeline starts collapsed for 9:16 and remembers `studio.timelineCollapsed`.
- The 9:16 frame is sized by height (`aspect-[9/16] h-full w-auto`) so the portrait picture fills the center column.
- The inspector is three tabs: Subtitles, Graphics, Music / SFX. Selecting a graphic switches to Graphics.
- Playback uses the project proxy. A music bed ducks while a caption is on screen.
- Autosave is debounced. Failure uses an amber banner with Retry and Open projects. That banner is the pattern other failures should follow.
- Delete and Backspace remove the selected graphic, or the selected caption when no graphic is selected. Inputs and text areas are ignored.

## How the pieces behave

| Surface | Role | Current behavior |
| --- | --- | --- |
| Top bar | Wayfinding and commit | Two filled black buttons (Studio and Export) compete. Most labels disappear below `xl`, leaving icons. `onExportComp` is an empty function. New project and Projects both open the same drawer. Aspect control offers 9:16 and 16:9. The type still allows 1:1, and the film maker offers 1:1, but the editor toggle does not. |
| Status strip | What to do next | Healthy state reads as a census (“Video prepared · N captions…”) plus “Inspect inserted or skipped treatments when ready.” Attention and gap states correctly turn amber. |
| Viewer | The edit | Play, pause, and a timecode sit on the frame. Canvas overlays draw splits, titles, karaoke, and safe area. Playback errors set a string in the viewer. Most other failures call `window.alert`. |
| Inspector | Detail for the selection | Fixed 320px. A graphic selection opens Graphics. A caption selection does not open Subtitles, so the detail can stay on the wrong tab. Collapse is duplicated: the rail and a top-bar icon. |
| Timeline | When things happen | Six lanes plus a ruler are packed into 168px, so the lanes scroll inside the pane. Collapse keeps the toolbar and hides the lanes. Zoom is pixels-per-second, default 60. |
| Studio overlay | Make a film from a site or a sentence | Separate layout, its own timeline component, preview in an iframe. It does not share selection, playhead, or undo with the caption editor. |
| Dialogs | Results and lists | Download-ready and DaVinci-bundle dialogs are written inline in `App.tsx`. Project drawer, editorial plan, reasoning log, feedback, and brand film are separate components. There is no shared dialog behavior for Escape or focus. |

`App.tsx` owns project state, playback, undo, upload, transcription, auto-produce, render, and DaVinci export. That file is the place a new banner or shortcut has to land today.

Keyboard coverage is the Delete handler only. Play, undo, and redo have buttons and no keys.

`window.alert` is the failure voice for upload, auto-produce, burn-in, transcription, project delete, DaVinci sync, Twelve Labs indexing, and several inspector uploads. Alerts sit outside the light theme and block the page.

The viewer calls the API on `hostname:8003` whenever the page is served from port 5173 or 5174 (`BACKEND_ORIGIN` in `frontend/src/services/api.ts`). A test link on port 5174 also needs port 8003 reachable from the same host.

## Suggestions

These are the changes to make next, in order. Do not reopen the left rail, and do not put Wikimedia-style chrome or a second dark theme into the editor.

### 1. One primary action in the top bar

Export stays the filled black button. Move Studio, Brand film, Feedback, Twelve Labs, and the Resolve cluster into one tools menu. The wordmark stays “Studio” for the editor. Rename the film maker control so it does not repeat that word. “Make film” matches the overlay’s own heading.

### 2. Failures use the amber banner, not `alert`

Upload, render, transcribe, delete, and sync errors should append to the existing save-error strip, or a single dismissible toast with the same amber treatment. Include the action that failed and a retry where the call is safe to repeat. Remove `alert()` from `App.tsx`, `TopNavBar.tsx`, and the inspector upload paths as those calls are touched.

### 3. Playback and history keys

Space toggles play when focus is not in a field. Cmd/Ctrl+Z and Cmd/Ctrl+Shift+Z call the undo and redo handlers that already exist. Keep Delete and Backspace as they are.

### 4. The first screen is the upload

When `source_media_path` is empty, the center column should be the upload action and a one-line description of the pipeline (transcribe, translate, review, export). The full tool row can stay, in its quieter form. An empty 9:16 frame under every control asks the editor to understand the product before they have a picture.

### 5. The status strip names the next step

When the edit is healthy, the strip can be one short line and the Review button, for example “Captions ready. Review the edit, then export.” Keep the amber treatment and the scorecard text for `needs_review` and `completed_with_gaps`. The long census can live inside Review.

### 6. The timeline can grow

Replace the fixed 168px with a splitter the editor can drag, with the collapsed `h-8` state kept. Default open height should show the ruler and the caption lane without an inner scrollbar. Track tint can stay, because it is the only color that distinguishes lanes.

### 7. Selection opens the matching inspector tab

A caption selection should switch to Subtitles the same way a graphic selection switches to Graphics. Seeking from a lane should do the same.

### 8. One dialog pattern

Extract the download and DaVinci success dialogs onto the same component: white panel, neutral border, Escape closes, focus returns to the control that opened it. New modals use that component.

### 9. Retire the unused left sidebar from the live path

Leave `LeftSidebar.tsx` unwired. Do not import it to “restore” stock search or API keys in the editor. Stock search for auto-produce belongs in the asset-review pipeline, not in a medical topic list. If the file stays, a comment at the top should say it is unused.

### 10. Aspect ratios match across both tools

Either add 1:1 to the editor toggle or stop offering it in the film maker until the caption editor can preview it. The preview sizing rule for 9:16 (height drives the frame) should be the rule for every ratio.

## Files to touch when implementing the suggestions

| Suggestion | Files |
| --- | --- |
| 1, 4, 5 | `frontend/src/components/layout/TopNavBar.tsx`, `frontend/src/App.tsx` |
| 2 | `frontend/src/App.tsx`, `TopNavBar.tsx`, `GraphicsTabInspector.tsx`, `AIMotionGraphicsPanel.tsx` |
| 3 | `frontend/src/App.tsx` key handler |
| 6, 7 | `frontend/src/components/timeline/Timeline.tsx`, `UnifiedStudioInspector.tsx` |
| 8 | `frontend/src/App.tsx` and a small shared dialog component |
| 9 | `frontend/src/components/sidebar/LeftSidebar.tsx` only if it is deleted or marked unused |
| 10 | `TopNavBar.tsx`, `VideoViewer.tsx`, `components/studio/Studio.tsx` |

After those land, replace the layout section of `docs/02_FRONTEND_ARCHITECTURE_AND_COMPONENTS.md` so it matches this shell.
