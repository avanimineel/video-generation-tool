---
name: caption-transcription
description: >-
  Hindi and Hinglish caption transcription, Gemini-first English translation,
  NLLB fallback, medical meaning checks, sentence joining, and caption edits
  for DaVinci Resolve Companion. Use before changing Whisper, translation,
  NLLB, caption layout, Join sentences, Redo captions, Save edit, or
  Save mapping for training.
---

# Caption transcription

Speech sets the words and the times. English is a label on that same span. A later change to the English does not move the time. The picture is not used to decide what was said.

Read this skill before editing `transcription_service.py`, `translation_service.py`, `automatic_captions.py`, `caption_mappings.py`, or the caption review UI.

## Pipeline

1. Domain on the project is `general`, `medical`, or `sports`. Unknown values become `general`. The Whisper prompt comes from `caption_prompt(domain)`.
2. Whisper `task=transcribe` writes the spoken words and word times. One language for the file. Hindi and English in one sentence stay one utterance.
3. `chunk_spoken_phrases` keeps a clause together (pause about 0.45s, break on `। . ? !`, max 18 words). Do not go back to 3-word boxes for the captions the editor reads.
4. Drop a Whisper segment only for a repetition loop (`compression_ratio > 2.4`), silence decoded as speech, or a stock closing on low confidence. Ordinary quiet speech stays.
5. Rejoin split numbers (`3` + `,000`). A few fixed sound-alikes run after the listen (`cuff` → `cough` in a medical line).
6. Join adjacent Hindi clauses, then `restore_sentences`, then translate.
7. Display path does **not** call `layout_automatic_captions`. That helper still slices English into 3-word groups for an old test. New caption work keeps the spoken sentence.

## Who translates

- Hindi (Devanagari) uses **Gemini** when `GEMINI_API_KEY` is set, including when `TRANSLATION_BACKEND=local`.
- English lines stay on the local path and are not sent to Gemini.
- If Gemini fails, that batch falls back to **NLLB** `facebook/nllb-200-distilled-600M`, `hin_Deva` → `eng_Latn`.
- Launcher default is `TRANSLATION_BACKEND=auto`. NLLB is the offline fallback, not the Hindi quality path.
- A larger NLLB competes with Whisper on the 16 GB GPU. Do not load one in the caption pass.

NLLB on this medical video spelled Hindi instead of translating it: “Adelog”, “him a thief”, “a thief’s medicine”, “patients without lung coughs”. Fluent grammar is not a pass. Those strings were saved in `transcription/translation_checkpoints` and replayed. Checkpoint identity is versioned (`version` in the digest). A rejected line must not be resumed. **Redo captions** deletes that cache for the video.

## Medical meaning, no person required

`normalize_medical_asr` rewrites mishearings before translation: `अदेलोग` / `आदिय लोग` → `आधे लोग`; `कांसर` → `कैंसर`; `उसकोलंग्` → `उसको लंग`. A correct phrase such as `फेफड़े का कैंसर` is not rewritten before the translator sees it.

## Running inferences

Decisions such as TB versus television use `RunningInferences`, walked in time order.

- Same-line evidence comes first. `टीवी` / `तीवी` with medicine, `मान`, `जैसा`, or `तरह` is TB. `टीवी पर` and “watching TV” stay television.
- If the line itself does not decide, earlier lines do. TB already established, or a lung disease already established in a medical project, makes a later `टीवी` into TB.
- The Gemini prompt for that later line includes those inferences and is told to write TB-like, not TV-like.
- English that still says “TV-like”, “TV”, or “television” for that decision is rejected. The replacement is “TB-like”.
- A line already stored on the project, including one marked `editor_locked` by Save edit, is corrected when the project is opened. The running server must be restarted after this code changes; it does not reload by itself. A finished translation is not treated as done while that English is still unusable.
- The spoken line about half the people, TB medicine, and half the people treating it as a lung infection with no medicine is two clauses. “कोई दवाई नहीं” means no medicine is started. It does not mean the illness is not an infection.
- After a lung-disease line, or on a patient line: `जाथ पेशेन्द` / `ददॉन` is “most patients come without any pain,” not the spellings “Jath”, “Profesand”, or “Dadon.” `सास में` with `दिक्कत` is breathing. It is not mother-in-law, and `पेशेंट` is not “a professional.” A family line such as `मेरी सास ने` stays mother-in-law.
- Saving a mapping still does not train Whisper or NLLB. A later weight update is a separate job and only uses lines that already passed this check.

`medical_english_is_unusable` rejects a line when:

- it is a Latin spelling of the Hindi (`is_transliteration_fragment`, including “Adelog” and “The Adelog considered”)
- TB medicine came out as thief, theft, or television, or the word TB is missing
- lung cancer or cancer came out as cough, or lung cancer is missing

`repair_medical_english` then writes the English that is used:

- TB medicine for half the people, when the spoken word was the TV homophone → “For half the people, it is taken as TB-like and TB medicine is started.”
- The following clause, half the people treating it as a lung infection and starting no medicine → “For half the people, it is taken as a lung infection and no medicine is started.”
- lung cancer named as cough → “The disease is lung cancer.”

`correct_medical_lines` applies that after translation and after saved edits. A saved line that fails the check is not put back. A saved line that passes stays, `editor_locked`. A correct sentence such as “Lung cancer is the commonest cancer in the world.” is left as it is.

Do not add a step that waits for a person to mark the line before this check runs.

## What the editor controls do

| Control | Effect |
| --- | --- |
| View captions | List, seek, edit |
| Join sentences | Join short chips into one clause, translate only lines that still need it, then run the medical check |
| Save edit | Locks that line. A locked line that fails the medical check is still replaced |
| Save mapping for training | Stores words and times in `caption_mappings.json` and up to 3 examples (80 chars) on the next Whisper prompt. **Does not train or change Whisper or NLLB weights** |
| Redo captions | Same video, clears captions and translation checkpoints, transcribes again, restores saved lines that pass the medical check |

Uploading the file again is not how captions are redone.

## Weights

Do not write Gemini output, vision labels, or an editor line into NLLB or Whisper weights on a caption pass. A future local-model update may store an accepted pair only after the medical check passes, and only then consider a separate LoRA job. If that job makes held-out lines worse, discard the weights and keep the correction in `correct_medical_lines`. Vision confirms a pictured entity. It does not write the sentence.

## Code map

| Piece | Location |
| --- | --- |
| Domain prompt, phrase chunks, hallucination filter | `backend/app/services/transcription_service.py` |
| Normalize, medical check, repair, join, translate | `backend/app/services/translation_service.py` |
| NLLB load and `hin_Deva` → `eng_Latn` | `backend/app/services/local_translation.py` |
| Redo captions, skip 3-word layout | `backend/app/services/auto_production_service.py` |
| Saved lines, prompt examples, no weight update | `backend/app/services/caption_mappings.py` |
| Legacy 3-word display | `backend/app/services/automatic_captions.py` |
| Join sentences button | `frontend/src/components/modals/CaptionReview.tsx` |

## Tests

```bash
.venv/bin/python -m pytest backend/tests/test_translation_mapping.py backend/tests/test_local_translation.py backend/tests/test_auto_produce_mode.py backend/tests/test_caption_mappings.py backend/tests/test_automatic_caption_policy.py backend/tests/test_project_domain.py -q
```

Any change to Hindi→English must keep these true: “Adelog” and “thief” are not stored; the TB line repairs to the half-the-people sentence; “patients without lung coughs” repairs to lung cancer; an already-correct cancer sentence stays; an edited line that passes the check is not translated again.
