#!/usr/bin/env python3
"""
Comprehensive DB builder: populates all 6 tables from repo data.

Run from anywhere — all paths are relative to the repo root.

Usage:
    python scripts/build_all.py

Sources:
    data/scannell/gv2ga.po       -> dictionary (Manx-Irish word mappings)
    data/scannell/focloir.txt    -> inflections (verb/noun/adj forms)
    data/scannell/multi-gv.txt   -> phrases (multi-word expressions)
    data/scannell/leniter.pl     -> mutations (computed lenition/eclipsis)
    data/scannell/focloir.txt    -> mutations (word list for computation)
    *.jsonl in repo root + data/raw/ -> parallel_sentences
    Hardcoded rules              -> grammar_rules
"""
import sqlite3
import re
import json
import os
import sys

# ============================================================
# PATHS - all relative to repo root
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
SCANNELL = os.path.join(REPO_ROOT, 'data', 'scannell')
MANXTXT = os.path.join(REPO_ROOT, 'manxtxt')
RAW_DIR = os.path.join(REPO_ROOT, 'data', 'raw')
DB_PATH = os.path.join(REPO_ROOT, 'data', 'processed', 'manx.db')

# Ensure output directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Remove old DB for clean rebuild
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("Removed existing database")

# ============================================================
# SCHEMA
# ============================================================
SCHEMA = """
CREATE TABLE IF NOT EXISTS dictionary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    english TEXT NOT NULL,
    manx TEXT NOT NULL,
    part_of_speech TEXT,
    gender TEXT,
    source TEXT,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_dict_english ON dictionary(english);
CREATE INDEX IF NOT EXISTS idx_dict_manx ON dictionary(manx);

CREATE TABLE IF NOT EXISTS inflections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_form TEXT NOT NULL,
    inflected_form TEXT NOT NULL,
    inflection_type TEXT NOT NULL,
    part_of_speech TEXT,
    pattern_class TEXT,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_infl_base ON inflections(base_form);
CREATE INDEX IF NOT EXISTS idx_infl_type ON inflections(inflection_type);

CREATE TABLE IF NOT EXISTS parallel_sentences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    english TEXT NOT NULL,
    manx TEXT NOT NULL,
    source TEXT,
    domain TEXT,
    quality TEXT DEFAULT 'unreviewed'
);
CREATE INDEX IF NOT EXISTS idx_par_english ON parallel_sentences(english);
CREATE INDEX IF NOT EXISTS idx_par_manx ON parallel_sentences(manx);

CREATE VIRTUAL TABLE IF NOT EXISTS parallel_fts USING fts5(
    english, manx, content='parallel_sentences', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS parallel_ai AFTER INSERT ON parallel_sentences BEGIN
    INSERT INTO parallel_fts(rowid, english, manx) VALUES (new.id, new.english, new.manx);
END;
CREATE TRIGGER IF NOT EXISTS parallel_ad AFTER DELETE ON parallel_sentences BEGIN
    INSERT INTO parallel_fts(parallel_fts, rowid, english, manx) VALUES('delete', old.id, old.english, old.manx);
END;
CREATE TRIGGER IF NOT EXISTS parallel_au AFTER UPDATE ON parallel_sentences BEGIN
    INSERT INTO parallel_fts(parallel_fts, rowid, english, manx) VALUES('delete', old.id, old.english, old.manx);
    INSERT INTO parallel_fts(rowid, english, manx) VALUES (new.id, new.english, new.manx);
END;

CREATE TABLE IF NOT EXISTS grammar_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    rule_text TEXT NOT NULL,
    examples TEXT,
    source TEXT
);
CREATE INDEX IF NOT EXISTS idx_gram_cat ON grammar_rules(category);

CREATE TABLE IF NOT EXISTS phrases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    english TEXT NOT NULL,
    manx TEXT NOT NULL,
    category TEXT,
    source TEXT
);
CREATE INDEX IF NOT EXISTS idx_phrase_english ON phrases(english);

CREATE TABLE IF NOT EXISTS mutations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_form TEXT NOT NULL,
    mutated_form TEXT NOT NULL,
    mutation_type TEXT NOT NULL,
    trigger_context TEXT,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_mut_base ON mutations(base_form);
"""

conn = sqlite3.connect(DB_PATH)
conn.executescript(SCHEMA)
print(f"Created database at {DB_PATH}")

# ============================================================
# HELPER: POS tag parser
# ============================================================
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
            word = re.sub(r'\d+$', '', word)
            return word, pos, gender
    return headword, None, None

# ============================================================
# 1. DICTIONARY from gv2ga.po
# ============================================================
print("=== 1. DICTIONARY (gv2ga.po) ===")

dict_count = 0
seen_words = set()

po_path = os.path.join(SCANNELL, 'gv2ga.po')
if os.path.exists(po_path):
    with open(po_path, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = re.findall(r'(?:^#[^\n]*\n)*^msgid "([^"]+)"\nmsgstr "([^"]*)"', content, re.MULTILINE)

    for msgid, msgstr in entries:
        if not msgstr or msgstr == msgid:
            continue
        manx_word, pos, gender = parse_pos(msgid)
        if not manx_word or len(manx_word) < 2:
            continue
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
else:
    print(f"  SKIPPED - {po_path} not found")

# ============================================================
# 2. INFLECTIONS from focloir.txt
# ============================================================
print("\n=== 2. INFLECTIONS (focloir.txt) ===")

infl_count = 0
focloir_path = os.path.join(SCANNELL, 'focloir.txt')
if os.path.exists(focloir_path):
    with open(focloir_path, 'r', encoding='utf-8') as f:
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

            if col2 and col2 != '0':
                vn_word, _, _ = parse_pos(col2)
                if vn_word and vn_word != base_word:
                    if pos == 'verb':
                        conn.execute(
                            "INSERT INTO inflections (base_form, inflected_form, inflection_type, part_of_speech, notes) VALUES (?,?,?,?,?)",
                            (base_word, vn_word, 'verbal_noun', 'verb', 'from focloir.txt')
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

            if col3 and col3 != '0':
                if col3 == '1':
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
else:
    print(f"  SKIPPED - {focloir_path} not found")

# ============================================================
# 3. PHRASES from multi-gv.txt
# ============================================================
print("\n=== 3. PHRASES (multi-gv.txt) ===")

phrase_count = 0
multi_path = os.path.join(SCANNELL, 'multi-gv.txt')
if os.path.exists(multi_path):
    with open(multi_path, 'r', encoding='utf-8') as f:
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
else:
    print(f"  SKIPPED - {multi_path} not found")

# ============================================================
# 4. PARALLEL SENTENCES from JSONL files
# ============================================================
print("\n=== 4. PARALLEL SENTENCES ===")

parallel_count = 0
seen_pairs = set()

def ingest_jsonl(filepath):
    """Ingest a JSONL file of parallel sentences."""
    global parallel_count
    file_count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            en = obj.get('source', obj.get('en', obj.get('english', ''))).strip()
            gv = obj.get('target', obj.get('gv', obj.get('manx', ''))).strip()
            source = obj.get('ref', obj.get('source_name', os.path.basename(filepath)))

            if not en or not gv:
                continue

            pair_key = (en.lower(), gv.lower())
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            conn.execute(
                "INSERT INTO parallel_sentences (english, manx, source) VALUES (?,?,?)",
                (en, gv, source)
            )
            parallel_count += 1
            file_count += 1
    return file_count

# Search repo root and data/raw for JSONL files
jsonl_files = []
for search_dir in [REPO_ROOT, RAW_DIR]:
    if os.path.exists(search_dir):
        for f in sorted(os.listdir(search_dir)):
            if f.endswith('.jsonl'):
                full = os.path.join(search_dir, f)
                if os.path.getsize(full) > 0:
                    jsonl_files.append(full)

for jf in jsonl_files:
    count = ingest_jsonl(jf)
    print(f"  {os.path.basename(jf)}: {count:,} sentences")

conn.commit()
print(f"  Total: {parallel_count:,} parallel sentences (deduplicated)")

# ============================================================
# 5. GRAMMAR RULES (hardcoded from Wheeler studies + corpus)
# ============================================================
print("\n=== 5. GRAMMAR RULES ===")

grammar_count = 0

all_grammar_rules = [
    # --- Lenition triggers ---
    ("LENITION:TRIGGER", "After definite article yn + feminine singular noun", "*yn vlein* (the year, < blein), *yn chabbane* (the cabin, < cabbane)", "Wheeler study 6"),
    ("LENITION:TRIGGER", "After daa (two)", "*daa vlein* (two years, < blein), *daa hie* (two houses, < thie)", "Wheeler study 6"),
    ("LENITION:TRIGGER", "After possessive adjectives my (my), dty (your sg.), e (his)", "*my vlein* (my year), *dty hie* (your house), *e charrey* (his friend)", "Wheeler study 6"),
    ("LENITION:TRIGGER", "After prepositions: er (on), fo (under), ny (than), ro (too), dy (to/particle)", "*er vullagh* (on top, < mullagh), *fo halloo* (underground, < thalloo)", "Wheeler study 6"),
    ("LENITION:TRIGGER", "After verbal particles dy/nagh in dependent clauses", "*dy voddin* (that I might, < foddin), *nagh vel* (that is not, < vel)", "Wheeler study 6"),
    ("LENITION:TRIGGER", "Past tense of regular verbs", "*hug* (gave, < tug/cur), *hilg* (threw, < tilg)", "Wheeler study 5"),
    ("LENITION:TRIGGER", "After particles cha (not) and nagh (that...not)", "*cha vel* (is not), *cha jarg* (cannot, < jarg)", "CO"),
    ("LENITION:TRIGGER", "After vocative particle y/a", "*y harvaant* (O servant, < sharvaant)", "CO"),
    ("LENITION:TRIGGER", "Adjective lenited after feminine singular noun", "*ben vie* (good woman, < mie), *blein vooar* (great year, < mooar)", "Wheeler study 4"),
    # --- Eclipsis triggers ---
    ("ECLIPSIS:TRIGGER", "After plural definite article ny", "*ny girree* (the cocks, < kirree - but eclipsis rare in modern Manx)", "Wheeler study 6"),
    ("ECLIPSIS:TRIGGER", "After possessive nyn (our/your pl./their)", "*nyn gione* (our head, < kione), *nyn dhie* (our house, < thie)", "CO"),
    ("ECLIPSIS:TRIGGER", "After preposition ayns yn (in the)", "*ayns yn gharey* (in the garden, < garey)", "CO"),
    # --- Lenition consonant mappings ---
    ("LENITION:MAP", "b -> v: *ben* -> *ven*", "b -> v, bw -> v", "leniter.pl"),
    ("LENITION:MAP", "m -> v: *mooar* -> *vooar*", "m -> v, mw -> v", "leniter.pl"),
    ("LENITION:MAP", "c -> ch: *cabbane* -> *chabbane*", "c/k -> ch (before non-h)", "leniter.pl"),
    ("LENITION:MAP", "ch/ch -> h: *chengey* -> *hengey*", "already-aspirated forms reduce to h", "leniter.pl"),
    ("LENITION:MAP", "d -> gh: *dooinney* -> *ghooinney*", "d/dh -> gh", "leniter.pl"),
    ("LENITION:MAP", "f -> zero (disappears): *fer* -> *'er*", "f drops entirely", "leniter.pl"),
    ("LENITION:MAP", "g -> gh/y: *garey* -> *gharey*, *geurey* -> *yeurey*", "g -> gh (before a,o,u,cons), g -> y (before e,i)", "leniter.pl"),
    ("LENITION:MAP", "j -> y: *jannoo* -> *yannoo*", "j -> y", "leniter.pl"),
    ("LENITION:MAP", "p -> ph: *peccah* -> *pheccah*", "p -> ph (before non-h)", "leniter.pl"),
    ("LENITION:MAP", "qu -> wh: *quoi* -> *whoi*", "qu -> wh", "leniter.pl"),
    ("LENITION:MAP", "s -> h/l/n: *sleityn* -> *leityn*, *sniaghtey* -> *niaghtey*", "sl->l, sn->n, sh->h, s->h (before vowel)", "leniter.pl"),
    ("LENITION:MAP", "str -> hr: *stroo* -> *hroo*", "str -> hr", "leniter.pl"),
    ("LENITION:MAP", "t -> h: *thie* -> *hie*, *thalloo* -> *halloo*", "t/th -> h", "leniter.pl"),
    # --- Eclipsis consonant mappings ---
    ("ECLIPSIS:MAP", "b -> m: *boayl* -> *moayl*", "b -> m", "CO"),
    ("ECLIPSIS:MAP", "c/k -> g: *kione* -> *gione*", "c/k -> g", "CO"),
    ("ECLIPSIS:MAP", "d -> n: *dorrys* -> *norrys*", "d -> n", "CO"),
    ("ECLIPSIS:MAP", "f -> v: *fockle* -> *vockle*", "f -> v", "CO"),
    ("ECLIPSIS:MAP", "g -> n'gh: *garey* -> *n'gharey*", "g -> n'gh (nasal + lenited)", "CO"),
    ("ECLIPSIS:MAP", "j -> n'y: *jannoo* -> *n'yannoo*", "j -> n'y", "CO"),
    ("ECLIPSIS:MAP", "p -> b: *peccah* -> *beccah*", "p -> b", "CO"),
    ("ECLIPSIS:MAP", "t -> d: *thie* -> *dhie*", "t -> d", "CO"),
    ("ECLIPSIS:MAP", "vowel -> n'+vowel: *awin* -> *n'awin*", "prefixed n' before vowels", "CO"),
    # --- Verb system ---
    ("VERB:TENSE", "Present: ta + subject + verbal noun. Habitual: bee + subject + verbal noun", "*Ta mee goll* (I am going), *Bee eh cheet* (He comes [habitually])", "CO"),
    ("VERB:TENSE", "Past: synthetic past form (often lenited), or ren + subject + VN", "*Honnick mee* (I saw), *Ren mee fakin* (I saw [periphrastic])", "CO"),
    ("VERB:TENSE", "Future: bee/vees + subject + VN, or synthetic future", "*Hig eh* (He will come), *Bee eh cheet* (He will be coming)", "CO"),
    ("VERB:TENSE", "Conditional: yinnagh/veagh + subject + VN", "*Yinnin shen* (I would do that), *Veagh eh goll* (He would be going)", "CO"),
    ("VERB:NEGATIVE", "cha + lenition + verb for simple negative", "*Cha nel mee* (I am not), *Cha jarg mee* (I cannot)", "CO"),
    ("VERB:QUESTION", "vel/row/bee etc. for interrogative; nagh for negative interrogative", "*Vel oo cheet?* (Are you coming?), *Nagh vel eh ayn?* (Is he not there?)", "CO"),
    ("VERB:IRREGULAR", "10 irregular/suppletive verbs: goll (go), cheet (come), cur (give/put), geddyn (get), jannoo (do/make), fakin (see), gra (say), clashtyn (hear), toiggal (understand), ec (at/have)", "Each has distinct past, future, conditional, imperative stems", "Wheeler study 5"),
    # --- Noun system ---
    ("NOUN:GENDER", "Two genders: masculine and feminine. Gender affects article, lenition of adjectives, and pronoun agreement", "*yn dooinney mooar* (the big man, no lenition), *yn ven vooar* (the big woman, lenition)", "CO"),
    ("NOUN:PLURAL", "7 plural classes: -yn (regular), -aghyn, -yn with vowel change, -eeyn, -tyn, vowel change only, irregular", "*thieyn* (houses), *cabbil* (horses < cabbyl), *kirree* (sheep < keyrrey)", "Wheeler study 1"),
    ("NOUN:GENITIVE", "Genitive formed by juxtaposition: possessed + possessor", "*dorrys y thie* (door of the house), *bainney ny baa* (milk of the cow)", "CO"),
    ("NOUN:ARTICLE", "yn (the) before singular; ny before plural. No indefinite article", "*yn dooinney* (the man), *ny deiney* (the men), *dooinney* (a man)", "CO"),
    # --- Adjective rules ---
    ("ADJECTIVE:POSITION", "Adjectives follow the noun", "*thie beg* (small house), *moddey mooar* (big dog)", "CO"),
    ("ADJECTIVE:LENITION", "Adjective lenited after feminine singular noun", "*ben vie* (good woman, < mie), *blein vooar* (great year, < mooar)", "Wheeler study 4"),
    ("ADJECTIVE:COMPARISON", "Comparative: ny + s-form or analytical ny smoo + adj", "*ny stroshey* (stronger), *ny smoo taitnyssagh* (more pleasant)", "CO"),
    ("ADJECTIVE:SUPERLATIVE", "Superlative: y/yn + s-form", "*yn stroshey* (the strongest)", "CO"),
    # --- Pronoun rules ---
    ("PRONOUN:PERSONAL", "Independent: mee (I), oo (you), eh (he), ee (she), shin (we), shiu (you pl.), ad (they)", "Used as subject/object in verbal constructions", "CO"),
    ("PRONOUN:POSSESSIVE", "my (my)+len, dty (your)+len, e (his)+len, e (her, no len, h- before vowel), nyn (our/your pl./their)+ecl", "*my vlein* (my year), *e charrey* (his friend), *e carrey* (her friend)", "CO"),
    ("PRONOUN:PREPOSITIONAL", "Prepositions inflect for person: ec->aym/ayd/echey/eck/ain/eu/oc, er->orrym/ort/er/urree/orrin/erriu/orroo", "*t'eh aym* (I have it, lit. it is at-me)", "CO"),
    ("PRONOUN:DEMONSTRATIVE", "shoh (this), shen (that), shid (yonder); used after noun", "*yn dooinney shoh* (this man), *yn lioar shen* (that book), *yn thie shid* (yonder house)", "CO"),
    ("PRONOUN:RELATIVE", "Relative pronoun not usually expressed; relative clause formed by verb alone or with 'ta'", "*yn dooinney haink* (the man who came), *yn ven ta cummal ayns shoh* (the woman who lives here)", "CO"),
    # --- Preposition rules ---
    ("PREPOSITION:LENITION", "Many prepositions trigger lenition: er (on), fo (under), dy (to), ny (than), ro (too), veih (from)", "*er vullagh* (on top), *fo halloo* (underground), *dy vie* (well, lit. to good)", "CO"),
    ("PREPOSITION:INFLECTION", "Prepositions inflect for person/number (prepositional pronouns)", "*ec* -> aym, ayd, echey, eck, ain, eu, oc", "CO"),
    ("PREPOSITION:COMPOUND", "Common compound prepositions: er-ash (back), er-lheh (separate), mysh (about), trooid (through)", "*Haink eh er-ash* (He came back), *mysh tree bleeaney* (about three years)", "CO"),
    # --- Copula rules ---
    ("COPULA:PRESENT", "she (is) - identifies, classifies, emphasises; often in cleft constructions", "*She Manninagh mee* (I am Manx), *She dooinney mie eh* (He is a good man)", "CO"),
    ("COPULA:NEGATIVE", "cha nee (is not)", "*Cha nee Manninagh mee* (I am not Manx)", "CO"),
    ("COPULA:PAST", "by/ba (was) + lenition", "*By vie lhiam shen* (I liked that, lit. was good with-me that)", "CO"),
    ("COPULA:QUESTION", "nee (is it?) in questions", "*Nee Manninagh oo?* (Are you Manx?)", "CO"),
    ("COPULA:VS_TA", "she classifies/identifies ('is a'), ta describes state/location ('is being/is at')", "*She fer-Loss eh* (He is a gardener) vs *T'eh gobbragh* (He is working)", "CO"),
    # --- Word order rules ---
    ("WORD_ORDER:VSO", "Basic word order is Verb-Subject-Object", "*Honnick yn dooinney yn kayt* (The man saw the cat - lit. saw the man the cat)", "CO"),
    ("WORD_ORDER:COPULA_FIRST", "Copula sentences: She + predicate + subject", "*She Manninagh mee* (I am a Manxman - lit. Is Manxman I)", "CO"),
    ("WORD_ORDER:ADJECTIVE_AFTER", "Adjectives follow the noun", "*thie beg* (small house), *moddey mooar* (big dog)", "CO"),
    ("WORD_ORDER:GENITIVE_AFTER", "Genitive noun follows the possessed noun", "*dorrys y thie* (the door of the house)", "CO"),
    ("WORD_ORDER:ADVERB_POSITION", "Adverbs typically follow the verb or come at end of clause", "*Haink eh dy-tappee* (He came quickly)", "CO"),
    ("WORD_ORDER:FRONTING", "Fronting for emphasis using copula cleft: She + fronted element + relative clause", "*She ayns Doolish v'eh cummal* (It was in Douglas he was living)", "CO + UD corpus"),
    # --- Numeral rules ---
    ("NUMERAL:SYSTEM", "Manx traditionally uses vigesimal (base-20) counting; decimal also used in modern Manx", "Vigesimal: *feed* (20), *daeed* (40 = 2x20), *tree feed* (60 = 3x20)", "CO"),
    ("NUMERAL:UN", "un (one) + singular noun + lenition", "*un vlein* (one year, < blein)", "CO"),
    ("NUMERAL:DAA", "daa (two) + singular noun + lenition", "*daa vlein* (two years), *daa hie* (two houses)", "CO"),
    ("NUMERAL:TREE_TO_JEIH", "tree (3) to jeih (10) + plural noun", "*tree thieyn* (three houses), *queig bleeantyn* (five years)", "CO"),
    ("NUMERAL:COUNTING_FORM", "Counting form (no noun): nane, jees, tree, kiare, queig, shey, shiaght, hoght, nuy, jeih", "Traditional: *nane-jeig* (11), *daa-yeig* (12), *tree-jeig* (13)...", "CO"),
]

for cat, rule, examples, source in all_grammar_rules:
    conn.execute(
        "INSERT INTO grammar_rules (category, rule_text, examples, source) VALUES (?,?,?,?)",
        (cat, rule, examples, source)
    )
    grammar_count += 1

conn.commit()
print(f"  Inserted {grammar_count:,} grammar rules")

# ============================================================
# 6. MUTATIONS - computed lenition/eclipsis for all known words
# ============================================================
print("\n=== 6. MUTATIONS ===")

mut_count = 0

# Collect all known words from focloir.txt
words = set()
if os.path.exists(focloir_path):
    with open(focloir_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if parts:
                word, _, _ = parse_pos(parts[0])
                if word and len(word) >= 2 and word[0].isalpha():
                    words.add(word.lower())

def lenite(word):
    """Apply Manx lenition rules (from leniter.pl)."""
    w = word
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
    return w

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
print("\n" + "=" * 50)
print("=== FINAL DATABASE STATUS ===")
print("=" * 50)
for table in ['dictionary', 'inflections', 'parallel_sentences', 'grammar_rules', 'phrases', 'mutations']:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    status = 'OK' if count > 0 else 'EMPTY'
    print(f"  {table}: {count:,} {status}")

db_size = os.path.getsize(DB_PATH)
print(f"\nDatabase size: {db_size / 1024 / 1024:.1f} MB")
print(f"Database path: {DB_PATH}")

conn.close()
print("\nDone!")
