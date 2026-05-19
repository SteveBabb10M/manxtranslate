#!/usr/bin/env python3
"""
Comprehensive DB builder: populates all 6 tables from available sources.
"""
import sqlite3
import re
import json
import os

DB_PATH = '/home/claude/manxtranslate/scripts/manx.db'
GAELG = '/home/claude/gaelg'
CAIGHDEAN = '/home/claude/caighdean'
MANXTXT = '/home/claude/manxtranslate/manxtxt'

conn = sqlite3.connect(DB_PATH)

# ============================================================
# 1. DICTIONARY from gv2ga.po (Manx→Irish) bridged to English
# ============================================================
print("=== 1. DICTIONARY (gv2ga.po) ===")

# Parse POS tags
POS_MAP = {
    '_nm': ('noun', 'm'), '_nf': ('noun', 'f'), '_n': ('noun', None),
    '_v': ('verb', None), '_a': ('adjective', None), '_adv': ('adverb', None),
    '_prep': ('preposition', None), '_conj': ('conjunction', None),
    '_pron': ('pronoun', None), '_det': ('determiner', None),
    '_interj': ('interjection', None), '_num': ('numeral', None),
}

def parse_pos(headword):
    """Extract word and POS from headword like 'aachaarjaghey_nm'"""
    for suffix, (pos, gender) in sorted(POS_MAP.items(), key=lambda x: -len(x[0])):
        if headword.endswith(suffix):
            word = headword[:-(len(suffix))].replace('-', '').replace('_', ' ')
            # Skip numbered variants like word1, word2
            word = re.sub(r'\d+$', '', word)
            return word, pos, gender
    return headword, None, None

# Build a simple Irish→English lookup from pairs-gv.txt approach
# Actually, we'll use the gv2ga.po directly - Manx headword → Irish gloss
# and note that for now we store Irish as the "english" field with a note
# Better: just store the Manx word with POS and gender from the PO file

dict_count = 0
seen_words = set()

with open(os.path.join(GAELG, 'gv2ga.po'), 'r', encoding='utf-8') as f:
    content = f.read()

# Parse PO file
entries = re.findall(r'(?:^#[^\n]*\n)*^msgid "([^"]+)"\nmsgstr "([^"]*)"', content, re.MULTILINE)

for msgid, msgstr in entries:
    if not msgstr or msgstr == msgid:
        continue
    
    manx_word, pos, gender = parse_pos(msgid)
    if not manx_word or len(manx_word) < 2:
        continue
    
    # Parse Irish translations (semicolon separated)
    irish_glosses = [g.strip() for g in msgstr.split(';') if g.strip()]
    
    for gloss in irish_glosses:
        irish_word, irish_pos, _ = parse_pos(gloss)
        if irish_word and len(irish_word) >= 2:
            key = (manx_word, irish_word)
            if key not in seen_words:
                seen_words.add(key)
                conn.execute(
                    "INSERT INTO dictionary (english, manx, part_of_speech, gender, source, notes) VALUES (?,?,?,?,?,?)",
                    (irish_word, manx_word, pos, gender, 'scannell_gv2ga', f'Irish gloss: {gloss}')
                )
                dict_count += 1

conn.commit()
print(f"  Inserted {dict_count:,} dictionary entries")

# ============================================================
# 2. INFLECTIONS from focloir.txt
# ============================================================
print("\n=== 2. INFLECTIONS (focloir.txt) ===")

infl_count = 0
with open(os.path.join(GAELG, 'focloir.txt'), 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) < 4:
            continue
        
        headword = parts[0]
        col2, col3, col4 = parts[1], parts[2], parts[3]
        
        base_word, pos, gender = parse_pos(headword)
        if not base_word or len(base_word) < 2:
            continue
        
        # Col2: for verbs = verbal noun, for nouns = genitive singular
        if col2 and col2 != '0':
            vn_word, _, _ = parse_pos(col2)
            if vn_word and vn_word != base_word:
                if pos == 'verb':
                    conn.execute(
                        "INSERT INTO inflections (base_form, inflected_form, inflection_type, part_of_speech, notes) VALUES (?,?,?,?,?)",
                        (base_word, vn_word, 'verbal_noun', 'verb', f'from focloir.txt')
                    )
                    infl_count += 1
                elif pos == 'noun':
                    conn.execute(
                        "INSERT INTO inflections (base_form, inflected_form, inflection_type, part_of_speech, notes) VALUES (?,?,?,?,?)",
                        (base_word, vn_word, 'genitive', 'noun', f'gender: {gender}')
                    )
                    infl_count += 1
                elif pos == 'adjective':
                    conn.execute(
                        "INSERT INTO inflections (base_form, inflected_form, inflection_type, part_of_speech, notes) VALUES (?,?,?,?,?)",
                        (base_word, vn_word, 'comparative', 'adjective', 'from focloir.txt')
                    )
                    infl_count += 1
        
        # Col3: for nouns = plural; '1' means regular -yn plural
        if col3 and col3 != '0':
            if col3 == '1':
                # Regular -yn plural
                plural = base_word + 'yn'
                conn.execute(
                    "INSERT INTO inflections (base_form, inflected_form, inflection_type, part_of_speech, pattern_class, notes) VALUES (?,?,?,?,?,?)",
                    (base_word, plural, 'plural', 'noun', 'regular_-yn', f'gender: {gender}')
                )
                infl_count += 1
            else:
                pl_word, _, _ = parse_pos(col3)
                if pl_word and pl_word != base_word:
                    conn.execute(
                        "INSERT INTO inflections (base_form, inflected_form, inflection_type, part_of_speech, notes) VALUES (?,?,?,?,?)",
                        (base_word, pl_word, 'plural', 'noun', f'gender: {gender}')
                    )
                    infl_count += 1
        
        # Col4: cross-reference to standard form
        if col4 and col4 != '0':
            ref_word, _, _ = parse_pos(col4)
            if ref_word and ref_word != base_word:
                conn.execute(
                    "INSERT INTO inflections (base_form, inflected_form, inflection_type, part_of_speech, notes) VALUES (?,?,?,?,?)",
                    (ref_word, base_word, 'variant', pos or 'unknown', 'cross-reference in focloir.txt')
                )
                infl_count += 1

conn.commit()
print(f"  Inserted {infl_count:,} inflection entries")

# ============================================================
# 3. PHRASES from multi-gv.txt  
# ============================================================
print("\n=== 3. PHRASES (multi-gv.txt) ===")

phrase_count = 0
with open(os.path.join(CAIGHDEAN, 'multi-gv.txt'), 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split(' ', 1)
        if len(parts) < 2:
            continue
        
        manx_phrase = parts[0].replace('_', ' ')
        irish_phrase = parts[1].strip()
        
        if len(manx_phrase) > 2 and len(irish_phrase) > 1:
            conn.execute(
                "INSERT INTO phrases (english, manx, category, source) VALUES (?,?,?,?)",
                (irish_phrase, manx_phrase, 'multi-word', 'scannell_caighdean')
            )
            phrase_count += 1

conn.commit()
print(f"  Inserted {phrase_count:,} phrases")

# ============================================================
# 4. PARALLEL SENTENCES from UD usage/pairs.txt
# ============================================================
print("\n=== 4. PARALLEL SENTENCES (ud/usage/pairs.txt) ===")

pairs_file = os.path.join(GAELG, 'ud/usage/pairs.txt')
existing = set()
for row in conn.execute("SELECT english, manx FROM parallel_sentences"):
    existing.add((row[0][:50], row[1][:50]))

par_count = 0
current_en = None
manx_tokens = []
irish_tokens = []

with open(pairs_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        
        # Sentence boundary marker
        m = re.match(r'^<div text="(.+?)"/>\s*=>\s*<div text="(.+?)"/>', line)
        if m:
            current_en = m.group(1)
            manx_tokens = []
            irish_tokens = []
            continue
        
        if line == '\\n':
            # End of sentence pair - reconstruct
            if current_en and manx_tokens:
                manx_sent = ' '.join(manx_tokens)
                key = (current_en[:50], manx_sent[:50])
                if key not in existing and len(manx_sent) > 3:
                    conn.execute(
                        "INSERT INTO parallel_sentences (english, manx, source, domain, quality) VALUES (?,?,?,?,?)",
                        (current_en, manx_sent, 'scannell_ud_usage', 'phrasebook', 'curated')
                    )
                    existing.add(key)
                    par_count += 1
            current_en = None
            manx_tokens = []
            irish_tokens = []
            continue
        
        # Token pairs: manx => irish
        parts = line.split(' => ')
        if len(parts) == 2:
            manx_tok = parts[0].strip()
            irish_tok = parts[1].strip()
            if manx_tok and manx_tok not in ('.', ',', '!', '?', ';', ':'):
                manx_tokens.append(manx_tok)
                irish_tokens.append(irish_tok)

conn.commit()
print(f"  Inserted {par_count:,} new parallel sentences")

# ============================================================
# 5. GRAMMAR RULES from Wheeler studies + writing standard
# ============================================================
print("\n=== 5. GRAMMAR RULES ===")

grammar_count = 0

# --- 5a. Lenition rules (from leniter.pl + Wheeler study 6) ---
lenition_rules = [
    ("MUTATION", "LENITION", "b, m → v (bw, mw → v)", "b/m (or bw/mw) lenites to v: *ben* → *ven*, *moar* → *voar*", "leniter.pl + Wheeler"),
    ("MUTATION", "LENITION", "c, k → ch (before non-h)", "*caashey* → *chaashey*, *kione* → *chione*. Note: ch, çh already lenited → h", "leniter.pl + Wheeler"),
    ("MUTATION", "LENITION", "ç → h", "*çheer* → *heer*", "leniter.pl"),
    ("MUTATION", "LENITION", "d → gh (dh → gh)", "*dooinney* → *ghooinney*, *dty* remains *dty*", "leniter.pl + Wheeler"),
    ("MUTATION", "LENITION", "f → zero (f disappears)", "*fer* → *er*, *feer* → *eer*", "leniter.pl + Wheeler"),
    ("MUTATION", "LENITION", "g → gh before a,o,u and non-h consonants; g → y before e,i", "*goll* → *gholl*, *geurey* → *yeurey*", "leniter.pl + Wheeler"),
    ("MUTATION", "LENITION", "j → y", "*jannoo* → *yannoo*", "leniter.pl"),
    ("MUTATION", "LENITION", "p → ph (before non-h)", "*peccah* → *pheccah*", "leniter.pl + Wheeler"),
    ("MUTATION", "LENITION", "qu → wh", "*quoi* → *whoi*", "leniter.pl"),
    ("MUTATION", "LENITION", "s → h before vowels (sh → h); sl → l; sn → n; str → hr", "*shoh* → *hoh*, *slane* → *lane*, *snaie* → *naie*, *stroo* → *hroo*", "leniter.pl + Wheeler"),
    ("MUTATION", "LENITION", "t, th → h", "*thie* → *hie*, *toshiaght* → *hoshiaght*", "leniter.pl + Wheeler"),
]

for cat, subcat, rule, examples, source in lenition_rules:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (f"{cat}:{subcat}", rule, examples, source)
    )
    grammar_count += 1

# --- 5b. Lenition trigger contexts ---
lenition_triggers = [
    ("MUTATION", "LENITION_TRIGGER", "After the article yn with feminine singular nouns", "*yn ven* (the woman, < ben), *yn çheer* → *yn heer* (the land)", "Wheeler/CO"),
    ("MUTATION", "LENITION_TRIGGER", "After possessive adjectives my (my) and dty (your sg.)", "*my voir* (my mother, < moir), *dty hie* (your house, < thie)", "Wheeler/CO + leniter.pl"),
    ("MUTATION", "LENITION_TRIGGER", "After dy (to/that) + verbal noun", "*dy yannoo* (to do, < jannoo), *dy gholl* (to go, < goll)", "Wheeler/CO"),
    ("MUTATION", "LENITION_TRIGGER", "Past tense independent form (synthetic)", "*ghow* (took, < gow), *hrog* (built, < trog)", "Wheeler study 5"),
    ("MUTATION", "LENITION_TRIGGER", "After er (after/perfect) with most consonants", "*er vrishey* (having broken), *er hashtey* (having saved)", "Wheeler study 6"),
    ("MUTATION", "LENITION_TRIGGER", "After cha/nagh (negative particles)", "*cha nel* (is not), *cha jarg* → *cha yarg* (cannot)", "Wheeler/CO"),
    ("MUTATION", "LENITION_TRIGGER", "Adjective after feminine singular noun", "*ben vie* (good woman, < mie)", "Wheeler/CO"),
    ("MUTATION", "LENITION_TRIGGER", "After preposition + article (in some combinations)", "*'sy valley* (in the town, < balley → valley after 'sy)", "Wheeler/CO"),
    ("MUTATION", "LENITION_TRIGGER", "Vocative (direct address)", "*Vummig!* (Mother!), *Vanninagh!* (Manxman!)", "traditional usage"),
    ("MUTATION", "LENITION_TRIGGER", "After certain numerals (un, daa)", "*un vlein* (one year, < blein), *daa vlein* (two years)", "Wheeler/CO"),
]

for cat, subcat, rule, examples, source in lenition_triggers:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (f"{cat}:{subcat}", rule, examples, source)
    )
    grammar_count += 1

# --- 5c. Eclipsis/Nasalisation rules ---
eclipsis_rules = [
    ("MUTATION", "ECLIPSIS", "b → m", "*boayrd* → *moayrd*", "Wheeler study 6"),
    ("MUTATION", "ECLIPSIS", "c, k → g", "*kione* → *gione*", "Wheeler study 6"),
    ("MUTATION", "ECLIPSIS", "d → n", "*dooinney* → *nooinney*", "Wheeler study 6"),
    ("MUTATION", "ECLIPSIS", "f → v", "*fockle* → *vockle*", "Wheeler study 6"),
    ("MUTATION", "ECLIPSIS", "g → n (ng before vowels)", "*goll* → *n'gholl* (after er)", "Wheeler study 6"),
    ("MUTATION", "ECLIPSIS", "j → n", "*jannoo* → *yannoo* (lenition) or *n'yannoo* (nasalisation after er)", "Wheeler study 6"),
    ("MUTATION", "ECLIPSIS", "p → b", "*peccah* → *beccah*", "Wheeler study 6"),
    ("MUTATION", "ECLIPSIS", "t → d", "*toshiaght* → *doshiaght*", "Wheeler study 6"),
    ("MUTATION", "ECLIPSIS", "Vowels: n' prefix added", "*ee* → *n'ee*, *immee* → *n'immee* (after er)", "Wheeler study 6"),
]

eclipsis_triggers = [
    ("MUTATION", "ECLIPSIS_TRIGGER", "After nyn (our/your pl./their possessive)", "*nyn moayrd* (their table, < boayrd), *nyn gione* (their head, < kione)", "Wheeler/CO"),
    ("MUTATION", "ECLIPSIS_TRIGGER", "After er with some verbs (variable, lexically conditioned)", "*er n'gholl* (having gone), *er n'ee* (having eaten) — but many verbs take lenition instead", "Wheeler study 6"),
    ("MUTATION", "ECLIPSIS_TRIGGER", "Dependent verb forms (after cha, nagh, nee, row, etc.)", "*cha dug* (did not give, < tug), *nagh row* (was not, < row)", "Wheeler study 5"),
]

for cat, subcat, rule, examples, source in eclipsis_rules + eclipsis_triggers:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (f"{cat}:{subcat}", rule, examples, source)
    )
    grammar_count += 1

# --- 5d. Article rules ---
article_rules = [
    ("ARTICLE", "FORM", "yn before singular nouns; ny before plural nouns and genitive singular feminine", "*yn dooinney* (the man), *ny deiney* (the men), *kione ny bleeaney* (end of the year)", "CO/Wheeler"),
    ("ARTICLE", "MUTATION_MASC", "yn does NOT cause lenition on masculine singular nouns", "*yn fer* (the man), *yn thie* (the house) — no mutation", "CO/Wheeler"),
    ("ARTICLE", "MUTATION_FEM", "yn causes lenition on feminine singular nouns (except d, t, s+vowel which take t-prefix)", "*yn ven* (the woman, < ben), *yn chlagh* (the stone, < clagh)", "CO/Wheeler"),
    ("ARTICLE", "T_PREFIX", "yn + feminine noun beginning with s+vowel: s replaced by t", "*yn traie* (the beach, from *straie*) — but this pattern is limited in Manx", "CO/Wheeler"),
    ("ARTICLE", "H_PREFIX", "ny + plural beginning with vowel: h-prefix", "*ny h-eiyrt* (the followers)", "CO/Wheeler"),
    ("ARTICLE", "GENITIVE_MASC", "Genitive of masculine: yn + lenition of following noun", "*kione yn tholtain* (the ruin's head), but see individual declensions", "CO/Wheeler"),
    ("ARTICLE", "GENITIVE_FEM", "Genitive of feminine: ny + (no lenition or eclipsis)", "*bun ny creg* (the foot of the rock)", "CO/Wheeler"),
]

for cat, subcat, rule, examples, source in article_rules:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (f"{cat}:{subcat}", rule, examples, source)
    )
    grammar_count += 1

# --- 5e. Verb rules ---
verb_rules = [
    ("VERB", "STRUCTURE", "Four principal parts: base, verbal noun, past tense, participle", "*cur* (base), *cur* (VN), *hug* (past), *currit* (participle); many verbs are defective", "Wheeler study 5"),
    ("VERB", "INDEPENDENT_DEPENDENT", "Independent forms in positive main/relative clauses; dependent forms after cha, nagh, nee, row", "Independent: *honnick mee* (I saw); Dependent: *cha vaik mee* (I didn't see)", "Wheeler study 5"),
    ("VERB", "PAST_SYNTHETIC", "Synthetic past = lenited base (consonant) or d'+base (vowel)", "*ghow* (took, < gow), *hie* (went, < goll), *d'ee* (ate, < ee)", "Wheeler study 5"),
    ("VERB", "PAST_PERIPHRASTIC", "Periphrastic past = ren + verbal noun", "*ren mee goll* (I went), *ren ad toshiaght* (they began)", "Wheeler study 5"),
    ("VERB", "FUTURE_SUFFIX", "Future: base + -ee (3rd person), -ym (1st sg), -mayd (1st pl)", "*ver-ym* (I will give), *hig-ee* (he/she will come)", "Wheeler study 5"),
    ("VERB", "CONDITIONAL", "Conditional: base + -in (1sg), -agh (other persons)", "*verrin* (I would give), *harragh eh* (he would come)", "Wheeler study 5"),
    ("VERB", "IMPERATIVE", "Imperative: singular = base; plural = base + -jee (biblical) or base + shiu (modern)", "*tar!* (come!), *tar-jee!* / *tar shiu!* (come! pl.)", "Wheeler study 5"),
    ("VERB", "PERFECT", "Perfect: ta + subject + er + verbal noun (lenited/nasalised)", "*ta mee er n'gholl* (I have gone), *ta eh er vrishey* (he has broken)", "Wheeler study 5/6"),
    ("VERB", "PROGRESSIVE", "Progressive: ta + subject + gerund (ag/ec + VN)", "*ta mee cloie* (I am playing), *v'eh screeu* (he was writing)", "Wheeler study 5"),
    ("VERB", "RELATIVE_FUTURE", "Relative future: used in subordinate clauses and proverbs; suffix -ys/-s", "*brishys accyrys trooid boallaghyn cloaie* (hunger will break through stone walls)", "Wheeler study 5"),
]

for cat, subcat, rule, examples, source in verb_rules:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (f"{cat}:{subcat}", rule, examples, source)
    )
    grammar_count += 1

# --- 5f. Noun rules ---
noun_rules = [
    ("NOUN", "DECLENSION_CLASSES", "Five basic noun declension classes based on genitive: A (-ey), B (-ee), C (-agh), D (stem change), E (irregular)", "A: *braag/braagey*, B: *blein/bleeaney*→ actually B is -ee, C: genitive -agh, D: stem vowel change", "Wheeler study 3"),
    ("NOUN", "PLURAL_REGULAR", "Most common plural: -yn suffix added to singular", "*thie/thieyn* (houses), *fer/fir* (men — irregular)", "Wheeler study 1"),
    ("NOUN", "PLURAL_CLASSES", "Plural classes: 1 (-yn), 1a (-ghyn/-aghyn), 1b (-jyn), 1c (-inyn), 1d (-tyn/-teeyn), 1e (-eeyn/-eenyn), 2 (-ee), 3 (stem change), 4 (vowel change)", "See Appendix C for full tables", "Wheeler study 1"),
    ("NOUN", "GENITIVE_USE", "Genitive case used after another noun (compound), after verbal nouns, and after certain prepositions", "*baatey eeasteyragh* or *baatey yn eeasteyr* (the fisherman's boat), *screeu lioar* (writing a book → *lioar* could take genitive)", "Wheeler study 2"),
    ("NOUN", "GENDER", "Two genders: masculine (nm) and feminine (nf). Gender affects article mutation and adjective agreement", "Masc: *yn dooinney mooar* (the big man); Fem: *yn ven vooar* (the big woman, < mooar lenited)", "Wheeler/CO"),
]

for cat, subcat, rule, examples, source in noun_rules:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (f"{cat}:{subcat}", rule, examples, source)
    )
    grammar_count += 1

# --- 5g. Adjective rules ---
adj_rules = [
    ("ADJECTIVE", "POSITION", "Adjective follows the noun in Manx", "*thie beg* (small house), *fer mooar* (big man)", "Wheeler study 4/CO"),
    ("ADJECTIVE", "MUTATION_AFTER_FEM", "Adjective lenites after feminine singular noun", "*ben vie* (good woman, < mie), *ben vooar* (big woman, < mooar)", "Wheeler study 4/CO"),
    ("ADJECTIVE", "COMPARATIVE", "Comparative: ny + comparative form (often -ey ending for -agh adjectives)", "*ny smoo* (bigger, < mooar), *ny s'berçhee* (richer)", "Wheeler study 4"),
    ("ADJECTIVE", "SUPERLATIVE", "Superlative: yn + comparative form (same as comparative but with yn)", "*yn smoo* (the biggest)", "Wheeler study 4"),
    ("ADJECTIVE", "PREDICATIVE", "Predicative adjective uses copula: She ... eh/ee", "*She mie eh* (it is good), *T'eh mooar* (it is big — with *ta* for temporary state)", "CO"),
]

for cat, subcat, rule, examples, source in adj_rules:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (f"{cat}:{subcat}", rule, examples, source)
    )
    grammar_count += 1

# --- 5h. Copula rules ---
copula_rules = [
    ("COPULA", "FORM", "She (is) — used for identification, classification, and emphasis", "*She dooinney mie eh* (he is a good man), *She Manninagh mee* (I am a Manxman)", "UD corpus + CO"),
    ("COPULA", "NEGATIVE", "Cha nee (is not)", "*Cha nee shen yn aght* (that is not the way)", "UD corpus + CO"),
    ("COPULA", "PAST", "By (was — copula)", "*By vie lhiam shen* (I would like that / I liked that)", "CO"),
    ("COPULA", "CLEFT", "Cleft sentences: She ... (da/ec) + relative clause", "*She ec y trass laa haink eh* (It was on the third day he came)", "UD corpus"),
    ("COPULA", "VS_TA", "She for permanent identity/classification; ta for temporary state/location", "*She fer-Loss eh* (he is a herbalist — identity); *T'eh skee* (he is tired — state)", "CO"),
]

for cat, subcat, rule, examples, source in copula_rules:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (f"{cat}:{subcat}", rule, examples, source)
    )
    grammar_count += 1

# --- 5i. Preposition rules ---
prep_rules = [
    ("PREPOSITION", "INFLECTED_PREPS", "Prepositions inflect for person/number: ec (at), er (on), da (to), jeh (of), lesh (with), rish (to/against), veih (from), ayn (in), fo (under), harrish (over), mysh (about), roish (before), trooid (through)", "ec: aym, ayd, echey, eck, ain, eu, oc; er: orrym, ort, er, urree, orrin, erriu, orroo", "Wheeler/CO + UD mwtokens.tsv"),
    ("PREPOSITION", "COMPOUND_PREPS", "Compound prepositions: er son (for), er-y-fa (because), kyndagh rish (because of), mastey (among), mysh (about), trooid (through)", "*er son shen* (for that), *kyndagh rish yn emshyr* (because of the weather)", "CO"),
    ("PREPOSITION", "MUTATIONS_AFTER", "Some prepositions trigger lenition of following noun (see mutation tables)", "*dy + VN: dy yannoo* (to do); *'sy + noun: 'sy valley* (in the town)", "Wheeler/CO"),
]

for cat, subcat, rule, examples, source in prep_rules:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (f"{cat}:{subcat}", rule, examples, source)
    )
    grammar_count += 1

# --- 5j. Pronoun rules ---
pronoun_rules = [
    ("PRONOUN", "PERSONAL", "Personal pronouns: mee (I), oo (you sg), eh (he), ee (she), shin (we), shiu (you pl), ad (they)", "Emphatic forms: mish, uss, eshyn, ish, shinyn, shiuish, adsyn", "CO"),
    ("PRONOUN", "POSSESSIVE", "Possessive adjectives: my (my, + lenition), dty (your sg, + lenition), e (his, + lenition), e (her, + h-prefix before vowels, NO lenition), nyn (our/your pl/their, + eclipsis)", "*my voir* (my mother), *e hie* (his house), *e thie* (her house — no lenition, h-prefix: *e hEnnym*)", "CO + UD corpus"),
    ("PRONOUN", "DEMONSTRATIVE", "shoh (this), shen (that), shid (yonder); used after noun", "*yn dooinney shoh* (this man), *yn lioar shen* (that book), *yn thie shid* (yonder house)", "CO"),
    ("PRONOUN", "RELATIVE", "Relative pronoun not usually expressed; relative clause formed by verb alone or with 'ta'", "*yn dooinney haink* (the man who came), *yn ven ta cummal ayns shoh* (the woman who lives here)", "CO"),
]

for cat, subcat, rule, examples, source in pronoun_rules:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (f"{cat}:{subcat}", rule, examples, source)
    )
    grammar_count += 1

# --- 5k. Word order rules ---
word_order_rules = [
    ("WORD_ORDER", "VSO", "Basic word order is Verb-Subject-Object", "*Honnick yn dooinney yn kayt* (The man saw the cat — lit. saw the man the cat)", "CO"),
    ("WORD_ORDER", "COPULA_FIRST", "Copula sentences: She + predicate + subject", "*She Manninagh mee* (I am a Manxman — lit. Is Manxman I)", "CO"),
    ("WORD_ORDER", "ADJECTIVE_AFTER", "Adjectives follow the noun", "*thie beg* (small house), *moddey mooar* (big dog)", "CO"),
    ("WORD_ORDER", "GENITIVE_AFTER", "Genitive noun follows the possessed noun", "*dorrys y thie* (the door of the house)", "CO"),
    ("WORD_ORDER", "ADVERB_POSITION", "Adverbs typically follow the verb or come at end of clause", "*Haink eh dy-tappee* (He came quickly)", "CO"),
    ("WORD_ORDER", "FRONTING", "Fronting for emphasis using copula cleft: She + fronted element + relative clause", "*She ayns Doolish v'eh cummal* (It was in Douglas he was living)", "CO + UD corpus"),
]

for cat, subcat, rule, examples, source in word_order_rules:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (f"{cat}:{subcat}", rule, examples, source)
    )
    grammar_count += 1

# --- 5l. Numeral rules ---
numeral_rules = [
    ("NUMERAL", "SYSTEM", "Manx traditionally uses vigesimal (base-20) counting; decimal also used in modern Manx", "Vigesimal: *feed* (20), *daeed* (40 = 2×20), *tree feed* (60 = 3×20); Decimal: *jeih, feed, jeih as feed* etc.", "CO"),
    ("NUMERAL", "UN", "un (one) + singular noun + lenition", "*un vlein* (one year, < blein)", "CO"),
    ("NUMERAL", "DAA", "daa (two) + singular noun + lenition", "*daa vlein* (two years), *daa hie* (two houses)", "CO"),
    ("NUMERAL", "TREE_TO_JEIH", "tree (3) to jeih (10) + plural noun", "*tree thieyn* (three houses), *queig bleeantyn* (five years)", "CO"),
    ("NUMERAL", "COUNTING_FORM", "Counting form (no noun): nane, jees, tree, kiare, queig, shey, shiaght, hoght, nuy, jeih", "Traditional: *nane-jeig* (11), *daa-yeig* (12), *tree-jeig* (13)...", "CO"),
]

for cat, subcat, rule, examples, source in numeral_rules:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (f"{cat}:{subcat}", rule, examples, source)
    )
    grammar_count += 1

conn.commit()
print(f"  Inserted {grammar_count:,} grammar rules")

# ============================================================
# 6. MUTATIONS TABLE - systematic mapping of base → mutated forms
# ============================================================
print("\n=== 6. MUTATIONS ===")

mut_count = 0

# Build lenition mappings from leniter.pl regex rules
lenition_map = [
    # (initial_pattern, lenited_result, description)
    ('b', 'v', 'b → v'),
    ('bw', 'v', 'bw → v'),
    ('m', 'v', 'm → v'),
    ('mw', 'v', 'mw → v'),
    ('ch', 'h', 'ch → h (already aspirated)'),
    ('çh', 'h', 'çh → h'),
    ('c', 'ch', 'c → ch (before non-h)'),
    ('k', 'ch', 'k → ch (before non-h)'),
    ('d', 'gh', 'd → gh'),
    ('dh', 'gh', 'dh → gh'),
    ('f', '', 'f → zero (disappears)'),
    ('g', 'gh', 'g → gh (before a,o,u or consonant)'),
    ('g', 'y', 'g → y (before e,i)'),
    ('j', 'y', 'j → y'),
    ('p', 'ph', 'p → ph (before non-h)'),
    ('qu', 'wh', 'qu → wh'),
    ('sl', 'l', 'sl → l'),
    ('sn', 'n', 'sn → n'),
    ('str', 'hr', 'str → hr'),
    ('sh', 'h', 'sh → h (before vowels)'),
    ('s', 'h', 's → h (before vowels)'),
    ('t', 'h', 't → h'),
    ('th', 'h', 'th → h'),
]

# Now apply these to actual words from focloir.txt to build the mutations table
with open(os.path.join(GAELG, 'focloir.txt'), 'r', encoding='utf-8') as f:
    words = set()
    for line in f:
        parts = line.strip().split('\t')
        if parts:
            word, _, _ = parse_pos(parts[0])
            if word and len(word) >= 2 and word[0].isalpha():
                words.add(word.lower())

# For each word, compute its lenited and eclipsed forms
def lenite(word):
    """Apply Manx lenition rules (from leniter.pl)."""
    w = word
    # Order matters - more specific patterns first
    if re.match(r'^[bm]w', w, re.I):
        return re.sub(r'^[bBmM]w?', lambda m: 'V' if m.group()[0].isupper() else 'v', w, count=1)
    if re.match(r'^[bm]', w, re.I):
        return re.sub(r'^[bBmM]', lambda m: 'V' if m.group().isupper() else 'v', w, count=1)
    if re.match(r'^[cç]h', w, re.I):
        return re.sub(r'^[cCçÇ]h', lambda m: 'H' if m.group()[0].isupper() else 'h', w, count=1)
    if re.match(r'^[ck](?!h)', w, re.I):
        return re.sub(r'^[cCkK]', lambda m: 'Ch' if m.group().isupper() else 'ch', w, count=1)
    if re.match(r'^g[ei]', w, re.I):
        return re.sub(r'^[gG]', lambda m: 'Y' if m.group().isupper() else 'y', w, count=1)
    if re.match(r'^g(?!h)', w, re.I):
        return re.sub(r'^[gG]', lambda m: 'Gh' if m.group().isupper() else 'gh', w, count=1)
    if re.match(r'^p(?!h)', w, re.I):
        return re.sub(r'^[pP]', lambda m: 'Ph' if m.group().isupper() else 'ph', w, count=1)
    if re.match(r'^qu', w, re.I):
        return re.sub(r'^[qQ]u', lambda m: 'Wh' if m.group()[0].isupper() else 'wh', w, count=1)
    if re.match(r'^s[hl]?l', w, re.I):
        return re.sub(r'^[sS]h?l', lambda m: 'L' if m.group()[0].isupper() else 'l', w, count=1)
    if re.match(r'^sn', w, re.I):
        return re.sub(r'^[sS]n', lambda m: 'N' if m.group()[0].isupper() else 'n', w, count=1)
    if re.match(r'^str', w, re.I):
        return re.sub(r'^[sS]tr', lambda m: 'Hr' if m.group()[0].isupper() else 'hr', w, count=1)
    if re.match(r'^sh?[aeiouy]', w, re.I):
        return re.sub(r'^[sS]h?', lambda m: 'H' if m.group()[0].isupper() else 'h', w, count=1)
    if re.match(r'^j', w, re.I):
        return re.sub(r'^[jJ]', lambda m: 'Y' if m.group().isupper() else 'y', w, count=1)
    if re.match(r'^th?', w, re.I):
        return re.sub(r'^[tT]h?', lambda m: 'H' if m.group()[0].isupper() else 'h', w, count=1)
    if re.match(r'^dh?', w, re.I):
        return re.sub(r'^[dD]h?', lambda m: 'Gh' if m.group()[0].isupper() else 'gh', w, count=1)
    if re.match(r'^[fF]', w):
        return re.sub(r'^[fF]', '', w, count=1)
    return w  # no change

def eclipse(word):
    """Apply Manx eclipsis/nasalisation rules."""
    w = word
    if re.match(r'^b', w, re.I):
        return re.sub(r'^[bB]', lambda m: 'M' if m.group().isupper() else 'm', w, count=1)
    if re.match(r'^[ck]', w, re.I):
        return re.sub(r'^[cCkK]', lambda m: 'G' if m.group().isupper() else 'g', w, count=1)
    if re.match(r'^d', w, re.I):
        return re.sub(r'^[dD]', lambda m: 'N' if m.group().isupper() else 'n', w, count=1)
    if re.match(r'^f', w, re.I):
        return re.sub(r'^[fF]', lambda m: 'V' if m.group().isupper() else 'v', w, count=1)
    if re.match(r'^g', w, re.I):
        return "n'gh" + w[1:] if w[0].islower() else "N'Gh" + w[1:]
    if re.match(r'^j', w, re.I):
        return "n'y" + w[1:] if w[0].islower() else "N'Y" + w[1:]
    if re.match(r'^p', w, re.I):
        return re.sub(r'^[pP]', lambda m: 'B' if m.group().isupper() else 'b', w, count=1)
    if re.match(r'^t', w, re.I):
        return re.sub(r'^[tT]', lambda m: 'D' if m.group().isupper() else 'd', w, count=1)
    if re.match(r'^[aeiou]', w, re.I):
        return "n'" + w
    return w

# Apply to all words and store
for word in sorted(words):
    lenited = lenite(word)
    if lenited != word:
        conn.execute(
            "INSERT INTO mutations (base_form, mutated_form, mutation_type, trigger_context, notes) VALUES (?,?,?,?,?)",
            (word, lenited, 'lenition', 'general', 'computed from leniter.pl rules')
        )
        mut_count += 1
    
    eclipsed = eclipse(word)
    if eclipsed != word and eclipsed != lenited:
        conn.execute(
            "INSERT INTO mutations (base_form, mutated_form, mutation_type, trigger_context, notes) VALUES (?,?,?,?,?)",
            (word, eclipsed, 'eclipsis', 'general', 'computed from nasalisation rules')
        )
        mut_count += 1

conn.commit()
print(f"  Inserted {mut_count:,} mutation entries")

# ============================================================
# FINAL STATUS
# ============================================================
print("\n" + "="*50)
print("=== FINAL DATABASE STATUS ===")
print("="*50)
for table in ['dictionary', 'inflections', 'parallel_sentences', 'grammar_rules', 'phrases', 'mutations']:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    status = '✓' if count > 0 else '✗ EMPTY'
    print(f"  {table}: {count:,} {status}")

conn.close()
print("\nDone!")
