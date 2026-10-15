import {useEffect, useState} from 'react';
import {api} from '../../services/api';

export function QualityPreview({projectId}:{projectId:string}) {
  const [open,setOpen]=useState(false),[job,setJob]=useState<any>(null),[error,setError]=useState('');
  useEffect(()=>{
    setJob(null);setError('');
    if(!open)return;
    let alive=true;
    const refresh=async()=>{try{const result=await api.qualityPreview(projectId);if(alive)setJob(result)}catch(e){if(alive)setError(String(e))}};
    void refresh();const timer=setInterval(refresh,2500);
    return()=>{alive=false;clearInterval(timer)};
  },[projectId,open]);
  const create=async()=>{setError('');try{setJob(await api.qualityPreview(projectId,true))}catch(e){setError(String(e))}};
  const url=job?.revision?api.qualityVideoUrl(projectId,job.revision):'';
  return <><button onClick={()=>setOpen(true)} className="px-3 py-1 rounded bg-teal-800 text-white">Documentary style preview</button>
    {open&&<div className="fixed inset-0 z-[110] bg-black/50 flex items-center justify-center p-5"><section role="dialog" aria-modal="true" aria-label="Documentary style preview" className="bg-white rounded-xl p-5 max-w-3xl w-full max-h-[95vh] overflow-auto text-neutral-900">
      <header className="flex justify-between items-center"><h2 className="text-lg font-semibold">A cleaner, more deliberate edit</h2><button onClick={()=>setOpen(false)} className="border rounded px-3 py-1">Close</button></header>
      <p className="text-sm text-neutral-600 my-3">The first 30 seconds, rendered at 1080p. Consistent phrase captions, restrained camera movement, and distinct concept cards. Your saved timeline stays intact.</p>
      {error&&<p role="alert" className="text-red-700">{error}</p>}
      {job?.error&&<p role="alert" className="text-red-700">{job.error}</p>}
      {job?.status==='complete'&&<video key={url} src={url} controls playsInline preload="metadata" className="mx-auto bg-neutral-950 rounded-lg" style={{maxHeight:'62vh',maxWidth:'100%'}}/>}
      {job?.status==='rendering'&&<div className="my-6"><p>Rendering your preview… {job.percent}%</p><progress value={job.percent} max={100} className="w-full"/></div>}
      <div className="flex items-center gap-4 mt-4"><button disabled={job?.status==='rendering'} onClick={create} className="bg-teal-800 text-white px-4 py-2 rounded disabled:opacity-50">{job?.status==='complete'?'Preview latest saved edit':'Create style preview'}</button>{job?.status==='complete'&&<a href={url} download className="text-teal-800 underline">Download this MP4</a>}</div>
      <p className="text-xs text-neutral-500 mt-3">Preview and download use the same rendered video. English phrase timing is estimated from the existing translation; this preview does not add verified research or new stock footage.</p>
    </section></div>}
  </>;
}
