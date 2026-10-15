STYLES = ('editorial', 'rise', 'script', 'dual', 'typewriter', 'staircase', 'paper', 'bold_pop', 'behind_subject', 'flame_subject', 'cooked_badge', 'cards_broll', 'mixed_typography')

TRAILING_STOP_WORDS = {
    'and', 'the', 'of', 'to', 'is', 'a', 'an', 'which', 'with', 'for', 'in',
    'that', 'it', 'as', 'at', 'by', 'from', 'or', 'so', 'are', 'was', 'were', 'be', 'this'
}

NUMBER_WORDS = set('one two three four five six seven eight nine ten eleven twelve twenty thirty forty fifty hundred thousand lakh million crore billion'.split())
PLAIN_WORDS = TRAILING_STOP_WORDS | set('i you we he she they my your our his her their them me us not no do does did can will would should have has had just only very really there here what when how why who if but then than into about on up out all more most'.split())


def accent_words(words):
    """The word(s) a title turns on: every number, otherwise the one strongest content word."""
    clean = [''.join(c for c in w.casefold() if c.isalnum()) for w in words]
    numbers = [w for w in clean if w and (any(c.isdigit() for c in w) or w in NUMBER_WORDS)]
    if numbers: return numbers
    content = [w for w in clean if w and w not in PLAIN_WORDS]
    return [max(content, key=len)] if content and len(clean) > 1 else content[:1]


def split_mixed_typography(words, timed_words=None):
    """Split title into setup_text (geometric bold sans) and accent_text (emotional punchword, 1-3 words)."""
    if not words:
        return "", ""
    if len(words) == 1:
        return "", words[0]
    if len(words) == 2:
        return words[0].upper(), words[1]

    acc = accent_words(words)
    clean_words = [''.join(c for c in w.casefold() if c.isalnum()) for w in words]
    clean_acc = set(acc)

    idx = -1
    for i, cw in enumerate(clean_words):
        if cw in clean_acc:
            idx = i
            break

    if idx != -1:
        if idx >= len(words) // 2:
            start_accent = max(1, idx)
            if len(words) - start_accent > 3:
                start_accent = len(words) - 2
            setup = ' '.join(words[:start_accent]).upper()
            accent = ' '.join(words[start_accent:])
        else:
            end_accent = min(len(words) - 1, idx + 1)
            accent = ' '.join(words[:end_accent])
            setup = ' '.join(words[end_accent:]).upper()
    else:
        split_point = max(1, len(words) - (2 if len(words) >= 4 else 1))
        setup = ' '.join(words[:split_point]).upper()
        accent = ' '.join(words[split_point:])

    return setup, accent


def editorial_lines(timed_words):
    """Short stacked lines, as a hand-set title: at most three words or about thirteen characters each."""
    lines, current = [], []
    for tw in timed_words:
        text = ' '.join(w['text'] for w in current + [tw])
        if current and (len(current) >= 3 or len(text) > 13):
            lines.append(current); current = []
        current.append(tw)
    if current: lines.append(current)
    return [{'text': ' '.join(w['text'] for w in line), 'offset': line[0]['offset']} for line in lines]


def arrange_title(graphic, style, captions=None):
    text = graphic.parameters.get('headline') or graphic.title
    
    # 1. Exact Word-by-Word Timing from Spoken Captions
    timed_words = []
    if captions:
        g_start = float(graphic.start)
        g_end = float(graphic.end)
        
        # Collect candidate spoken words strictly within [g_start - 0.08, g_end + 0.08]
        raw_words = []
        for cap in captions:
            words_list = getattr(cap, 'words', []) or []
            if words_list:
                for w in words_list:
                    w_txt = getattr(w, 'word', '') or ''
                    w_start = float(getattr(w, 'start', cap.start))
                    w_end = float(getattr(w, 'end', cap.end))
                    if w_txt.strip() and w_start >= (g_start - 0.12) and w_start < (g_end + 0.10):
                        raw_words.append({
                            'text': w_txt.strip(),
                            'start': w_start,
                            'end': w_end,
                            'offset': round(max(0.0, w_start - g_start), 3),
                            'duration': round(max(0.12, w_end - w_start), 3)
                        })
            elif getattr(cap, 'text', '') and cap.start < (g_end + 0.10) and cap.end > (g_start - 0.10):
                cap_words = cap.text.split()
                if cap_words:
                    step = (cap.end - cap.start) / max(1, len(cap_words))
                    for idx, cw in enumerate(cap_words):
                        w_s = cap.start + idx * step
                        w_e = w_s + step
                        if w_s >= (g_start - 0.12) and w_s < (g_end + 0.10):
                            raw_words.append({
                                'text': cw.strip(),
                                'start': w_s,
                                'end': w_e,
                                'offset': round(max(0.0, w_s - g_start), 3),
                                'duration': round(max(0.12, step), 3)
                            })

        # Filter: Respect sentence boundary and stop punctuation
        # If a word ends with '.', '?', '!' and we have at least 3 words, terminate to prevent next sentence spillover
        for i, rw in enumerate(raw_words):
            timed_words.append(rw)
            clean_token = rw['text'].rstrip('",\';')
            if clean_token.endswith(('.', '?', '!')) and len(timed_words) >= 3:
                # Stop if there's a subsequent gap or next word starts with capital letter (new sentence)
                if i + 1 < len(raw_words):
                    next_w = raw_words[i+1]['text']
                    if next_w and (next_w[0].isupper() or raw_words[i+1]['start'] - rw['end'] > 0.25):
                        break

        # Trim trailing conjunctions, prepositions, and connector words (e.g. "cover it. And", "companies. The same is the")
        while len(timed_words) > 2:
            last_text = timed_words[-1]['text'].strip()
            # If the last word has terminal punctuation, keep it as the clean complete sentence end
            if last_text.endswith(('.', '!', '?')):
                break
            last_clean = last_text.lower().rstrip('.,!?:;')
            if last_clean in TRAILING_STOP_WORDS:
                timed_words.pop()
            else:
                break

    # Preserve the authored headline. Align matching words in sequence; label estimates.
    import re
    norm = lambda word: re.sub(r'[^\w]', '', word).casefold()
    source_words = timed_words
    timed_words = []
    cursor = 0
    words = text.split()
    total_dur = max(.6, float(graphic.end) - float(graphic.start))
    for i, word in enumerate(words):
        match = next((j for j in range(cursor, len(source_words)) if norm(source_words[j]['text']) == norm(word)), None)
        if match is not None:
            tw = dict(source_words[match], text=word, timing='aligned')
            cursor = match + 1
        else:
            offset = i * total_dur * .65 / max(1, len(words))
            tw = dict(text=word, offset=round(offset,3), duration=.18, timing='estimated', start=graphic.start+offset, end=graphic.start+offset+.18)
        if timed_words: tw['offset'] = max(tw['offset'], timed_words[-1]['offset'])
        timed_words.append(tw)

    graphic.parameters['timed_words'] = timed_words
    words = [tw['text'] for tw in timed_words]
    if not words: return

    # Layout multi-line groupings according to chosen style
    if style == 'editorial':
        lines = editorial_lines(timed_words)
        graphic.parameters['accent_words'] = accent_words(words)
    elif style == 'staircase':
        lines = [{'text': tw['text'], 'offset': tw['offset']} for tw in timed_words]
    elif style == 'dual' and len(timed_words) > 1:
        split = max(1, len(timed_words) // 2)
        lines = [
            {'text': ' '.join(tw['text'] for tw in timed_words[:split]), 'offset': timed_words[0]['offset']},
            {'text': ' '.join(tw['text'] for tw in timed_words[split:]), 'offset': timed_words[split]['offset']}
        ]
    elif style == 'behind_subject':
        if graphic.pos_y == .5: graphic.pos_y = .19
        if len(timed_words) >= 4:
            s1 = len(timed_words) // 3
            s2 = 2 * len(timed_words) // 3
            lines = [
                {'text': ' '.join(tw['text'] for tw in timed_words[:s1]), 'offset': timed_words[0]['offset']},
                {'text': ' '.join(tw['text'] for tw in timed_words[s1:s2]), 'offset': timed_words[s1]['offset']},
                {'text': ' '.join(tw['text'] for tw in timed_words[s2:]), 'offset': timed_words[s2]['offset']}
            ]
        elif len(timed_words) >= 2:
            split = max(1, len(timed_words) // 2)
            lines = [
                {'text': ' '.join(tw['text'] for tw in timed_words[:split]), 'offset': timed_words[0]['offset']},
                {'text': ' '.join(tw['text'] for tw in timed_words[split:]), 'offset': timed_words[split]['offset']},
                {'text': '', 'offset': timed_words[-1]['offset']}
            ]
        else:
            lines = [{'text': text, 'offset': 0}]
    elif style == 'cards_broll':
        if len(timed_words) >= 3:
            lines = [
                {'text': timed_words[0]['text'], 'offset': timed_words[0]['offset']},
                {'text': ' '.join(tw['text'] for tw in timed_words[1:-1]), 'offset': timed_words[1]['offset']},
                {'text': timed_words[-1]['text'], 'offset': timed_words[-1]['offset']}
            ]
        elif len(timed_words) == 2:
            lines = [
                {'text': timed_words[0]['text'], 'offset': timed_words[0]['offset']},
                {'text': timed_words[1]['text'], 'offset': timed_words[1]['offset']}
            ]
        else:
            lines = [{'text': text, 'offset': 0}]
    elif style == 'cooked_badge' and len(timed_words) > 1:
        lines = [
            {'text': timed_words[0]['text'], 'offset': timed_words[0]['offset']},
            {'text': ' '.join(tw['text'] for tw in timed_words[1:]), 'offset': timed_words[1]['offset']}
        ]
    elif style == 'paper':
        if len(timed_words) > 1:
            lines = [
                {'text': ' '.join(tw['text'] for tw in timed_words[:-1]), 'offset': timed_words[0]['offset']},
                {'text': timed_words[-1]['text'], 'offset': timed_words[-1]['offset']}
            ]
        else:
            lines = [{'text': text, 'offset': 0}]
    elif style == 'rise' and len(timed_words) > 1:
        split = max(1, len(timed_words) // 2)
        lines = [
            {'text': ' '.join(tw['text'] for tw in timed_words[:split]), 'offset': timed_words[0]['offset']},
            {'text': ' '.join(tw['text'] for tw in timed_words[split:]), 'offset': timed_words[split]['offset']}
        ]
    elif style == 'flame_subject':
        lines = [{'text': text, 'offset': 0}]
        graphic.parameters['flame_effect'] = True
    elif style == 'mixed_typography':
        setup_t = graphic.parameters.get('setup_text')
        accent_t = graphic.parameters.get('accent_text')
        if not setup_t and not accent_t:
            setup_t, accent_t = split_mixed_typography(words, timed_words)
        graphic.parameters['setup_text'] = setup_t
        graphic.parameters['accent_text'] = accent_t
        graphic.parameters.setdefault('setup_color', '#FFFFFF')
        graphic.parameters.setdefault('accent_color', '#E04F26')
        graphic.parameters.setdefault('bounding_box_highlight', True)
        graphic.parameters.setdefault('box_rotation', -3.0)
        lines = [
            {'text': setup_t, 'offset': timed_words[0]['offset'] if timed_words else 0},
            {'text': accent_t, 'offset': timed_words[max(0, len(timed_words)//2)]['offset'] if timed_words else 0}
        ]
    else:
        lines = [{'text': text, 'offset': 0}]

    graphic.parameters.update(title_style=style, title_lines=lines)




def choose_title_style(graphic):
    """Respect explicit treatments; no cycling through effects by timeline index."""
    p=graphic.parameters
    requested=p.get('title_style') or p.get('composition_plan',{}).get('entrance_animation')
    if requested in STYLES:return requested
    if getattr(graphic, 'template_id', '') == 'mixed_typography_title': return 'mixed_typography'
    # One consistent house style; boxed, paper, flame and script looks are opt-in.
    return 'editorial'
