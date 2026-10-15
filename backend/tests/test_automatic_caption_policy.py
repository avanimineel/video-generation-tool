from app.core.models import CaptionItem,CaptionStyle
from app.services.automatic_captions import layout_automatic_captions

def test_three_word_groups_keep_all_text_static_and_same_size():
    caps=[CaptionItem(id='a',start=0,end=2,text='पहला हिस्सा',translated_text='These are the first five',style=CaptionStyle(has_highlight=True,has_keyword_emphasis=True,animation_type='bounce')),CaptionItem(id='b',start=2,end=4,text='अगला',translated_text='words and these are more words today')]
    result=layout_automatic_captions(caps)
    assert all(len(c.translated_text.split())==3 for c in result)
    assert ' '.join(c.translated_text for c in result)=='These are the first five words and these are more words today'
    assert len({c.style.font_size for c in result})==1
    assert all(not c.style.has_highlight and not c.style.has_keyword_emphasis and c.style.animation_type=='none' for c in result)
    assert all(c.timing_basis=='translated_estimate' for c in result)
    assert caps[0].style.has_highlight # Does not mutate source audit.

def test_short_ending_is_not_padded_with_fabricated_words():
    result=layout_automatic_captions([CaptionItem(id='a',start=0,end=2,text='Do not invent words')])
    assert [c.translated_text for c in result]==['Do not invent','words']

def test_spoken_numbers_are_not_split_across_subtitles():
    from app.services.transcription_service import join_number_fragments
    words=[dict(word=w,start=s,end=e) for w,s,e in (('with',2.36,2.7),('3',2.7,3.14),(',000,',3.14,3.52),('5',3.6,3.76),(',000,',3.76,4.14),('10',4.22,4.34),(',000,',4.34,4.72),('costs',4.8,5.0),('2',5.0,5.1),('.5',5.1,5.3),('yes',5.3,5.5),(',',5.5,5.6))]
    result=join_number_fragments(words)
    assert [w['word'] for w in result]==['with','3,000,','5,000,','10,000,','costs','2.5','yes',',']
    assert (result[1]['start'],result[1]['end'])==(2.7,3.52)
    assert words[1]['word']=='3' # Input is not mutated.
