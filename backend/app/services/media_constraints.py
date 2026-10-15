"""Source-metadata requirements run before model-based visual relevance review."""
import re
from urllib.parse import unquote

def evidence_rejection(candidate, row):
    asset=row.get('asset',{})
    context=' '.join(str(v) for v in (row.get('semantic_context',{}).get('transcript',''), row.get('rationale',''), asset.get('required_environment',''), asset.get('retrieval_query',''))).casefold()
    metadata=' '.join(str(candidate.get(k,'')) for k in ('title','description','location','source_url','author_url','url')).casefold()
    metadata=unquote(metadata).replace('-', ' ').replace('_',' ')
    if re.search(r'\b(india|indian|bharat)\b|भारत',context):
        locations=r'\b(india|indian|bharat|delhi|mumbai|kolkata|chennai|bengaluru|bangalore|gujarat|uttar pradesh|madhya pradesh|mizoram|varanasi|gwalior|assam|kerala|rajasthan|maharashtra|punjab|bihar|hyderabad)\b|भारत'
        if not re.search(locations,metadata):
            return 'Indian setting requested, but candidate source metadata does not document it.'
    if row.get('intent')=='IDENTIFY' or row.get('visual_role') in ('identity','evidence'):
        required=asset.get('required_entities',[])
        if not required:
            return 'Identity visual has no named subject requirement.'
        for name in required:
            parts=re.findall(r'\w+',str(name).casefold())
            if parts and not all(re.search(r'(?<!\w)'+re.escape(part)+r'(?!\w)',metadata) for part in parts):
                return 'Source metadata does not identify required subject: '+str(name)
    return None
