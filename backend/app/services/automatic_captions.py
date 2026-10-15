"""Static three-word English display groups; original-language audit stays separate.
No words are invented to pad the final group. Timing provenance remains explicit.
"""
from app.core.models import CaptionItem, WordTiming

def layout_automatic_captions(captions):
    records=[]
    for cap in sorted(captions,key=lambda c:c.start):
        text=cap.translated_text or cap.text
        words=text.split()
        matched=len(cap.words)==len(words) and [w.word for w in cap.words]==words and all(w.end>w.start for w in cap.words)
        for i,word in enumerate(words):
            timing=cap.words[i].model_copy(deep=True) if matched else WordTiming(word=word,start=cap.start+(cap.end-cap.start)*i/len(words),end=cap.start+(cap.end-cap.start)*(i+1)/len(words))
            timing.highlight=False;timing.is_keyword=False;timing.keyword_color=None;timing.keyword_font=None;timing.keyword_category=None
            records.append((timing,cap,not matched or text!=cap.text))
    result=[]
    for i in range(0,len(records),3):
        chunk=records[i:i+3];words=[x[0] for x in chunk]
        parents={x[1].id:x[1] for x in chunk}
        first=chunk[0][1];style=first.style.model_copy(deep=True)
        style.animation_type='none';style.has_highlight=False;style.has_keyword_emphasis=False
        style.highlight_scale=1;style.highlight_bounce=False;style.pacing_mode='full_line';style.max_lines=1
        translated=' '.join(w.word for w in words)
        native=' '.join(p.text for p in parents.values()) if any(x[2] for x in chunk) else translated
        result.append(CaptionItem(id=f'auto3_{i//3}_{first.id}',start=words[0].start,end=words[-1].end,text=native,
            translated_text=translated,words=words,style=style,source_language=first.source_language,
            source_caption_ids=list(parents),timing_basis='translated_estimate' if any(x[2] for x in chunk) else 'asr_estimate',
            pos_x=first.pos_x,pos_y=first.pos_y))
    # Pick one size for the whole automatic subtitle track, never resize by word.
    longest=max((len(c.translated_text) for c in result),default=1)
    size=min(24,max(8,int(280/max(1,longest*.7+1))))
    for c in result:c.style.font_size=size
    return result
