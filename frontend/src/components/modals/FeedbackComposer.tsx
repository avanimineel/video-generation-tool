import React,{useState} from 'react';
import {api} from '../../services/api';
import {ProjectState} from '../../types';
export function FeedbackComposer({project,time,onSaved,onUpdated}:{project:ProjectState,time:number,onSaved:()=>void,onUpdated:(p:ProjectState)=>void}){
 const [target,setTarget]=useState('moment'),[start,setStart]=useState(time),[end,setEnd]=useState(Math.min(project.duration_seconds,time+5));
 const [decision,setDecision]=useState<'keep'|'cut'|'swap'>('swap'),[notes,setNotes]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState(''),[dirty,setDirty]=useState(false);
 const graphic=project.graphics.find(g=>g.id===target);
 async function save(){
  setError('');setMessage('');const a=graphic?.start??start,b=graphic?.end??end;
  if(!notes.trim()){setError('Explain what was wrong or what should appear instead.');return;}
  if(a<0||b<=a||b>project.duration_seconds+.1){setError('Choose a valid start and end within this video.');return;}
  setBusy(true);
  try{const result=await api.logDecision({project_id:project.id,cue_id:graphic?.id??`moment_${a.toFixed(2)}_${b.toFixed(2)}`,decision,start_sec:a,end_sec:b,graphic_type:graphic?.template_id??'missing_visual',reasoning:notes.trim(),editor_notes:notes.trim(),transcript_context:project.captions.filter(c=>c.start<b&&c.end>a).map(c=>c.translated_text||c.text).join(' '),selected_asset:graphic?{url:graphic.source_url,media_url:graphic.media_url,title:graphic.title}:undefined});
   if(!result.success)throw new Error('Feedback could not be saved. Please retry.');
   setDirty(false);setMessage('Saved. This feedback will guide the next iteration.');onSaved();
  }catch(e){setError(String(e));}finally{setBusy(false);}
 }
 async function iterate(){setBusy(true);setError('');setMessage('Creating the next iteration with saved feedback…');try{const r=await api.runAutoProduction(project.id,true);if(r.project)onUpdated(r.project);if(!r.success||r.editorial_report?.status==='blocked')throw new Error(r.error||r.editorial_report?.errors?.join(' ')||'Automatic edit failed');setMessage(`Saved next iteration: ${r.project?.graphics?.length??0} visuals.`);}catch(e){setError(String(e));setMessage('');}finally{setBusy(false);}}
 return <section aria-label="Give editorial feedback" className="p-4 border-b bg-white shrink-0 max-h-[45vh] overflow-y-auto">
 <h3 className="font-bold">Improve the next edit</h3><p className="text-xs text-neutral-600 mb-2">Select a visual or mark a missing moment. Feedback guides regeneration; it does not immediately change the timeline.</p>
 <div className="flex flex-wrap gap-2"><select aria-label="Feedback target" value={target} disabled={busy} onChange={e=>{setTarget(e.target.value);setDirty(true);}} className="border rounded p-2 max-w-full"><option value="moment">Missing visual / specific moment</option>{project.graphics.map(g=><option key={g.id} value={g.id}>{g.start.toFixed(1)}–{g.end.toFixed(1)}s · {g.title||g.template_id}</option>)}</select>
 <select aria-label="Feedback decision" value={decision} disabled={busy} onChange={e=>{setDecision(e.target.value as typeof decision);setDirty(true);}} className="border rounded p-2"><option value="swap">Change / add</option><option value="keep">Keep this approach</option><option value="cut">Avoid this choice</option></select>
 {!graphic&&<><label>Start (s) <input aria-label="Feedback start seconds" type="number" step="0.1" value={start} onChange={e=>{setStart(Number(e.target.value));setDirty(true);}} className="border w-20 p-2"/></label><label>End (s) <input aria-label="Feedback end seconds" type="number" step="0.1" value={end} onChange={e=>{setEnd(Number(e.target.value));setDirty(true);}} className="border w-20 p-2"/></label></>}</div>
 <textarea aria-label="Feedback explanation" value={notes} disabled={busy} onChange={e=>{setNotes(e.target.value);setDirty(true);setMessage('');}} placeholder="What is wrong and why? What should appear instead?" className="border rounded w-full p-2 mt-2" rows={2}/>
 <div className="flex gap-2 flex-wrap"><button onClick={save} disabled={busy} className="px-3 py-2 bg-purple-700 text-white rounded disabled:opacity-50">Save feedback</button><button onClick={iterate} disabled={busy||dirty} className="px-3 py-2 bg-neutral-900 text-white rounded disabled:opacity-50">Create next iteration</button></div>
 {dirty&&<p className="text-xs mt-1">Save feedback before creating the next iteration.</p>}{message&&<p role="status" className="text-sm mt-2 text-emerald-800">{message}</p>}{error&&<p role="alert" className="text-sm mt-2 text-red-700">{error}</p>}</section>;
}
