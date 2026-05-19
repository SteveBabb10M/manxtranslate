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

# --- Kelly Fockleyreen (Phil Kelly's 130K-entry Manx-English dictionary) ---
kelly_path = os.path.join(RAW_DIR, 'kelly_fockleyreen.jsonl')
kelly_dict_count = 0
kelly_example_pairs = []

if os.path.exists(kelly_path):
    print(f"\n  --- Kelly Fockleyreen ---")
    with open(kelly_path, 'r', encoding='utf-8') as fh:
        for line in fh:
            obj = json.loads(line)
            eng = obj['english'].strip()
            if not eng or len(eng) < 2:
                continue

            for gv in obj.get('manx', []):
                gv = gv.strip()
                if not gv or len(gv) < 2:
                    continue
                # Skip entries that look like example sentences rather than translations
                if len(gv) > 80 or len(eng) > 80:
                    continue
                key = (eng.lower()[:50], gv.lower()[:50])
                if key in seen_words:
                    continue
                seen_words.add(key)
                conn.execute(
                    "INSERT INTO dictionary (english, manx, part_of_speech, source) VALUES (?,?,?,?)",
                    (eng, gv, '', 'kelly-fockleyreen')
                )
                kelly_dict_count += 1

            # Collect example sentence pairs for parallel_sentences later
            examples = obj.get('examples', [])
            en_example = None
            for ex in examples:
                if ex.startswith('EN:'):
                    en_example = ex[3:].strip()
                elif en_example and not ex.startswith('EN:'):
                    # This is the Manx translation of the previous English example
                    kelly_example_pairs.append((en_example, ex.strip()))
                    en_example = None
                else:
                    en_example = None

    conn.commit()
    print(f"  Kelly dictionary: {kelly_dict_count:,} new entries")
    print(f"  Kelly example pairs collected: {len(kelly_example_pairs):,} (will add in parallel section)")
else:
    print(f"\n  Kelly Fockleyreen not found at {kelly_path}")

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

            en = obj.get('source', obj.get('en', obj.get('english', '')))
            gv = obj.get('target', obj.get('gv', obj.get('manx', '')))
            # Handle fields that are lists instead of strings
            if isinstance(en, list):
                en = ' '.join(str(x) for x in en)
            if isinstance(gv, list):
                gv = ' '.join(str(x) for x in gv)
            en = str(en).strip()
            gv = str(gv).strip()
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
print(f"  JSONL subtotal: {parallel_count:,} parallel sentences (deduplicated)")

# --- manx-search-data CSVs (david-allison/manx-search-data) ---
# If the repo is cloned alongside this one, ingest its aligned CSV data.
# Each document.csv has columns: Manx, English, Diplomatic[, Notes]
import csv

MANX_SEARCH_DIR = os.path.join(REPO_ROOT, '..', 'manx-search-data', 'OpenData')
if not os.path.isdir(MANX_SEARCH_DIR):
    # Also check a sibling clone location
    for candidate in [
        os.path.join(os.path.expanduser('~'), 'manx-search-data', 'OpenData'),
        os.path.join(REPO_ROOT, 'data', 'manx-search-data', 'OpenData'),
    ]:
        if os.path.isdir(candidate):
            MANX_SEARCH_DIR = candidate
            break

msd_count = 0
if os.path.isdir(MANX_SEARCH_DIR):
    print(f"\n  --- manx-search-data CSVs ---")
    csv_files = []
    for root, dirs, files in os.walk(MANX_SEARCH_DIR):
        for f in files:
            if f == 'document.csv':
                csv_files.append(os.path.join(root, f))

    for csv_path in sorted(csv_files):
        rel_path = os.path.relpath(csv_path, MANX_SEARCH_DIR)
        source_name = os.path.dirname(rel_path).replace(os.sep, '/')
        try:
            with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as fh:
                reader = csv.reader(fh)
                header = next(reader, None)
                if not header or len(header) < 2:
                    continue

                # Detect column order from headers
                h0 = header[0].strip().lower()
                h1 = header[1].strip().lower()
                if h0 == 'manx' and h1 == 'english':
                    gv_col, en_col = 0, 1
                elif h0 == 'english' and h1 == 'manx':
                    gv_col, en_col = 1, 0
                else:
                    # Skip non-bilingual CSVs (Speaker,Manx; Manx,Manx2; etc.)
                    continue

                for row in reader:
                    manx = row[gv_col].strip() if len(row) > gv_col else ''
                    eng = row[en_col].strip() if len(row) > en_col else ''

                    # Quality filters: skip empty, too short, or too long
                    if not manx or not eng or len(manx) < 5 or len(eng) < 5:
                        continue
                    if len(manx) > 2000 or len(eng) > 2000:
                        continue

                    pair_key = (eng.lower(), manx.lower())
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    conn.execute(
                        "INSERT INTO parallel_sentences (english, manx, source, domain) VALUES (?,?,?,?)",
                        (eng, manx, f"manx-search-data/{source_name}", 'corpus')
                    )
                    parallel_count += 1
                    msd_count += 1
        except Exception as e:
            print(f"    Warning: {rel_path}: {e}")

    conn.commit()
    print(f"  manx-search-data: {msd_count:,} new sentences")
else:
    print(f"\n  manx-search-data not found (optional: clone david-allison/manx-search-data alongside this repo)")

print(f"  Subtotal after manx-search-data: {parallel_count:,}")

# --- Kelly Fockleyreen example sentences ---
kelly_pair_count = 0
if kelly_example_pairs:
    print(f"\n  --- Kelly Fockleyreen example sentences ---")
    for en, gv in kelly_example_pairs:
        if len(en) < 5 or len(gv) < 5 or len(en) > 500 or len(gv) > 500:
            continue
        pair_key = (en.lower(), gv.lower())
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        conn.execute(
            "INSERT INTO parallel_sentences (english, manx, source, domain) VALUES (?,?,?,?)",
            (en, gv, 'kelly-fockleyreen/examples', 'mixed')
        )
        parallel_count += 1
        kelly_pair_count += 1
    conn.commit()
    print(f"  Kelly example pairs: {kelly_pair_count:,} new parallel sentences")

# --- Modern bilingual content from manxtxt/ ---
# Ansooryn (exercise answers), Combine Result units, and Facebook translations
# contain aligned English↔Manx sentence pairs in contemporary language.

manxtxt_pairs = 0

if os.path.isdir(MANXTXT):
    print(f"\n  --- manxtxt/ modern bilingual content ---")

    def add_pair(eng, gv, source):
        """Add a parallel pair if not already seen."""
        global parallel_count, manxtxt_pairs
        eng = eng.strip()
        gv = gv.strip()
        # Clean up numbering prefixes like "1 ", "2\t"
        eng = re.sub(r'^\d+[\s\t]+', '', eng)
        gv = re.sub(r'^\d+[\s\t]+', '', gv)
        # Remove trailing page numbers
        eng = re.sub(r'\s+\d+\s*$', '', eng)
        gv = re.sub(r'\s+\d+\s*$', '', gv)
        if not eng or not gv or len(eng) < 3 or len(gv) < 3:
            return
        if len(eng) > 500 or len(gv) > 500:
            return
        pair_key = (eng.lower(), gv.lower())
        if pair_key in seen_pairs:
            return
        seen_pairs.add(pair_key)
        conn.execute(
            "INSERT INTO parallel_sentences (english, manx, source, domain) VALUES (?,?,?,?)",
            (eng, gv, source, 'modern')
        )
        parallel_count += 1
        manxtxt_pairs += 1

    # --- 1. Ansooryn (exercise answer files) ---
    # Format: tab-separated Manx\tEnglish or English\tManx pairs
    # with "Cur Baarle" / "Cur Gaelg" direction markers
    ansooryn_files = sorted([
        f for f in os.listdir(MANXTXT)
        if 'ansooryn' in f.lower() or 'anssooryn' in f.lower()
    ])
    ans_count = 0
    for fname in ansooryn_files:
        fpath = os.path.join(MANXTXT, fname)
        with open(fpath, 'r', encoding='utf-8-sig', errors='replace') as fh:
            direction = None  # 'gv2en' or 'en2gv'
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                # Detect direction markers
                if 'Cur Baarle' in line or 'Put English' in line:
                    direction = 'gv2en'
                    continue
                elif 'Cur Gaelg' in line or 'Put Manx' in line:
                    direction = 'en2gv'
                    continue
                elif line.startswith('Unnid') or line.startswith('Unit'):
                    direction = None
                    continue

                if direction and '\t' in line:
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        left = parts[0].strip()
                        right = parts[1].strip()
                        # Skip header-like lines
                        if any(x in left.lower() for x in ['unnid', 'unit', 'cur baarle', 'cur gaelg', 'put english', 'put manx']):
                            continue
                        if direction == 'gv2en':
                            add_pair(right, left, f'manxtxt/ansooryn/{fname}')
                            ans_count += 1
                        elif direction == 'en2gv':
                            add_pair(left, right, f'manxtxt/ansooryn/{fname}')
                            ans_count += 1
    print(f"    Ansooryn exercises: {ans_count} pairs")

    # --- 1b. Inline GV+EN pairs from ansooryn + Combine Result ---
    # Some lines have "Manx sentence English sentence" without tabs
    # e.g. "Ta mee cho mooar as elefant I'm as big as an elephant"
    # Also extract vocabulary items like "Coardail\t-\tAgree"
    inline_files = ansooryn_files + sorted([
        f for f in os.listdir(MANXTXT)
        if f.startswith('Combine') and f.endswith('.txt')
    ])
    inline_count = 0
    en_starts = r'(?:I(?:\'m|\s)|You(?:\'re|\s)|He(?:\'s|\s)|She(?:\'s|\s)|We(?:\'re|\s)|They(?:\'re|\s)|It(?:\'s|\s)|Do\s|Does\s|Did\s|Is\s|Are\s|Was\s|Were\s|Who\s|What\s|Where\s|When\s|Why\s|How\s|Am\s|Isn\'t|Aren\'t|Doesn\'t|Don\'t|Won\'t|Wouldn\'t|There(?:\'s|\s))'
    gv_starts = r'(?:Ta\s|Vel\s|Cha\s|Nagh\s|Share\s|Nhare\s|Bare\s|T\'eh\s|T\'ee\s|T\'ad\s|Neeym\s|Nee\s|Ren\s|Va\s|Row\s|Hie\s)'
    for fname in inline_files:
        fpath = os.path.join(MANXTXT, fname)
        with open(fpath, 'r', encoding='utf-8-sig', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not line or len(line) < 10:
                    continue
                # Match: GV sentence followed by EN sentence on same line
                m = re.match(rf'^({gv_starts}.{{5,60}}?)\s+({en_starts}.+)$', line)
                if m:
                    gv = m.group(1).strip()
                    en = m.group(2).strip()
                    # Reject if EN part contains another GV sentence (table row with multiple pairs)
                    if re.search(gv_starts, en[5:]):
                        continue
                    if len(gv) > 5 and len(en) > 5 and len(en) < 200:
                        add_pair(en, gv, f'manxtxt/inline/{fname}')
                        inline_count += 1

                # Also extract vocabulary items: "Word\t-\tManx word"
                vocab_m = re.match(r'^(\w[\w\s]*?)\t-\t(\w[\w\s]*?)$', line)
                if vocab_m:
                    en_w = vocab_m.group(1).strip()
                    gv_w = vocab_m.group(2).strip()
                    if len(en_w) > 1 and len(gv_w) > 1:
                        conn.execute(
                            "INSERT OR IGNORE INTO dictionary (english, manx, part_of_speech, source) VALUES (?,?,?,?)",
                            (en_w, gv_w, '', f'manxtxt/vocab/{fname}')
                        )
    print(f"    Inline GV+EN pairs: {inline_count} pairs")

    # --- 2. Combine Result units (bilingual exercises) ---
    # Same format as ansooryn but within the combined course units
    combine_files = sorted([
        f for f in os.listdir(MANXTXT)
        if f.startswith('Combine') and f.endswith('.txt')
    ])
    combine_count = 0
    for fname in combine_files:
        fpath = os.path.join(MANXTXT, fname)
        with open(fpath, 'r', encoding='utf-8-sig', errors='replace') as fh:
            direction = None
            lines = fh.readlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                i += 1
                if not line:
                    continue
                if 'Cur Baarle' in line or 'Put English' in line:
                    direction = 'gv2en'
                    continue
                elif 'Cur Gaelg' in line or 'Put Manx' in line:
                    direction = 'en2gv'
                    continue
                elif line.startswith('UNNID') or line.startswith('Unnid'):
                    direction = None
                    continue
                elif line.startswith('Vocabulary') or line.startswith('Duillag'):
                    direction = None
                    continue

                if direction and '\t' in line:
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        left = parts[0].strip()
                        right = parts[1].strip()
                        if any(x in left.lower() for x in ['unnid', 'cur baarle', 'cur gaelg', 'put english', 'put manx']):
                            continue
                        if not right or right.startswith('_'):
                            continue
                        if direction == 'gv2en':
                            add_pair(right, left, f'manxtxt/combine/{fname}')
                            combine_count += 1
                        elif direction == 'en2gv':
                            add_pair(left, right, f'manxtxt/combine/{fname}')
                            combine_count += 1
    print(f"    Combine Result units: {combine_count} pairs")

    # --- 3. Facebook translations ---
    # Format: English line followed by Manx translation on next line
    fb_file = os.path.join(MANXTXT, 'facebook%20translations%20and%20info.txt')
    fb_count = 0
    if os.path.exists(fb_file):
        with open(fb_file, 'r', encoding='utf-8-sig', errors='replace') as fh:
            lines = [l.strip() for l in fh.readlines()]
            i = 0
            while i < len(lines) - 1:
                line = lines[i]
                i += 1
                # Skip comments and blanks
                if not line or line.startswith('#'):
                    continue
                # Look for tab-separated pairs on same line
                if '\t' in line:
                    parts = line.split('\t', 1)
                    if len(parts) == 2 and parts[0] and parts[1]:
                        add_pair(parts[0].strip(), parts[1].strip(), 'manxtxt/facebook')
                        fb_count += 1
                    continue
                # Otherwise look for EN line followed by GV line
                next_line = lines[i] if i < len(lines) else ''
                if next_line and not next_line.startswith('#'):
                    # Heuristic: if line is English-looking and next is Manx-looking
                    # Facebook file alternates EN/GV
                    add_pair(line, next_line, 'manxtxt/facebook')
                    fb_count += 1
                    i += 1
        print(f"    Facebook translations: {fb_count} pairs")

    # --- 4. Food glossary ---
    # Format: "English term - Manx term" per line
    food_file = os.path.join(MANXTXT, 'Glossary%20of%20food%20terms.txt')
    food_count = 0
    if os.path.exists(food_file):
        with open(food_file, 'r', encoding='utf-8-sig', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if ' - ' in line and not line.startswith('English') and not line.startswith('Kindly'):
                    parts = line.split(' - ', 1)
                    if len(parts) == 2:
                        eng = parts[0].strip()
                        gv = parts[1].strip()
                        if eng and gv and len(eng) > 1 and len(gv) > 1:
                            # Add to dictionary table too
                            dict_key = (gv.lower(), eng.lower()[:50])
                            conn.execute(
                                "INSERT OR IGNORE INTO dictionary (english, manx, part_of_speech, source) VALUES (?,?,?,?)",
                                (eng, gv, 'n', 'manxtxt/food-glossary')
                            )
                            food_count += 1
        print(f"    Food glossary: {food_count} entries (dictionary)")

    # --- 5. Computer terminology ---
    # Format: "term n/vb\tManx equivalent"
    comp_file = os.path.join(MANXTXT, 'computer%20terminology%20argeed%20by%20Coonceil%20ny%20Gaelgey.txt')
    comp_count = 0
    if os.path.exists(comp_file):
        with open(comp_file, 'r', encoding='utf-8-sig', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('\ufeff'):
                    continue
                if '\t' in line:
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        eng_raw = parts[0].strip()
                        gv = parts[1].strip()
                        # Strip POS tags from English
                        eng = re.sub(r'\s+[nv](?:b|pl)?\s*$', '', eng_raw).strip()
                        eng = re.sub(r'\s+adj(?:,\s*pp)?\s*$', '', eng).strip()
                        if eng and gv and len(eng) > 1:
                            pos = ''
                            if re.search(r'\bvb\b', eng_raw):
                                pos = 'v'
                            elif re.search(r'\bn\b', eng_raw):
                                pos = 'n'
                            elif re.search(r'\badj\b', eng_raw):
                                pos = 'adj'
                            conn.execute(
                                "INSERT OR IGNORE INTO dictionary (english, manx, part_of_speech, source) VALUES (?,?,?,?)",
                                (eng, gv, pos, 'manxtxt/computer-terminology')
                            )
                            comp_count += 1
        print(f"    Computer terminology: {comp_count} entries (dictionary)")

    # --- 6. focCnyG 4/5/6 and CnyG 2007 (modern approved terminology) ---
    # Format: "English term [POS] Manx term" with line wrapping
    cnyg_files = [
        ('focCnyG4.txt', 'focCnyG4'),
        ('focCnyG5.txt', 'focCnyG5'),
        ('focCnyG6.txt', 'focCnyG6'),
        ('Coonceil%20ny%20Gaelgey%20terms%20upto%202007.txt', 'CnyG-2007'),
    ]
    cnyg_count = 0
    for fname, source_label in cnyg_files:
        fpath = os.path.join(MANXTXT, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, 'r', encoding='utf-8-sig', errors='replace') as fh:
            content = fh.read()
        # These files have entries like:
        # "abolish vb moogh, mooghey"
        # "access n cair f -entreil"
        # Split on lines, try to parse English term + POS + Manx
        for line in content.split('\n'):
            line = line.strip()
            if not line or len(line) < 4:
                continue
            # Skip headers and meta
            if line.startswith('BAARLE') or line.startswith('Coonceil') or line.startswith('Fockleyreen') or line.startswith('focCnyG') or line.startswith('Cur magh') or line.startswith('('):
                continue

            # Try to match: English [POS] Manx
            # POS markers: n, vb, adj, npl, adv, pp, pref
            m = re.match(r'^(.+?)\s+(?:n(?:pl)?|vb|adj|adv|pp|pref)\s+(.+)$', line)
            if m:
                eng = m.group(1).strip()
                gv = m.group(2).strip()
                # Extract POS
                pos_m = re.search(r'\b(n(?:pl)?|vb|adj|adv)\b', line[len(eng):len(eng)+10])
                pos = ''
                if pos_m:
                    p = pos_m.group(1)
                    if p.startswith('n'):
                        pos = 'n'
                    elif p == 'vb':
                        pos = 'v'
                    elif p == 'adj':
                        pos = 'adj'
                    elif p == 'adv':
                        pos = 'adv'
                # Clean Manx: remove gender markers and pl info for dictionary
                gv_clean = re.sub(r'\s+[mf]\s', ' ', gv)
                gv_clean = re.sub(r',\s*pl\s+.*$', '', gv_clean).strip()
                gv_clean = re.sub(r'\s+[mf]$', '', gv_clean).strip()

                if eng and gv_clean and len(eng) > 1 and len(gv_clean) > 1:
                    conn.execute(
                        "INSERT OR IGNORE INTO dictionary (english, manx, part_of_speech, source) VALUES (?,?,?,?)",
                        (eng, gv_clean, pos, f'manxtxt/{source_label}')
                    )
                    cnyg_count += 1
    print(f"    CnyG terminology (4/5/6/2007): {cnyg_count} entries (dictionary)")

    # --- 7. Nobles Hospital report (bilingual healthcare text) ---
    # This is continuous Manx prose — add as Manx-only for potential back-translation
    # but extract any inline translations where English terms appear in brackets
    nobles_file = os.path.join(MANXTXT, 'nobleshospital%20gaelg%20(new).txt')
    nobles_count = 0
    if os.path.exists(nobles_file):
        with open(nobles_file, 'r', encoding='utf-8-sig', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                # Look for patterns like "Manx term (English)" or bullet items
                # The Nobles report has section headers in English too
                pass  # Complex format — skip for now, focus on clean bilingual sources
        print(f"    Nobles Hospital: skipped (Manx prose, needs back-translation)")

    conn.commit()
    print(f"  manxtxt/ total: {manxtxt_pairs:,} new parallel pairs")

# --- UD_Manx-Cadhan (Universal Dependencies treebank) ---
# Contains syntactically parsed Manx sentences, many with English translations.
# Mostly modern prose — Wikipedia, news, contemporary writing.
UD_DIR = None
for candidate in [
    os.path.join(REPO_ROOT, '..', 'UD_Manx-Cadhan'),
    os.path.join(os.path.expanduser('~'), 'UD_Manx-Cadhan'),
    os.path.join(REPO_ROOT, 'data', 'UD_Manx-Cadhan'),
]:
    if os.path.isdir(candidate):
        UD_DIR = candidate
        break

ud_count = 0
if UD_DIR:
    print(f"\n  --- UD_Manx-Cadhan treebank ---")
    for conllu_file in sorted(os.listdir(UD_DIR)):
        if not conllu_file.endswith('.conllu'):
            continue
        fpath = os.path.join(UD_DIR, conllu_file)
        gv_text = None
        en_text = None
        with open(fpath, 'r', encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if line.startswith('# text = '):
                    gv_text = line[9:].strip()
                elif line.startswith('# text_en = '):
                    en_text = line[12:].strip()
                elif line == '' and gv_text and en_text:
                    if len(en_text) >= 5 and len(gv_text) >= 5:
                        pair_key = (en_text.lower(), gv_text.lower())
                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            conn.execute(
                                "INSERT INTO parallel_sentences (english, manx, source, domain) VALUES (?,?,?,?)",
                                (en_text, gv_text, f'UD_Manx-Cadhan/{conllu_file}', 'modern')
                            )
                            parallel_count += 1
                            ud_count += 1
                    gv_text = None
                    en_text = None
    conn.commit()
    print(f"  UD_Manx-Cadhan: {ud_count:,} new parallel sentences")
else:
    print(f"\n  UD_Manx-Cadhan not found (optional: clone UniversalDependencies/UD_Manx-Cadhan alongside this repo)")

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
