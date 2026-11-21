"""Source-metadata requirements run before model-based visual relevance review.

There is no country or city list here. A place or person is required only when
this video's brief marks the visual as identity or evidence and names that subject.
"""
import re
from urllib.parse import unquote

def evidence_rejection(candidate, row):
    asset=row.get('asset',{})
    metadata=' '.join(str(candidate.get(k,'')) for k in ('title','description','location','source_url','author_url','url')).casefold()
    metadata=unquote(metadata).replace('-', ' ').replace('_',' ')
    if row.get('intent')=='IDENTIFY' or row.get('visual_role') in ('identity','evidence'):
        required=asset.get('required_entities',[])
        if not required:
            return 'Identity visual has no named subject requirement.'
        for name in required:
            parts=re.findall(r'\w+',str(name).casefold())
            if parts and not all(re.search(r'(?<!\w)'+re.escape(part)+r'(?!\w)',metadata) for part in parts):
                return 'Source metadata does not identify required subject: '+str(name)
    return None
