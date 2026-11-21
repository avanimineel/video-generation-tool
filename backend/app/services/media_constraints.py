"""Source-metadata requirements run before model-based visual relevance review."""
import re
from urllib.parse import unquote

def evidence_rejection(candidate, row):
    asset=row.get('asset',{})
    # An illustration of a lung or a medicine is not an India shot just because
    # the surrounding sentence mentions India. Require Indian metadata only when
    # the requested picture asks for it, or the visual is identity/evidence.
    picture=' '.join(str(v) for v in (
        asset.get('required_environment',''), asset.get('retrieval_query',''),
        asset.get('semantic_target',''), asset.get('desired_visual_description',''),
        ' '.join(asset.get('alternate_queries') or []),
    ))
    if row.get('visual_role') in ('identity','evidence') or row.get('intent')=='IDENTIFY':
        picture += ' ' + str((row.get('semantic_context') or {}).get('transcript',''))
    context=picture.casefold()
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
