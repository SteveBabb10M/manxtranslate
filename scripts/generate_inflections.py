#!/usr/bin/env python3
"""
generate_inflections.py — Generate verb conjugation inflections and noun genitives
from Kelly's Grammar patterns + Scannell focloir stems + Wheeler genitive study.

Outputs SQL INSERT statements for the inflections table.
Can also be imported and called from build_all.py.
"""

import re
import os
import sqlite3
import sys

# ─── LENITION RULES (from Scannell's leniter.pl) ───
def lenite(word):
    """Apply Manx lenition to a word."""
    if not word:
        return word
    
    w = word
    # Order matters — match longest prefix first
    rules = [
        # b/m -> v (bw/mw -> v)
        (r'^[bm]w?', 'v'),
        (r'^[BM]w?', 'V'),
        # ch -> h
        (r'^[cç]h', 'h'),
        (r'^[CÇ]h', 'H'),
        # c/k (not before h) -> ch
        (r'^[ck]([^h])', r'ch\1'),
        (r'^[CK]([^h])', r'Ch\1'),
        # g before e/i -> y
        (r'^g([ei])', r'y\1'),
        (r'^G([ei])', r'Y\1'),
        # g (not before h/i) -> gh
        (r'^g([^hi])', r'gh\1'),
        (r'^G([^hi])', r'Gh\1'),
        # p (not before h) -> ph
        (r'^p([^h])', r'ph\1'),
        (r'^P([^h])', r'Ph\1'),
        # qu -> wh
        (r'^qu', 'wh'),
        (r'^Qu', 'Wh'),
        # sl/shl -> l
        (r'^sh?l', 'l'),
        (r'^Sh?l', 'L'),
        # sn -> n
        (r'^sn', 'n'),
        (r'^Sn', 'N'),
        # str -> hr
        (r'^str', 'hr'),
        (r'^Str', 'Hr'),
        # s/sh before vowel -> h
        (r'^sh?([aeiouy])', r'h\1'),
        (r'^Sh?([aeiouy])', r'H\1'),
        # j -> y
        (r'^j', 'y'),
        (r'^J', 'Y'),
        # t/th -> h
        (r'^th?', 'h'),
        (r'^Th?', 'H'),
        # d/dh -> gh
        (r'^dh?', 'gh'),
        (r'^Dh?', 'Gh'),
        # f -> (disappears)
        (r'^[Ff]', ''),
    ]
    
    for pattern, replacement in rules:
        new_w = re.sub(pattern, replacement, w)
        if new_w != w:
            return new_w
    return w


# ─── ECLIPSIS RULES ───
def eclipsis(word):
    """Apply Manx eclipsis (nasalisation) to a word."""
    if not word:
        return word
    rules = [
        (r'^[bB]', 'm'),
        (r'^[cCkK]', 'g'),
        (r'^[dD]', 'n'),
        (r'^[fF]', 'v'),
        (r'^[gG]', 'n'),  # ng in some contexts
        (r'^[jJ]', 'y'),
        (r'^[pP]', 'b'),
        (r'^[tT]', 'd'),
    ]
    for pattern, replacement in rules:
        new_w = re.sub(pattern, replacement, word)
        if new_w != word:
            return new_w
    return word


# ─── REGULAR VERB CONJUGATION ───
# Based on Kelly's Grammar Ch.13 paradigm patterns:
#   coayl/chaill/caillee, screeu/screeu/screeuee, 
#   giu/diu/iuee, ginsh/dinsh/inshee, kionnaghey/chionnee/kionnee
#   gymmyrkey/dymmyrk/ymmyrkee

def conjugate_regular(stem, verbal_noun=None):
    """
    Generate full paradigm for a regular Manx verb.
    Returns list of (inflected_form, inflection_type, notes) tuples.
    
    stem: the verb root from focloir (e.g. 'screeu', 'tilg', 'faag')
    verbal_noun: if known from focloir
    """
    forms = []
    lenited = lenite(stem)
    
    # Past tense (preterimperfect) — lenited stem
    # Kelly: chaill mee, screeu mee, diu mee, dinsh mee
    if lenited != stem:
        forms.append((lenited, 'past', f'past stem (lenited from {stem})'))
    
    # Future — stem + ee (3rd person / general)
    # Kelly: caillee, screeuee, iuee, inshee, kionnee, ymmyrkee
    future = stem + 'ee'
    forms.append((future, 'future', 'future 3sg/general'))
    
    # Future 1sg — stem + ym  
    # Kelly: cailleeym, screeuym, iuym, inshym, kionneeym, ymmyrkym
    future_1sg = stem + 'ym'
    forms.append((future_1sg, 'future_1sg', 'future 1st person singular'))
    
    # Future relative — stem + ys
    # Kelly: chaillys, screeuys, loayrys
    future_rel = stem + 'ys'
    forms.append((future_rel, 'future_relative', 'future relative/habitual'))

    # Conditional 1sg — lenited stem + in
    # Kelly: chaillin, screeuin, iuin, inshin, chionneein, ymmyrkin
    cond_1sg = lenited + 'in'
    forms.append((cond_1sg, 'conditional_1sg', 'conditional 1st person singular'))
    
    # Conditional 3sg/general — lenited stem + agh
    # Kelly: chaillagh, screeuagh, iuagh, inshagh, chionnagh, ymmyrkagh
    cond_3sg = lenited + 'agh'
    forms.append((cond_3sg, 'conditional', 'conditional 3sg/general'))
    
    # Imperative 2sg — bare stem (unlenited)
    # Kelly: caill, screeu, iu, insh, kionnee, ymmyrk
    forms.append((stem, 'imperative_2sg', 'imperative 2nd person singular'))
    
    # Imperative 2pl — stem + jee
    # Kelly: caill-jee, screeu-jee, iu-jee, insh-ee(!), kionnee-jee, ymmyrk-jee
    imp_2pl = stem + '-jee'
    forms.append((imp_2pl, 'imperative_2pl', 'imperative 2nd person plural'))
    
    # Supine/past participle — stem + it or t
    # Kelly: caillit, screeut, iut, inshit, kionnit, ymmyrkit
    if stem.endswith(('ee', 'eu', 'u', 'oo')):
        supine = stem + 't'
    else:
        supine = stem + 'it'
    forms.append((supine, 'supine', 'past participle / supine'))
    
    # Verbal noun (if provided from focloir)
    if verbal_noun and verbal_noun != stem and verbal_noun != '0':
        forms.append((verbal_noun, 'verbal_noun', 'verbal noun'))
    
    # Negative future — cha + eclipsis of stem
    # Kelly: cha gaillym, cha n'iu-ym, cha n'inshym
    neg_stem = eclipsis(stem)
    if neg_stem != stem:
        forms.append((neg_stem, 'negative_stem', f'negative/interrogative stem (eclipsis of {stem})'))
    
    return forms


# ─── IRREGULAR VERBS ───
# Complete paradigms from Kelly's Grammar Ch.13

IRREGULAR_VERBS = {
    'goll': {
        'english': 'to go',
        'verbal_noun': 'goll',
        'forms': [
            ('hie', 'past', 'past tense (all persons)'),
            ('hem', 'future_1sg', 'future 1sg (also hedym)'),
            ('hedym', 'future_1sg', 'future 1sg variant'),
            ('hed', 'future', 'future 2sg/3sg/3pl'),
            ('hemayd', 'future_1pl', 'future 1st person plural'),
            ('raghin', 'conditional_1sg', 'conditional 1sg'),
            ('ragh', 'conditional', 'conditional general'),
            ('immee', 'imperative_2sg', 'imperative 2sg'),
            ('immee-jee', 'imperative_2pl', 'imperative 2pl'),
            ('er ngoll', 'past_participle', 'past participle'),
            ('goll', 'verbal_noun', 'verbal noun'),
            ('immit', 'supine', 'supine (gone)'),
        ]
    },
    'cheet': {
        'english': 'to come',
        'verbal_noun': 'cheet',
        'forms': [
            ('haink', 'past', 'past tense (all persons)'),
            ('higym', 'future_1sg', 'future 1sg'),
            ('hig', 'future', 'future 2sg/3sg/3pl'),
            ('higmayd', 'future_1pl', 'future 1pl'),
            ('harragh', 'conditional', 'conditional general'),
            ('harrin', 'conditional_1sg', 'conditional 1sg'),
            ('tar', 'imperative_2sg', 'imperative 2sg'),
            ('tar-jee', 'imperative_2pl', 'imperative 2pl'),
            ('er jeet', 'past_participle', 'past participle'),
            ('cheet', 'verbal_noun', 'verbal noun'),
            ('jeet', 'supine', 'supine (come)'),
        ]
    },
    'jannoo': {
        'english': 'to do, to make',
        'verbal_noun': 'jannoo',
        'forms': [
            ('ren', 'past', 'past tense (all persons)'),
            ("nee'm", 'future_1sg', 'future 1sg'),
            ('nee', 'future', 'future 2sg/3sg/3pl'),
            ('nee mayd', 'future_1pl', 'future 1pl'),
            ('yinnin', 'conditional_1sg', 'conditional 1sg'),
            ('yinnagh', 'conditional', 'conditional general'),
            ('jean', 'imperative_2sg', 'imperative 2sg'),
            ('jean-jee', 'imperative_2pl', 'imperative 2pl'),
            ("er n'yannoo", 'past_participle', 'past participle'),
            ('jeant', 'supine', 'supine (done/made)'),
        ]
    },
    'cur': {
        'english': 'to put, to give',
        'verbal_noun': 'cur',
        'forms': [
            ('hug', 'past', 'past tense (all persons)'),
            ('verym', 'future_1sg', 'future 1sg'),
            ('ver', 'future', 'future 2sg/3sg/3pl'),
            ('vermayd', 'future_1pl', 'future 1pl'),
            ('verrin', 'conditional_1sg', 'conditional 1sg'),
            ('verragh', 'conditional', 'conditional general'),
            ('cur', 'imperative_2sg', 'imperative 2sg'),
            ('cur-jee', 'imperative_2pl', 'imperative 2pl'),
            ('er goyrt', 'past_participle', 'past participle'),
            ('currit', 'supine', 'supine (put/given)'),
            ('coyrt', 'verbal_noun', 'verbal noun (giving)'),
        ]
    },
    'geddyn': {
        'english': 'to get, to find',
        'verbal_noun': 'geddyn',
        'forms': [
            ('hooar', 'past', 'past tense (all persons)'),
            ('yioym', 'future_1sg', 'future 1sg'),
            ('yiow', 'future', 'future 2sg/3sg/3pl'),
            ('yiow mayd', 'future_1pl', 'future 1pl'),
            ('yiowin', 'conditional_1sg', 'conditional 1sg'),
            ('yiogh', 'conditional', 'conditional general'),
            ('fow', 'imperative_2sg', 'imperative 2sg'),
            ('fow-jee', 'imperative_2pl', 'imperative 2pl'),
            ('er gheddyn', 'past_participle', 'past participle'),
            ('feddynit', 'supine', 'supine (got/found)'),
        ]
    },
    'clashtyn': {
        'english': 'to hear',
        'verbal_noun': 'clashtyn',
        'forms': [
            ('cheayll', 'past', 'past tense (all persons)'),
            ('chluin', 'past', 'past tense variant (all persons)'),
            ('cluinym', 'future_1sg', 'future 1sg'),
            ('cluinee', 'future', 'future 2sg/3sg/3pl'),
            ('cluinee mayd', 'future_1pl', 'future 1pl'),
            ('chluinin', 'conditional_1sg', 'conditional 1sg'),
            ('chluinagh', 'conditional', 'conditional general'),
            ('clasht', 'imperative_2sg', 'imperative 2sg'),
            ('clasht-jee', 'imperative_2pl', 'imperative 2pl'),
            ('er chlashtyn', 'past_participle', 'past participle'),
            ('cluinit', 'supine', 'supine (heard)'),
        ]
    },
    'gra': {
        'english': 'to say',
        'verbal_noun': 'gra',
        'forms': [
            ('dooyrt', 'past', 'past tense (all persons)'),
            ('jirym', 'future_1sg', 'future 1sg'),
            ('jir', 'future', 'future 2sg/3sg/3pl'),
            ('jir mayd', 'future_1pl', 'future 1pl'),
            ('yiarrin', 'conditional_1sg', 'conditional 1sg'),
            ('yiarragh', 'conditional', 'conditional general'),
            ('abbyr', 'imperative_2sg', 'imperative 2sg'),
            ('abbyr-jee', 'imperative_2pl', 'imperative 2pl'),
            ('er ghra', 'past_participle', 'past participle'),
            ('grait', 'supine', 'supine (said)'),
        ]
    },
    'fakin': {
        'english': 'to see',
        'verbal_noun': 'fakin',
        'forms': [
            ('honnick', 'past', 'past tense (all persons)'),
            ('heeym', 'future_1sg', 'future 1sg'),
            ('hee', 'future', 'future 2sg/3sg/3pl'),
            ('hee mayd', 'future_1pl', 'future 1pl'),
            ('heein', 'conditional_1sg', 'conditional 1sg'),
            ('heeagh', 'conditional', 'conditional general'),
            ('faik', 'imperative_2sg', 'imperative 2sg'),
            ('faik-jee', 'imperative_2pl', 'imperative 2pl'),
            ('er vakin', 'past_participle', 'past participle'),
            ('fakinit', 'supine', 'supine (seen)'),
        ]
    },
    'goaill': {
        'english': 'to take',
        'verbal_noun': 'goaill',
        'forms': [
            ('ghow', 'past', 'past tense (all persons)'),
            ('goym', 'future_1sg', 'future 1sg'),
            ('gowee', 'future', 'future 2sg/3sg/3pl'),
            ('gowee mayd', 'future_1pl', 'future 1pl'),
            ('ghowin', 'conditional_1sg', 'conditional 1sg'),
            ('ghogh', 'conditional', 'conditional general'),
            ('gow', 'imperative_2sg', 'imperative 2sg'),
            ('gow-jee', 'imperative_2pl', 'imperative 2pl'),
            ('er ghoaill', 'past_participle', 'past participle'),
            ('goit', 'supine', 'supine (taken)'),
        ]
    },
    'roshtyn': {
        'english': 'to reach, to arrive',
        'verbal_noun': 'roshtyn',
        'forms': [
            ('raink', 'past', 'past tense (all persons)'),
            ('roshtyn', 'verbal_noun', 'verbal noun'),
        ]
    },
}


# ─── PARSE FOCLOIR VERB STEMS ───
def load_focloir_verbs(focloir_path):
    """Load verb stems and verbal nouns from Scannell's focloir.txt"""
    verbs = []
    seen = set()
    with open(focloir_path) as f:
        for line in f:
            parts = line.strip().split('\t')
            if not parts or not parts[0].endswith('_v'):
                continue
            stem = parts[0].replace('_v', '')
            # Clean verbal noun from second column
            vn = None
            if len(parts) > 1 and parts[1] != '0':
                vn = parts[1]
                # Strip POS suffixes
                vn = re.sub(r'_[a-z]+$', '', vn)
            
            # Check for variant pointer in column 4
            variant_of = None
            if len(parts) > 3 and parts[3] != '0':
                variant_of = re.sub(r'_[a-z]+$', '', parts[3])
            
            if stem not in seen and not variant_of:
                verbs.append((stem, vn))
                seen.add(stem)
    
    return verbs


# ─── WHEELER GENITIVE CASE PARSER ───
def parse_wheeler_genitives(filepath):
    """
    Parse Wheeler's Genitive Case study to extract genitive forms.
    The file contains tab-separated tables for each genitive class:
      Class A (-ey), Class B (-ee), Class C (-agh), Class D (stem change), Class E (irregular)
    Format: singular\tgenitive\tm/f\tgloss\tpl_class\tN_class
    Returns list of (base_form, genitive_form, gen_class, notes) tuples.
    """
    if not os.path.exists(filepath):
        print(f"  Wheeler genitive file not found: {filepath}")
        return []
    
    with open(filepath, encoding='utf-8-sig') as f:
        text = f.read()
    
    genitives = []
    
    # Find each class section by its header and parse tab-separated data
    class_patterns = [
        ('A', r'Class A\.\s*Genitive in -ey'),
        ('B', r'Class B\.\s*Genitive in -ee'),
        ('C', r'Class C\.\s*Gen(?:itive|der) in -agh'),
        ('D', r'Class D\.\s*Genitive with stem'),
        ('E', r'Class E\.\s*Irregular genitive'),
    ]
    
    # Find start positions for each class
    positions = []
    for cls, pattern in class_patterns:
        m = re.search(pattern, text)
        if m:
            positions.append((cls, m.start()))
    
    # Sort by position and add end boundary
    positions.sort(key=lambda x: x[1])
    
    for i, (cls, start) in enumerate(positions):
        end = positions[i + 1][1] if i + 1 < len(positions) else len(text)
        chunk = text[start:end]
        lines = chunk.split('\n')
        
        for line in lines:
            line = line.strip().replace('\r', '')
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            
            nom = parts[0].strip()
            gen = parts[1].strip()
            
            # Skip headers, empty lines, class labels
            if not nom or not gen:
                continue
            if nom.startswith(('Singular', 'Class', 'Nom')):
                continue
            if gen.startswith(('Genitive', 'Gen.')):
                continue
            if gen in ('m', 'f', 'tf', ''):
                continue
            # Skip if nom looks like a header fragment
            if len(nom) < 2:
                continue
            
            # Extract gender and gloss
            gender = parts[2].strip() if len(parts) >= 3 else ''
            gloss = parts[3].strip() if len(parts) >= 4 else ''
            
            # Handle variant forms (e.g. "binjey ~ binshey")
            gen_forms = [g.strip() for g in re.split(r'\s*~\s*', gen)]
            # Strip (K) markers (= from Kelly/Cregeen only)
            gen_forms = [re.sub(r'\s*\(K\)\s*', '', g).strip() for g in gen_forms]
            
            for gf in gen_forms:
                if gf and len(gf) > 1:
                    notes_parts = []
                    if gloss:
                        notes_parts.append(f"'{gloss}'")
                    if gender:
                        notes_parts.append(f"gender: {gender}")
                    notes_parts.append(f"genitive class {cls}")
                    
                    genitives.append((nom, gf, f'Wheeler_class_{cls}', ', '.join(notes_parts)))
    
    # Deduplicate
    seen = set()
    unique = []
    for base, gen, src, notes in genitives:
        key = (base.lower(), gen.lower())
        if key not in seen:
            seen.add(key)
            unique.append((base, gen, src, notes))
    
    return unique


# ─── MAIN: GENERATE AND INSERT ───
def generate_all_inflections(db_path, focloir_path, genitive_path=None):
    """Generate all inflections and insert into database."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get existing inflections to avoid duplicates
    existing = set()
    for row in cursor.execute('SELECT base_form, inflected_form, inflection_type FROM inflections'):
        existing.add((row[0].lower(), row[1].lower(), row[2].lower()))
    
    print(f"Existing inflections: {len(existing)}")
    
    new_entries = []
    
    # ── 1. IRREGULAR VERBS ──
    print("\n=== Irregular Verbs (Kelly's Grammar) ===")
    for lemma, data in IRREGULAR_VERBS.items():
        for form, infl_type, notes in data['forms']:
            key = (lemma.lower(), form.lower(), infl_type.lower())
            if key not in existing:
                new_entries.append((lemma, form, infl_type, 'verb', 'irregular', 
                                   f"Kelly Grammar: {data['english']}. {notes}"))
                existing.add(key)
    print(f"  Irregular verb forms: {len([e for e in new_entries if e[4] == 'irregular'])}")
    
    # ── 2. REGULAR VERBS ──
    print("\n=== Regular Verbs (focloir stems + Kelly paradigm) ===")
    irregular_stems = set(IRREGULAR_VERBS.keys())
    # Also exclude stems that are variants of irregulars
    irregular_all = set()
    for lemma, data in IRREGULAR_VERBS.items():
        irregular_all.add(lemma)
        for form, _, _ in data['forms']:
            irregular_all.add(form.split()[0])  # first word of multi-word forms
    
    verbs = load_focloir_verbs(focloir_path)
    regular_count = 0
    for stem, vn in verbs:
        if stem in irregular_stems:
            continue
        
        forms = conjugate_regular(stem, vn)
        for form, infl_type, notes in forms:
            key = (stem.lower(), form.lower(), infl_type.lower())
            if key not in existing:
                new_entries.append((stem, form, infl_type, 'verb', 'regular',
                                   f"Generated from Kelly paradigm. {notes}"))
                existing.add(key)
                regular_count += 1
    
    print(f"  Regular verb forms generated: {regular_count}")
    print(f"  From {len(verbs)} stems ({len(verbs) - len(irregular_stems)} regular)")
    
    # ── 3. WHEELER GENITIVES ──
    if genitive_path and os.path.exists(genitive_path):
        print("\n=== Wheeler Genitive Forms ===")
        genitives = parse_wheeler_genitives(genitive_path)
        gen_count = 0
        for base, gen, src, notes in genitives:
            key = (base.lower(), gen.lower(), 'genitive')
            if key not in existing:
                new_entries.append((base, gen, 'genitive', 'noun', src,
                                   f"Wheeler Genitive Case study. {notes}"))
                existing.add(key)
                gen_count += 1
        print(f"  Genitive forms extracted: {gen_count}")
    
    # ── INSERT ──
    print(f"\n=== Inserting {len(new_entries)} new inflections ===")
    cursor.executemany(
        'INSERT INTO inflections (base_form, inflected_form, inflection_type, part_of_speech, pattern_class, notes) VALUES (?, ?, ?, ?, ?, ?)',
        new_entries
    )
    conn.commit()
    
    # Report totals
    total = cursor.execute('SELECT COUNT(*) FROM inflections').fetchone()[0]
    print(f"  Total inflections now: {total}")
    
    # Breakdown
    print("\n  Breakdown by type:")
    for row in cursor.execute('SELECT inflection_type, COUNT(*) FROM inflections GROUP BY inflection_type ORDER BY COUNT(*) DESC'):
        print(f"    {row[0]:25s} {row[1]:>6d}")
    
    conn.close()
    return len(new_entries)


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(base_dir)  # scripts/ -> repo root
    
    db_path = os.path.join(repo_dir, 'data', 'processed', 'manx.db')
    focloir_path = os.path.join(repo_dir, 'data', 'scannell', 'focloir.txt')
    genitive_path = os.path.join(repo_dir, 'data', 'raw', 'Genitive_case.txt')
    
    # Allow override from command line
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    if len(sys.argv) > 2:
        focloir_path = sys.argv[2]
    if len(sys.argv) > 3:
        genitive_path = sys.argv[3]
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)
    
    generate_all_inflections(db_path, focloir_path, genitive_path)
