#!/usr/bin/env python3
"""
Ingest Wheeler inflection studies (1, 3, 4, 5, 6), Kelly Grammar online (Ch. 9, 11)
and OCR grammars (manx_soc_gramm.txt, verb_syntax.txt) into the manxtranslate DB.

Usage:
    python scripts/ingest_wheeler_kelly.py path/to/manx.db

Each source is processed by its own function so failures stay isolated.
Inserts are deduplicated against existing rows.
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
import urllib.request
import html
from html.parser import HTMLParser


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
LM_TEXTS = os.path.join(REPO_ROOT, 'data', 'raw', 'learnmanx_texts')
RAW_DIR = os.path.join(REPO_ROOT, 'data', 'raw')

WHEELER_1 = os.path.join(LM_TEXTS, 'Manx_Gaelic_inflection_1._Noun_plurals.txt')
WHEELER_3 = os.path.join(LM_TEXTS, 'Manx_Gaelic_inflection_3._Noun_paradigms.txt')
WHEELER_4 = os.path.join(LM_TEXTS, 'Manx_Gaelic_inflection_4._Adjectives.txt')
WHEELER_5 = os.path.join(LM_TEXTS, 'Manx_Gaelic_inflection_5._Verbs.txt')
WHEELER_6 = os.path.join(LM_TEXTS, 'Manx_Gaelic_inflection_6._Initial_mutati.txt')

MANX_SOC = os.path.join(RAW_DIR, 'manx_soc_gramm.txt')
VERB_SYNTAX = os.path.join(RAW_DIR, 'verb_syntax.txt')

KELLY_CH9_URL = 'https://www.isle-of-man.com/manxnotebook/manxsoc/msvol02/chap09.htm'
KELLY_CH11_URL = 'https://www.isle-of-man.com/manxnotebook/manxsoc/msvol02/chap11.htm'


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
ARROW_RE = re.compile(r"\s*(?:[—–-]+>|→|->|—>|>|\^)\s*")


def normalise_arrow_line(s: str) -> str:
    """Normalise arrow separators in a fragment to a single ASCII '->'."""
    return ARROW_RE.sub(' -> ', s)


def clean_token(tok: str) -> str:
    """Strip surrounding punctuation and whitespace from a Manx token."""
    tok = tok.strip()
    tok = tok.strip('.,;:!?"`«»“”’‘()[]{}')
    tok = re.sub(r'\s+', ' ', tok)
    return tok


def is_plausible_manx(tok: str) -> bool:
    """Heuristic filter: reject obvious OCR garbage tokens."""
    if not tok or len(tok) < 2:
        return False
    if len(tok) > 40:
        return False
    if not re.search(r"[A-Za-zçÇ]", tok):
        return False
    # reject tokens whose alpha ratio is too low
    alpha = sum(1 for c in tok if c.isalpha() or c in "çÇ'ʼ’-")
    if alpha / max(1, len(tok)) < 0.6:
        return False
    return True


class DedupInserter:
    """Tracks existing (base, inflected, type) and (category, rule) to avoid dupes."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.infl_keys: set[tuple[str, str, str]] = set()
        self.rule_keys: set[tuple[str, str]] = set()
        for b, i, t in conn.execute(
            "SELECT base_form, inflected_form, inflection_type FROM inflections"
        ):
            self.infl_keys.add((
                (b or '').lower().strip(),
                (i or '').lower().strip(),
                (t or '').lower().strip(),
            ))
        for c, r in conn.execute("SELECT category, rule_text FROM grammar_rules"):
            self.rule_keys.add((
                (c or '').strip(),
                (r or '').strip(),
            ))

    def add_inflection(self, base, inflected, infl_type, pos=None,
                       pattern_class=None, notes=None) -> bool:
        if not base or not inflected:
            return False
        key = (base.lower().strip(), inflected.lower().strip(),
               infl_type.lower().strip())
        if key in self.infl_keys:
            return False
        self.infl_keys.add(key)
        self.conn.execute(
            "INSERT INTO inflections (base_form, inflected_form, inflection_type,"
            " part_of_speech, pattern_class, notes) VALUES (?,?,?,?,?,?)",
            (base, inflected, infl_type, pos, pattern_class, notes),
        )
        return True

    def add_rule(self, category, rule_text, examples=None, source=None) -> bool:
        if not category or not rule_text:
            return False
        key = (category.strip(), rule_text.strip())
        if key in self.rule_keys:
            return False
        self.rule_keys.add(key)
        self.conn.execute(
            "INSERT INTO grammar_rules (category, rule_text, examples, source)"
            " VALUES (?,?,?,?)",
            (category, rule_text, examples, source),
        )
        return True


# ------------------------------------------------------------
# Source 1: Wheeler Study 1 — Noun Plurals
# ------------------------------------------------------------
# OCR rendered Wheeler's class labels variably:
#   "1" = 1
#   "lai" / "la1" = 1a1
#   "la2" = 1a2
#   "lb" = 1b
#   "lc2" / "lc3" = 1c2 / 1c3
#   "lei" appears for BOTH 1c1 (-nyn) and 1e1 (-eeyn): we disambiguate by suffix context
#   "le2" = 1e2
#   "Idl"/"Id1" = 1d1; "Id2" = 1d2; "Id3" = 1d3
#   "If" = 1f
CLASS_HEAD_RE = re.compile(
    r"\b[Cc]lass\s+"
    r"(?P<cls>[1lI][a-fA-F]?[0-9ilI]?|If|Idl|Id1|Id2|Id3|"
    r"lai|la1|la2|lb|lc1|lc2|lc3|le1|le2|lei|2|3|4|5)"
    r"\b",
)
# Suffix context inside (or shortly after) a class heading helps disambiguate "lei"
SUFFIX_CONTEXT_RE = re.compile(
    r"in\s*[-‐]?\s*(?P<sfx>yn|ghyn|aghyn|dyn|jyn|nyn|inyn|eynyn|tyn|teeyn|teenyn|eeyn|eenyn|in|ee)"
)

# Allowed plural-class tokens after canonicalisation
KNOWN_PLURAL_CLASSES = {
    '1', '1a1', '1a2', '1b', '1c1', '1c2', '1c3', '1d1', '1d2', '1d3',
    '1e1', '1e2', '1f', '2', '3', '4', '5',
}

CLASS_DESCRIPTIONS = {
    '1':   "Plural in -yn (default class). Suffix -yn added directly to the stem.",
    '1a1': "Plural in -ghyn. Used with stems ending in a stressed final vowel.",
    '1a2': "Plural in -aghyn. Default for stems ending in unstressed -ey; also some in -agh.",
    '1b':  "Plural in -dyn or -jyn. Rare; ~9 nouns total.",
    '1c1': "Plural in -nyn. ~10 nouns, several with alternative inflections.",
    '1c2': "Plural in -inyn. A handful of nouns; most have regular class 1 alternatives.",
    '1c3': "Plural in -eynyn. Very rare.",
    '1d1': "Plural in -tyn (or -tçhyn). Often with stem vowel and consonant changes.",
    '1d2': "Plural in -teeyn. Stems ending in /n/ or slender /lj/.",
    '1d3': "Plural in -teenyn. Rare.",
    '1e1': "Plural in -eeyn. Often with loss of unstressed final syllable (-ey/-agh/-in).",
    '1e2': "Plural in -eenyn. Rare; e.g. anmeenyn from annym.",
    '1f':  "Plural in -in. Very rare; e.g. clein from clea.",
    '2':   "Plural in -ee. Many agent nouns from -agh; e.g. cummaltagh -> cummaltee.",
    '3':   "Plural by stem change: broad final C replaced by slender (cabbyl -> cabbil).",
    '4':   "Plural by stem vowel change (with following slender consonant); e.g. mac -> mec.",
    '5':   "Wholly irregular, suppletive or syncretic plurals (ben -> mraane).",
}


def canonical_plural_class(raw: str | None, context: str = "") -> str | None:
    """Normalise OCR variants of a plural class label to canonical form.

    `context` is the surrounding text used to disambiguate OCR collisions
    (e.g. "lei" → 1c1 vs 1e1, depending on the suffix mentioned nearby).
    """
    if not raw:
        return None
    s = raw.strip()
    # Leading I/l → 1
    s = re.sub(r"^[lI](?=[a-fA-F0-9il])", "1", s)
    s = s.lower()
    # Trailing 'i' or 'l' OCR'd from '1'
    s = re.sub(r"([a-f])[il]$", r"\g<1>1", s)
    # "1if" → "1f" (rare)
    if s == "1if":
        s = "1f"
    # Disambiguate "lei" → 1c1 (-nyn) or 1e1 (-eeyn) by suffix mentioned nearby
    if s == "1e1":
        # If the original token was "lei" (i.e. raw started with "le"/"Le")
        # and the context says "-nyn", interpret as 1c1.
        raw_lower = raw.lower()
        if raw_lower in ('lei', 'le1'):
            sfx_m = SUFFIX_CONTEXT_RE.search(context or '')
            if sfx_m:
                sfx = sfx_m.group('sfx').lower()
                if sfx == 'nyn':
                    s = '1c1'
                elif sfx == 'eeyn':
                    s = '1e1'
    if s in KNOWN_PLURAL_CLASSES:
        return s
    return None


GLOSS_RE = re.compile(r"[‘'`]([^‘’'`]+?)[’'`]")
# Match a single Manx word (letters, çÇ, internal ' or -)
TOKEN_RE = r"[A-Za-zçÇ][A-Za-zçÇ’'\-]*"
# Arrow pair: WORD ARROW WORD. Arrow forms include em-dash+>, em-dash+>+blacksquare,
# en-dash+>, hyphen(s)+>, unicode →, plain ^ between letters (OCR for →).
ARROW_PAIR_RE = re.compile(
    r"(?P<a>" + TOKEN_RE + r")"
    r"(?:\s*(?:[—–\-]+>■?|→|\^)\s*|\^)"
    r"(?P<b>" + TOKEN_RE + r")"
)


# A line is a "section header" if it begins with Class/class/Other class/Likewise, class
SECTION_HEADER_RE = re.compile(
    r"^\s*(?:Other\s+|Likewise,\s+)?[Cc]lass(?:\s*[a-z]*\s+|\s+)"
    r"(?P<cls>[1lI][a-fA-F]?[0-9ilI]?|If|Idl|Id1|Id2|Id3|lai|la1|la2|"
    r"lb|lc1|lc2|lc3|le1|le2|lei|2|3|4|5)"
    r"\b"
)


def extract_plural_entries(text: str):
    """Yield (singular, plural, gloss, pattern_class) tuples from prose text.

    Two-pass: first identify line ranges per class (section headers being
    lines that *begin* with a class heading), then in each range collect
    arrow-paired entries.
    """
    raw_lines = text.splitlines()

    # Pass 1: identify section header lines and the class each starts.
    # A "section" begins at a header line and runs until the next header line.
    section_starts: list[tuple[int, str]] = []  # (line_idx, class)
    for i, ln in enumerate(raw_lines):
        m = SECTION_HEADER_RE.match(ln)
        if not m:
            continue
        # Context for disambiguating OCR-ambiguous "lei" — look at this line
        # plus the next two lines (where suffix info may be).
        context = ' '.join(raw_lines[i:i + 3])
        cand = canonical_plural_class(m.group('cls'), context=context)
        if cand:
            section_starts.append((i, cand))

    if not section_starts:
        return

    # Build (start, end, class) ranges
    ranges: list[tuple[int, int, str]] = []
    for j, (start, cls) in enumerate(section_starts):
        end = section_starts[j + 1][0] if j + 1 < len(section_starts) else len(raw_lines)
        ranges.append((start, end, cls))

    # Pass 2: for each line in each range, extract arrow pairs.
    for start, end, cls in ranges:
        for i in range(start, end):
            line = raw_lines[i]
            if re.match(r"^\d+$", line.strip()):
                continue
            if line.startswith('Manx Gaelic inflection') or line.startswith('Max Wheeler'):
                continue
            # Class heading lines have an arrow within the heading
            # (e.g. "Class 3, sg. broad C —> pl. slender C:"). Strip prefix
            # up to ":" if present so we don't pick up "C → C" pairs.
            entry_text = line
            if i == start and ':' in line:
                entry_text = line.split(':', 1)[1]

            # Also collect a gloss-search window of nearby lines for cases
            # where the entry's gloss wraps to the next line.
            window = ' '.join(raw_lines[i:i + 2])

            for pair_m in ARROW_PAIR_RE.finditer(entry_text):
                singular = clean_token(pair_m.group('a')).rstrip(',.;:')
                plural = clean_token(pair_m.group('b')).rstrip(',.;:')
                if not is_plausible_manx(singular) or not is_plausible_manx(plural):
                    continue
                if singular.lower() == 'class':
                    continue
                # Gloss lookup: nearest single-quoted phrase after the arrow,
                # within the window.
                # Find this match's position in window.
                window_offset = window.find(entry_text)
                tail_start = (window_offset + pair_m.end()) if window_offset >= 0 else pair_m.end()
                tail_gloss = GLOSS_RE.search(window[tail_start:tail_start + 200])
                if not tail_gloss:
                    tail_gloss = GLOSS_RE.search(window[:200])
                gloss = tail_gloss.group(1).strip() if tail_gloss else None
                yield singular, plural, gloss, cls


def split_top_level_comma(s: str) -> list[str]:
    """Split on commas not inside (), [], or single quotes."""
    out = []
    depth = 0
    quote = False
    cur = []
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        elif ch in "‘'`":
            quote = not quote
        elif ch in "’":
            quote = False
        if ch == ',' and depth == 0 and not quote:
            out.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        out.append(''.join(cur))
    return out


def ingest_source_1(conn, dedup) -> tuple[int, int]:
    if not os.path.exists(WHEELER_1):
        print(f"  SKIPPED — file not found: {WHEELER_1}")
        return 0, 0
    text = open(WHEELER_1, encoding='utf-8', errors='replace').read()
    infl_added = 0
    by_class: dict[str, list[tuple[str, str, str | None]]] = {}
    for sing, plur, gloss, cls in extract_plural_entries(text):
        ok = dedup.add_inflection(
            base=sing, inflected=plur, infl_type='plural',
            pos='noun', pattern_class=cls,
            notes=f"gloss: {gloss}" if gloss else None,
        )
        if ok:
            infl_added += 1
        by_class.setdefault(cls, []).append((sing, plur, gloss))

    rules_added = 0
    for cls, examples in sorted(by_class.items()):
        desc = CLASS_DESCRIPTIONS.get(cls,
                                      f"Plural class {cls} (Wheeler study 1).")
        ex_strs = []
        for sing, plur, gloss in examples[:3]:
            piece = f"{sing} -> {plur}"
            if gloss:
                piece += f" '{gloss}'"
            ex_strs.append(piece)
        ok = dedup.add_rule(
            category=f"NOUN:PLURAL:CLASS_{cls.upper()}",
            rule_text=desc,
            examples='; '.join(ex_strs),
            source='Wheeler study 1 (Noun plurals)',
        )
        if ok:
            rules_added += 1
    return infl_added, rules_added


# ------------------------------------------------------------
# Source 2: Wheeler Study 3 — Noun Paradigms
# ------------------------------------------------------------
PARADIGM_RE = re.compile(r"^(?P<para>[A-E][0-9]+[a-z]?)\b")


def ingest_source_2(conn, dedup) -> tuple[int, int]:
    if not os.path.exists(WHEELER_3):
        print(f"  SKIPPED — file not found: {WHEELER_3}")
        return 0, 0
    infl_added = 0
    rules_added = 0
    paradigm_examples: dict[str, list[tuple[str, str, str]]] = {}

    with open(WHEELER_3, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            raw = line.rstrip('\n')
            # Tab-separated rows
            if '\t' not in raw:
                continue
            cells = [c.strip() for c in raw.split('\t')]
            cells = [c for c in cells if c != '']
            if len(cells) < 4:
                continue
            m = PARADIGM_RE.match(cells[0])
            if not m:
                continue
            para = m.group('para')
            # Filter the leading paradigm label out of cells[0] if it has extra text
            singular = clean_token(cells[1])
            genitive = clean_token(cells[2])
            plural = clean_token(cells[3])
            plural_class = cells[4] if len(cells) > 4 else None
            # Reject header-like rows
            if singular.lower() == 'singular' or genitive.lower() == 'genitive':
                continue
            if not is_plausible_manx(singular):
                continue

            if is_plausible_manx(genitive) and genitive.lower() != singular.lower():
                if dedup.add_inflection(
                    base=singular, inflected=genitive, infl_type='genitive',
                    pos='noun', pattern_class=para,
                    notes=f"Wheeler paradigm {para}",
                ):
                    infl_added += 1
            if is_plausible_manx(plural) and plural.lower() != singular.lower():
                # plural class may have OCR noise; pass through canonical if known
                pcls = canonical_plural_class(plural_class) or plural_class
                if dedup.add_inflection(
                    base=singular, inflected=plural, infl_type='plural',
                    pos='noun', pattern_class=pcls,
                    notes=f"Wheeler paradigm {para}",
                ):
                    infl_added += 1
            paradigm_examples.setdefault(para, []).append(
                (singular, genitive, plural))

    for para, examples in sorted(paradigm_examples.items()):
        ex_strs = [f"{s} - {g} - {p}" for s, g, p in examples[:3]]
        rule_text = (f"Noun paradigm {para}: singular - genitive - plural pattern,"
                     f" from Wheeler's classification of Cregeen's inflected nouns.")
        if dedup.add_rule(
            category=f"NOUN:PARADIGM:{para.upper()}",
            rule_text=rule_text,
            examples='; '.join(ex_strs),
            source='Wheeler study 3 (Noun paradigms)',
        ):
            rules_added += 1
    return infl_added, rules_added


# ------------------------------------------------------------
# Source 3: Wheeler Study 4 — Adjectives
# ------------------------------------------------------------
def ingest_source_3(conn, dedup) -> tuple[int, int]:
    if not os.path.exists(WHEELER_4):
        print(f"  SKIPPED — file not found: {WHEELER_4}")
        return 0, 0
    infl_added = 0
    rules_added = 0

    with open(WHEELER_4, encoding='utf-8', errors='replace') as fh:
        lines = fh.readlines()

    section = None  # 'comp_ee', 'comp_ey', 'comp_ey_vowel_change',
                    # 'comp_suppletive', 'comp_identical', 'plural'

    section_examples: dict[str, list[tuple[str, str, str | None]]] = {}

    for raw in lines:
        line = raw.rstrip('\n')
        low = line.strip().lower()

        # section transitions
        if 'comparative in -ee' in low or 'comparatives in -ee' in low:
            section = 'comp_ee'
            continue
        if 'comparatives in -ey' in low or 'comparative in -ey' in low:
            section = 'comp_ey'
            continue
        if 'comp. -ey with vowel change' in low or 'vowel change' in low and 'comp' in low:
            section = 'comp_ey_vowel_change'
            continue
        if 'suppletive' in low and 'comp' in low:
            section = 'comp_suppletive'
            continue
        if 'comparative form that is identical to the positive' in low:
            section = 'comp_identical'
            continue
        if 'adjectives with inflected plural' in low:
            section = 'plural'
            continue
        # Reset on prose paragraph headers
        if line.startswith('Manx Gaelic inflection'):
            continue

        # Heuristic: tab-separated table rows
        if '\t' not in line:
            continue
        cells = [c.strip() for c in line.split('\t')]
        cells = [c for c in cells if c]

        # 3-col layout: adj, comp, gloss
        # 6-col layout: adj, comp, gloss, adj, comp, gloss
        # 2-col layout for plural: adj, comp/plural; gloss may be missing
        # Try to extract triplets
        triplets = []
        if len(cells) >= 6:
            triplets.append(cells[0:3])
            triplets.append(cells[3:6])
        elif len(cells) >= 3:
            triplets.append(cells[0:3])
        else:
            continue

        for trip in triplets:
            if len(trip) < 2:
                continue
            base = clean_token(trip[0])
            inflected = clean_token(trip[1])
            gloss = clean_token(trip[2]) if len(trip) >= 3 else None
            if not is_plausible_manx(base) or not is_plausible_manx(inflected):
                continue
            # skip rows that look like headers
            if base.lower() in ('adj.', 'positive', 'adj', 'comp.', 'comp'):
                continue

            # plural section: handle "aegey Bx142" suffix
            if section == 'plural':
                bib_m = re.search(r"\bBx(\d+)", inflected)
                notes_parts = [f"gloss: {gloss}"] if gloss else []
                if bib_m:
                    notes_parts.append(f"Bible occurrences: {bib_m.group(1)}")
                    inflected = re.sub(r"\s*Bx\d+", '', inflected).strip()
                if not is_plausible_manx(inflected):
                    continue
                if dedup.add_inflection(
                    base=base, inflected=inflected, infl_type='plural',
                    pos='adjective', pattern_class='adj_plural_-ey',
                    notes='; '.join(notes_parts) or None,
                ):
                    infl_added += 1
                section_examples.setdefault(section, []).append(
                    (base, inflected, gloss))
                continue

            # Comparative sections
            pattern_class = {
                'comp_ee': 'comp_ee',
                'comp_ey': 'comp_ey',
                'comp_ey_vowel_change': 'comp_ey_vowel_change',
                'comp_suppletive': 'comp_suppletive',
                'comp_identical': 'comp_identical',
            }.get(section)
            if pattern_class is None:
                continue
            if dedup.add_inflection(
                base=base, inflected=inflected, infl_type='comparative',
                pos='adjective', pattern_class=pattern_class,
                notes=f"gloss: {gloss}" if gloss else None,
            ):
                infl_added += 1
            section_examples.setdefault(section, []).append(
                (base, inflected, gloss))

    rule_specs = {
        'comp_ee':
            ("ADJECTIVE:COMPARATIVE:EE",
             "Adjectives ending in -agh form their comparative by replacing"
             " -agh with -ee (Wheeler: ~334 examples in Cregeen)."),
        'comp_ey':
            ("ADJECTIVE:COMPARATIVE:EY",
             "Adjectives form their comparative by adding -ey to the stem;"
             " most are monosyllabic."),
        'comp_ey_vowel_change':
            ("ADJECTIVE:COMPARATIVE:EY_VOWEL_CHANGE",
             "Comparative in -ey accompanied by a stem-vowel change"
             " (e.g. ard -> yrjey, dowin -> diuney)."),
        'comp_suppletive':
            ("ADJECTIVE:COMPARATIVE:SUPPLETIVE",
             "Suppletive comparatives — wholly different stem"
             " (faggys -> (s)niessey, olk -> (s)messey)."),
        'comp_identical':
            ("ADJECTIVE:COMPARATIVE:IDENTICAL",
             "Adjectives whose comparative is identical to the positive form"
             " (e.g. aarloo, bannee, maynrey)."),
        'plural':
            ("ADJECTIVE:PLURAL",
             "Plural adjectives are formed by adding -ey to the stem;"
             " used attributively in plural contexts."),
    }
    for sect, (cat, desc) in rule_specs.items():
        exs = section_examples.get(sect, [])
        ex_str = '; '.join(f"{b} -> {i}" + (f" '{g}'" if g else '')
                            for b, i, g in exs[:3])
        if dedup.add_rule(
            category=cat,
            rule_text=desc,
            examples=ex_str or None,
            source='Wheeler study 4 (Adjectives)',
        ):
            rules_added += 1
    return infl_added, rules_added


# ------------------------------------------------------------
# Source 4: Wheeler Study 5 — Verbs
# ------------------------------------------------------------
VN_SECTION_HEADERS = [
    # Order matters — more specific phrases first.
    ('Verbs without verbal noun', 'no_vn'),
    ('Verbs with suffixless verbal nouns', 'vn_suffixless'),
    ('Verbs with verbal nouns in -ey', 'vn_ey'),
    ('Verbs with verbal nouns in -aghey', 'vn_aghey'),
    ('Verbs with verbal nouns in -aghtyn', 'vn_aghtyn'),
    ('Verbs with verbal nouns in -aght', 'vn_aght'),
    ('Verbs with verbal nouns in -agh', 'vn_agh'),
    ('Verbs with verbal nouns in -ail', 'vn_ail'),
    ('Verbs with verbal nouns in -al', 'vn_al'),
    ('Verbs with verbal nouns in -in', 'vn_in'),
    ('Verbs with verbal nouns in -tyn', 'vn_tyn'),
]

# Cells that are pure English glosses or paradigm-label headers we should skip
PARADIGM_HEADER_CELLS = {
    'base', 'verbal noun', 'past', 'ptcp', 'imperative', 'imperative 2sg',
    'imperative 2pl', 'root', 'roots', 'gerund', 'perfect', 'participle',
    'present', 'present independent', 'present dependent',
    'future independent', 'future dependent', 'future relative',
    'past independent', 'past dependent', 'conditional', 'paradigm',
    'singular', 'genitive', 'plural', 'notes', 'emphatic',
    'conditional independent 1sg', 'conditional independent other',
    'conditional dependent 1sg', 'conditional dependent other',
    'future independent 1sg', 'future independent 1pl', 'future independent 2/3',
    'future dependent 1sg', 'future dependent 1pl', 'future dependent 2/3',
    'future relative 1sg', 'future relative 1pl', 'future relative 2/3',
    'dy + vn',
}

# Conservative Manx-token detector: must look like a Manx word with at least
# one Manx-distinctive feature OR be a known short Manx particle.
MANX_FEATURE_RE = re.compile(
    r"(çÇ|aa|ee|oo|yy|yn$|ail$|al$|ee$|ey$|agh$|agh[ye]|aght$|aghyn$|"
    r"ail$|al$|ey$|iagh$|iaght$|eet$|eit$|eyrey|raght|^ny|^dy|^ag|^yn)",
    re.IGNORECASE,
)
# Common English words we know appear as glosses in this file's tables
ENGLISH_GLOSS_WORDS = {
    'please', 'prevail', 'wall', 'band', 'veil', 'justice', 'change',
    'chew', 'plait', 'cloak', 'clay', 'shoe', 'number', 'call', 'arm',
    'forfeit', 'feather', 'fodder', 'take', 'root', 'spring', 'grill',
    'halt', 'set', 'dog', 'on', 'give', 'alms', 'beg', 'shit', 'peep',
    'whip', 'dry', 'after', 'rain', 'cover', 'mud', 'labour', 'allot',
    'rust', 'piece', 'pepper', 'pluck', 'hoard', 'impound', 'warn',
    'stripe', 'freeze', 'riot', 'wipe', 'rick', 'seal', 'sound',
    'vanish', 'squat', 'smash', 'sort', 'hack', 'hoe', 'spey', 'geld',
    'snort', 'hiss', 'astonish', 'gape', 'thatch', 'forebode', 'trot',
    'try', 'idly', 'stroll', 'grow', 'complain', 'jeer', 'swim',
    'extirpate', 'swell', 'calve', 'grind', 'waft', 'milk', 'betray',
    'judge', 'boil', 'bruise', 'reap', 'lose', 'cast', 'wear', 'wean',
    'flee', 'seek', 'heat', 'turn', 'harrow', 'dig', 'play', 'tease',
    'grieve', 'hop', 'shake', 'corrode', 'sell', 'ruin', 'crush',
    'create', 'give', 'put', 'send', 'dance', 'lament', 'attempt',
    'eat', 'desire', 'pay', 'name', 'wring', 'weave', 'rest', 'wait',
    'keep', 'weed-corn', 'steal', 'wrestle', 'entreat', 'hatch', 'brew',
    'drive', 'mention', 'wonder', 'tell', 'rise', 'drink', 'forget',
    'shut', 'warp', 'suck', 'cavil', 'forgive', 'read', 'melt', 'leap',
    'lie', 'down', 'rot', 'deliver', 'stagger', 'swear', 'cure', 'mock',
    'sweat', 'reproach', 'suspect', 'pant', 'choose', 'govern', 'divide',
    'run', 'write', 'push', 'stir', 'lurk', 'hunt', 'suppose', 'sharpen',
    'lick', 'up', 'walk', 'shed', 'daub', 'paint', 'surname', 'creep',
    'spin', 'sit', 'shine', 'soak', 'woo', 'sprinkle', 'strive',
    'destroy', 'weld', 'converse', 'alight', 'draw', 'pick', 'thaw',
    'measure', 'plough', 'ebb', 'abate', 'travel', 'envy', 'roll',
    'horse', 'need', 'row', 'graze', 'petition', 'argue', 'make',
    'bare', 'indulge', 'drown', 'bargain', 'baptize', 'dwell', 'live',
    'feed', 'enliven', 'blossom', 'stare', 'taste', 'form', 'into',
    'ball', 'cloud', 'trouble', 'roast', 'blister', 'shoe', 'fallow',
    'dash', 'vow', 'inspire', 'coax', 'break', 'thicken', 'intr',
    'roar', 'glory', 'cut', 'with', 'nails', 'hooves', 'sting', 'act',
    'rope', 'heather', 'speak', 'ironically', 'guard', 'shackle',
    'bestow', 'kneel', 'polish', 'come', 'out', 'of', 'the', 'ground',
    'excite', 'provoke', 'bite', 'grip', 'sun', 'air', 'pain', 'hold',
    'frown', 'jeer',
}


def is_manx_inflection(token: str) -> bool:
    """Stricter check than is_plausible_manx, intended for verb-table cells.

    Accepts: token has a Manx-distinctive feature, OR has 4+ chars and
    contains characteristic doubled letters or suffixes.
    """
    if not is_plausible_manx(token):
        return False
    t = token.lower().strip('-')
    if t in ENGLISH_GLOSS_WORDS:
        return False
    # Multi-word: not a single inflection
    if ' ' in token:
        return False
    if MANX_FEATURE_RE.search(t):
        return True
    # Hyphenated forms like d-aase, d-eayrt, j-eeck are valid past forms
    if re.match(r"^[a-z]-[a-zçÇ]{2,}", t):
        return True
    # Otherwise reject short word that looks like English
    if len(t) <= 5 and re.match(r"^[a-z]+$", t):
        return False
    # Accept ç-containing tokens regardless
    if 'ç' in token or 'Ç' in token:
        return True
    # Default: accept tokens >= 5 chars that pass is_plausible
    return len(t) >= 5


SECTION_LAYOUTS = {
    # name -> (vn_col, past_col, ptcp_col)
    # vn_col=None means VN is not present in the table.
    'no_vn':         (None, 1, 2),  # Base | Past | Ptcp | gloss
    'vn_suffixless': (1, 2, 3),     # Base | VN | Past | Ptcp | gloss
    'vn_ey':         (1, 2, 3),
    'vn_aghey':      (1, 2, 3),
    'vn_aghtyn':     (1, 2, 3),
    'vn_aght':       (1, 2, 3),
    'vn_agh':        (1, 2, 3),
    'vn_ail':        (1, 2, 3),
    'vn_al':         (1, 2, 3),
    'vn_in':         (1, 2, 3),
    'vn_tyn':        (1, 2, 3),
}


def ingest_source_4(conn, dedup) -> tuple[int, int]:
    if not os.path.exists(WHEELER_5):
        print(f"  SKIPPED — file not found: {WHEELER_5}")
        return 0, 0
    infl_added = 0
    rules_added = 0

    with open(WHEELER_5, encoding='utf-8', errors='replace') as fh:
        text = fh.read()
    lines = text.splitlines()

    current_section: str | None = None
    section_counts: dict[str, int] = {}

    for raw in lines:
        line = raw.rstrip('\n')

        # Section detection (longest header phrase first, hence sorted list)
        for header, label in sorted(VN_SECTION_HEADERS, key=lambda x: -len(x[0])):
            if header in line:
                current_section = label
                break
        if line.strip().startswith('Manx Gaelic inflection'):
            continue

        if '\t' not in line:
            continue
        # Preserve empty cells (use multiple-tab splitting that keeps gaps).
        cells = [c.strip() for c in line.split('\t')]
        if len(cells) < 2 or not cells[0]:
            continue

        # Base may be given as "alt1 alt2"; take first plausible token only.
        raw_base = cells[0].replace('(', '').replace(')', '')
        first_word = raw_base.split()[0] if raw_base.split() else ''
        base = clean_token(first_word)
        if not is_plausible_manx(base):
            continue
        first_lower = base.lower()
        if first_lower in PARADIGM_HEADER_CELLS:
            continue
        # Reject rows whose base has unexpected suffix digits (OCR footnote markers)
        if re.search(r"\d", base):
            continue

        if current_section is None:
            continue

        layout = SECTION_LAYOUTS.get(current_section)
        if layout is None:
            continue
        vn_col, past_col, ptcp_col = layout

        def get(col):
            if col is None or col >= len(cells):
                return ''
            v = cells[col].replace('(', '').replace(')', '').strip()
            return v

        notes_base = f"Wheeler study 5, section: {current_section}"

        def insert_alts(value, infl_type):
            nonlocal infl_added
            if not value:
                return
            for alt in re.split(r"\s+|~|,", value):
                alt = clean_token(alt).strip('-')
                if not alt or alt.lower() == base.lower():
                    continue
                if not is_manx_inflection(alt):
                    continue
                if dedup.add_inflection(
                    base=base, inflected=alt, infl_type=infl_type,
                    pos='verb', pattern_class=current_section,
                    notes=notes_base,
                ):
                    infl_added += 1

        if vn_col is not None:
            insert_alts(get(vn_col), 'verbal_noun')
        insert_alts(get(past_col), 'past')
        insert_alts(get(ptcp_col), 'past_participle')

        section_counts[current_section] = section_counts.get(current_section, 0) + 1

    # Verb mutation rules (Table 1 in Wheeler study 5)
    mutation_rules = [
        ("VERB:MUTATION:IMPERATIVE",
         "Imperative: independent radical; no dependent/relative mutation.",
         "toig (imperative of toiggal)"),
        ("VERB:MUTATION:FUTURE",
         "Future indicative: independent radical, dependent Nasalization 3 (n' before V,"
         " optional for f-), relative Lenition 1.",
         "toigym / doiggym / hoiggym"),
        ("VERB:MUTATION:CONDITIONAL",
         "Conditional: independent Lenition 1, dependent Nasalization 3 (n' before V,"
         " optional for f-).",
         "hoiggin / doiggin"),
        ("VERB:MUTATION:PAST_REGULAR",
         "Past (regular): both independent and dependent Lenition 1, d- prefix before"
         " an initial vowel.",
         "hoig / hoig; d-aase from aase"),
        ("VERB:MUTATION:PAST_IRREGULAR",
         "Past (irregular): independent Lenition 1 (d- before V); dependent Nasalization 3.",
         "hug / dug from cur"),
        ("VERB:MUTATION:GERUND",
         "Gerund: g- prefixed before initial vowel.",
         "gymmyrkey from ymmyrkey"),
        ("VERB:MUTATION:VN_AFTER_DY",
         "Verbal noun after dy, y, my, dty, ny (masc.): Lenition 1.",
         "dy hoiggal from toiggal; dy yannoo from jannoo"),
        ("VERB:MUTATION:VN_AFTER_NY_FEM",
         "Verbal noun after ny (fem.): Radical (no mutation).",
         "ny toiggal"),
        ("VERB:MUTATION:VN_AFTER_NYN",
         "Verbal noun after nyn: Nasalization 1.",
         "nyn dhie from thie"),
        ("VERB:MUTATION:VN_AFTER_ER_PERFECT",
         "Verbal noun after er (Perfect tense): Nasalization 2, with n- prefixed before V.",
         "er n'ymmyrkey; er gholl"),
        ("VERB:NASALIZATION_3",
         "Nasalization 3 (voicing) mappings: p->b, t->d, çh->j, k/c->g, qu->gu, f->v;"
         " others remain radical.",
         "p -> b, t -> d, k -> g, f -> v"),
        ("VERB:IMPERATIVE",
         "Imperative singular = verb base; plural adds -jee (Biblical Manx) or adds shiu.",
         "toig / toigjee; jean / jeanjee"),
        ("VERB:CONDITIONAL_INFLECTION",
         "Conditional: -in for 1sg, -agh + subject for other persons.",
         "hoiggin / hoiggagh ad"),
        ("VERB:FUTURE_INFLECTION",
         "Future independent has -ee for non-1st persons; -ym (1sg), -mayd (1pl);"
         " dependent lacks -ee.",
         "toiggee, toiggym, toigmayd; doig (dependent)"),
        ("VERB:RELATIVE_FUTURE",
         "Relative future: -ys for non-1st-person (e.g. brishys); -ym for 1sg, -mayd 1pl.",
         "brishys, brishym, brishysmayd"),
        ("VERB:EPENTHESIS",
         "Stems ending in awkward consonant clusters insert epenthetic [ə] (written -y- next"
         " to broad consonants, -i- next to slender) in suffix-less forms.",
         "ceaghl- -> imperative ceaghil, past ceaghil"),
    ]
    for cat, rule, examples in mutation_rules:
        if dedup.add_rule(
            category=cat,
            rule_text=rule,
            examples=examples,
            source='Wheeler study 5 (Verbs)',
        ):
            rules_added += 1

    # VN suffix classification rules — one per section that yielded entries
    section_descriptions = {
        'no_vn': "Verbs lacking a verbal noun in Cregeen (~69 verbs, ~7%)."
                 " Some are defective; many use only periphrastic constructions.",
        'vn_suffixless': "Verbs whose verbal noun has no suffix; the VN matches the base"
                         " or differs only orthographically (~127 verbs).",
        'vn_ey': "Verbs with verbal noun in -ey (or -ghey after a vowel-final base) — the"
                 " largest single class (~249 verbs, ~28%).",
        'vn_aghey': "Verbs with verbal noun in -aghey (variant of -ey after a stem ending in"
                    " -agh or after a vowel-final stem).",
        'vn_aght': "Verbs with verbal noun in -aght (or -aghtyn).",
        'vn_aghtyn': "Verbs with verbal noun in -aghtyn.",
        'vn_agh': "Verbs with verbal noun in -agh.",
        'vn_al': "Verbs with verbal noun in -al.",
        'vn_ail': "Verbs with verbal noun in -ail (often from -ay/-ai stems).",
        'vn_in': "Verbs with verbal noun in -in (rare).",
        'vn_tyn': "Verbs with verbal noun in -tyn (rare).",
    }
    for sect, desc in section_descriptions.items():
        cnt = section_counts.get(sect, 0)
        if cnt == 0:
            continue
        if dedup.add_rule(
            category=f"VERB:VN_CLASS:{sect.upper()}",
            rule_text=desc,
            examples=f"{cnt} verbs in Cregeen (Wheeler study 5).",
            source='Wheeler study 5 (Verbs)',
        ):
            rules_added += 1

    return infl_added, rules_added


# ------------------------------------------------------------
# Source 5: Wheeler Study 6 — Initial Mutations after `er`
# ------------------------------------------------------------
PERFECT_ENTRY_RE = re.compile(
    r"(?P<verb>[a-zçA-ZÇ][a-zçA-ZÇ’'\-]+)\s*:\s*er\s+"
    r"(?P<mut>(?:n[’']\s*)?[a-zçA-ZÇ’'\-]+)"
    r"(?:\s*\((?P<count>\d+)\))?",
)
TABLE_ROW_RE = re.compile(
    r"^(?P<verb>[a-zçA-ZÇ][a-zçA-ZÇ’'\-]+)\s+"
    r"(?P<nas_form>er\s+n[’']\s*[a-zçA-ZÇ’'\-]+)?\s*(?P<n>\d+)?\s*"
    r"(?P<len_form>er\s+[a-zçA-ZÇ’'\-]+(?:\s+magh)?)?\s*(?P<l>\d+)?\s*"
    r"(?P<total>\d+)?\s+(?P<pct>\d+)%?\s*$",
)


def ingest_source_5(conn, dedup) -> tuple[int, int]:
    if not os.path.exists(WHEELER_6):
        print(f"  SKIPPED — file not found: {WHEELER_6}")
        return 0, 0
    infl_added = 0
    rules_added = 0

    text = open(WHEELER_6, encoding='utf-8', errors='replace').read()
    # Strip out "(x)" epenthesis markers inside forms (e.g. "ho(y)lley" -> "hoylley")
    # while keeping enclosing punctuation outside the form intact.
    text_clean = re.sub(r"\(([a-zçÇ]+)\)", r"\1", text)

    # Catch "verb: er XXX (N)" pattern anywhere — the most reliable signal
    for m in PERFECT_ENTRY_RE.finditer(text_clean):
        verb = clean_token(m.group('verb'))
        mut = clean_token(m.group('mut'))
        # Reconstruct full perfect: "er <mut>" (mut already contains optional n')
        if not is_plausible_manx(verb) or not is_plausible_manx(mut):
            continue
        # Reject if mut is just "n" or a bare prefix
        if len(mut.replace("’", '').replace("'", '').strip('n -')) < 2:
            continue
        # Reject category labels like "YEE:" (all uppercase, used as section headers)
        if verb.isupper() and len(verb) <= 4:
            continue
        perfect_form = f"er {mut}"
        count = m.group('count')
        notes = f"Wheeler study 6"
        if count:
            notes += f"; Bible occurrences: {count}"
        if dedup.add_inflection(
            base=verb, inflected=perfect_form, infl_type='perfect',
            pos='verb', pattern_class='er_perfect',
            notes=notes,
        ):
            infl_added += 1

    # Group rules
    group_rules = [
        ("VERB:MUTATION:ER_PERFECT:P_B_M_S",
         "Initial p-, b-, m-, and s- verbs invariably undergo Lenition 1 in the"
         " Perfect tense er construction.",
         "er phaagey, er vrishey, er vooghey, er hirrey"),
        ("VERB:MUTATION:ER_PERFECT:VOWEL",
         "Vowel-initial verbs take prefixed n' in the Perfect tense (Nasalization).",
         "er n'aarlaghey, er n'eeck, er n'irree, er n'ymmyrkey"),
        ("VERB:MUTATION:ER_PERFECT:T",
         "Most t-initial verbs take Lenition 1 invariably (er h-). Variable verbs"
         " include tuittym (98% nas.), taghyrt (96% nas.), troggal (23% nas.),"
         " tayrn (16% nas.), treigeil (12% nas.), toiggal (5% nas.).",
         "er hilgey, er duittym, er hroggal, er hayrn"),
        ("VERB:MUTATION:ER_PERFECT:CH",
         "Most çh-initial verbs take Lenition 1 invariably (er h-). Variable verbs"
         " include çheet (100% nas.), çherraghtyn (73% nas.), çhyrmaghey (50%),"
         " çhyndaa (44%), çhaglym (17%), çhebbal (17%).",
         "er heet (rare), er jeet (633x); er jyndaa ~ er hyndaa"),
        ("VERB:MUTATION:ER_PERFECT:D",
         "Verbs beginning with d- always take Lenition 1 (d -> gh, hence er gh-).",
         "er ghellal, er gheayrtey, er gheyrey, er ghoostey"),
        ("VERB:MUTATION:ER_PERFECT:J",
         "j-initial verbs: jarrood and jeeaghyn always lenition (er yarrood, er"
         " yeeaghyn). jannoo strongly favours nasalization (98% er n'yannoo)."
         " jiooldey (75% nas.), jeigh (38% nas.).",
         "er n'yannoo, er n'yiooldey; er yeeaghyn"),
        ("VERB:MUTATION:ER_PERFECT:K",
         "k/c-initial verbs nearly always take Lenition 1 (er ch-). Only cosney"
         " shows notable nasalization (8%).",
         "er chosney, er chionnaghey, er choyrt"),
        ("VERB:MUTATION:ER_PERFECT:G",
         "g-initial verbs mostly take Lenition 1. goll strongly favours"
         " nasalization (79% er n'gholl); goaill the opposite (80% er ghoaill)."
         " gi- before V is spelt gh- or yi- (yi- is ~79% preferred).",
         "er ghra, er n'gholl, er ghoaill, er yiarey"),
        ("VERB:MUTATION:ER_PERFECT:F",
         "f-initial verbs: nasalization is dominant for most (fakin 94%, fosley"
         " 94%, fuirriaght 86%, feaysley 83%, freayll 62%); fockley magh is the"
         " main lenition-favourer (3% nas.).",
         "er vakin, er vosley, er n'ockley magh"),
    ]
    for cat, rule, examples in group_rules:
        if dedup.add_rule(
            category=cat,
            rule_text=rule,
            examples=examples,
            source='Wheeler study 6 (Initial mutation after er)',
        ):
            rules_added += 1

    # Individual high-frequency variation stats as rules
    stat_lines = [
        ("tuittym", "er duittym", "er huittym", 98, 2),
        ("taghyrt", "er daghyrt", "er haghyrt", 96, 4),
        ("troggal", "er droggal", "er hroggal", 23, 77),
        ("tayrn",   "er dayrn",   "er hayrn",   16, 84),
        ("treigeil","er dreigeil","er hreigeil",12, 88),
        ("toiggal", "er doiggal", "er hoiggal",  5, 95),
        ("çheet",   "er jeet",    "er heet",   100, 0),
        ("çhyndaa", "er jyndaa",  "er hyndaa",  44, 56),
        ("jannoo",  "er n'yannoo","er yannoo",  98, 2),
        ("jiooldey","er n'yiooldey","er yiooldey",75,25),
        ("jeigh",   "er n'yeigh", "er yeigh",   38, 62),
        ("cosney",  "er gosney",  "er chosney",  8, 92),
        ("goll",    "er n'gholl", "er gholl",   79, 21),
        ("goaill",  "er n'ghoaill","er ghoaill", 20, 80),
        ("geddyn",  "er n'gheddyn","er gheddyn",  5, 95),
        ("fakin",   "er vakin",   "er n'akin",  94, 6),
        ("fosley",  "er vosley",  "er n'osley", 94, 6),
        ("foaddey", "er voaddey", "er n'oaddey",50, 50),
        ("faagail", "er vaagail", "er n'aagail",39, 61),
        ("fockley", "er vockley magh","er n'ockley magh", 3, 97),
    ]
    for verb, nas, lenform, pct_n, pct_l in stat_lines:
        cat = f"VERB:MUTATION:ER_PERFECT:STATS"
        rule = (f"{verb}: er-perfect varies between Nasalization {pct_n}% ({nas})"
                f" and Lenition 1 {pct_l}% ({lenform}) in the Manx Bible.")
        if dedup.add_rule(
            category=cat,
            rule_text=rule,
            examples=f"{nas} / {lenform}",
            source='Wheeler study 6 (Initial mutation after er)',
        ):
            rules_added += 1

    return infl_added, rules_added


# ------------------------------------------------------------
# Sources 6 & 7: Kelly Grammar online (Ch. 9, 11)
# ------------------------------------------------------------
class _PlainTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag in ('br', 'p', 'tr', 'div', 'li', 'td', 'th', 'h1', 'h2', 'h3', 'h4'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip -= 1
        if tag in ('p', 'tr', 'div', 'li', 'h1', 'h2', 'h3', 'h4'):
            self.parts.append('\n')

    def handle_data(self, data):
        if self.skip == 0:
            self.parts.append(data)


def fetch_url(url: str, timeout: float = 30.0) -> str | None:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'manxtranslate/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        # decode (page is Latin-1 or Windows-1252; ISO-8859-1 is safest)
        try:
            return raw.decode('utf-8')
        except UnicodeDecodeError:
            return raw.decode('iso-8859-1', errors='replace')
    except Exception as e:
        print(f"  fetch failed for {url}: {e}")
        return None


def html_to_text(content: str) -> str:
    p = _PlainTextExtractor()
    p.feed(content)
    return html.unescape(''.join(p.parts))


def ingest_source_6_kelly_ch9(conn, dedup) -> tuple[int, int]:
    content = fetch_url(KELLY_CH9_URL)
    if content is None:
        return 0, 0
    text = html_to_text(content)
    infl_added = 0
    rules_added = 0

    # Heuristic: find dictionary-style table rows of the form
    # "Manx-word, English-gloss" or paradigm lines.
    # The page lists declensions; look for arrow-like patterns and "gen."/"plur." markers.
    text_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Look for explicit paradigms in the prose, e.g.
    # "Nom. ben, Gen. mna, Plur. mnaa"
    paradigm_re = re.compile(
        r"\bNom\.\s*([A-Za-zçÇ’'\-]+).*?Gen\.\s*([A-Za-zçÇ’'\-]+)"
        r"(?:.*?(?:Plur|Pl)\.\s*([A-Za-zçÇ’'\-]+))?",
        re.IGNORECASE,
    )
    for ln in text_lines:
        for m in paradigm_re.finditer(ln):
            nom = clean_token(m.group(1))
            gen = clean_token(m.group(2)) if m.group(2) else ''
            plur = clean_token(m.group(3)) if m.group(3) else ''
            if not is_plausible_manx(nom):
                continue
            if is_plausible_manx(gen) and gen.lower() != nom.lower():
                if dedup.add_inflection(
                    base=nom, inflected=gen, infl_type='genitive',
                    pos='noun', pattern_class='kelly_declension',
                    notes='Kelly Grammar Ch.9 (online)',
                ):
                    infl_added += 1
            if is_plausible_manx(plur) and plur.lower() != nom.lower():
                if dedup.add_inflection(
                    base=nom, inflected=plur, infl_type='plural',
                    pos='noun', pattern_class='kelly_declension',
                    notes='Kelly Grammar Ch.9 (online)',
                ):
                    infl_added += 1

    # Add a few overview rules summarizing Kelly's chapter
    summary_rules = [
        ("NOUN:DECLENSION:KELLY",
         "Kelly (1859) treats Manx nouns by declension: nominative, genitive,"
         " dative, vocative, and plural. The genitive shows a stem change,"
         " a suffix in -ey/-ee/-agh, or zero change depending on declension.",
         None),
        ("NOUN:DECLENSION:KELLY:DECLENSIONS",
         "Kelly distinguishes broad/slender vowel endings as governing the"
         " choice of genitive suffix (-a/-e in MS spelling, -ey/-ee in modern).",
         None),
    ]
    for cat, rule, examples in summary_rules:
        if dedup.add_rule(category=cat, rule_text=rule,
                          examples=examples,
                          source='Kelly Grammar Ch.9 (isle-of-man.com)'):
            rules_added += 1

    # Skim text for short rule-like sentences mentioning declensions
    declension_sent_re = re.compile(
        r"\b(?:First|Second|Third|Fourth|Fifth) [Dd]eclension[^.]*\.")
    for sent in declension_sent_re.findall(text):
        sent = re.sub(r"\s+", ' ', sent).strip()
        if 30 < len(sent) < 400:
            if dedup.add_rule(
                category='NOUN:DECLENSION:KELLY',
                rule_text=sent,
                examples=None,
                source='Kelly Grammar Ch.9 (isle-of-man.com)',
            ):
                rules_added += 1

    return infl_added, rules_added


def ingest_source_7_kelly_ch11(conn, dedup) -> tuple[int, int]:
    content = fetch_url(KELLY_CH11_URL)
    if content is None:
        return 0, 0
    text = html_to_text(content)
    infl_added = 0
    rules_added = 0

    # Look for "positive comp. compar." style lines or definition lists with
    # "X, comp. Y" or "X — Y"
    text_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    comp_re = re.compile(
        r"([a-zçÇ’'\-]{2,20})\s*,\s*(?:comp(?:arative)?\.?|compar\.|comp\.)"
        r"\s*([a-zçÇ’'\-]{2,20})",
        re.IGNORECASE,
    )
    for ln in text_lines:
        for m in comp_re.finditer(ln):
            base = clean_token(m.group(1))
            comp = clean_token(m.group(2))
            if (is_plausible_manx(base) and is_plausible_manx(comp)
                    and base.lower() != comp.lower()):
                if dedup.add_inflection(
                    base=base, inflected=comp, infl_type='comparative',
                    pos='adjective', pattern_class='kelly_comparison',
                    notes='Kelly Grammar Ch.11 (online)',
                ):
                    infl_added += 1

    summary_rules = [
        ("ADJECTIVE:COMPARISON:KELLY",
         "Kelly (1859) treats adjective comparison as having two degrees:"
         " positive and comparative (which also serves the superlative)."
         " The comparative is formed by adding -ee (after -agh) or -ey,"
         " sometimes with stem change or suppletion.",
         None),
        ("ADJECTIVE:COMPARISON:KELLY:CONSTRUCTION",
         "The standard comparative construction uses the copula particle s'"
         " before the comparative form (ny s'+adj), with na introducing the"
         " standard of comparison.",
         "ny s'lhiurey na'n thalloo"),
    ]
    for cat, rule, examples in summary_rules:
        if dedup.add_rule(category=cat, rule_text=rule, examples=examples,
                          source='Kelly Grammar Ch.11 (isle-of-man.com)'):
            rules_added += 1

    return infl_added, rules_added


# ------------------------------------------------------------
# Source 8: OCR grammars (Kelly + Thomson)
# ------------------------------------------------------------
def ingest_source_8(conn, dedup) -> tuple[int, int]:
    infl_added = 0
    rules_added = 0

    # ---- 8a: manx_soc_gramm.txt (Kelly OCR) ----
    if os.path.exists(MANX_SOC):
        with open(MANX_SOC, encoding='utf-8', errors='replace') as fh:
            lines = fh.readlines()

        chapter_re = re.compile(r"^CHAPTER\s+([IVX]+)\.?\s*$")
        topic_re = re.compile(r"^Of\s+(?:the\s+)?[A-Z][A-Za-z]+",)
        current_chapter = None
        # Collect (chapter, topic, intro_text)
        i = 0
        while i < len(lines):
            ln = lines[i].rstrip()
            m = chapter_re.match(ln.strip())
            if m:
                current_chapter = m.group(1)
                # Try to read the topic on the next non-empty line
                j = i + 1
                topic = None
                while j < len(lines) and j < i + 5:
                    cand = lines[j].strip()
                    if cand and not cand.startswith('CHAPTER'):
                        topic = cand
                        break
                    j += 1
                # And gather up to ~10 lines of prose after the topic
                body_lines = []
                k = j + 1 if topic else j
                while k < len(lines) and len(body_lines) < 12:
                    b = lines[k].strip()
                    if b and not chapter_re.match(b):
                        body_lines.append(b)
                    elif chapter_re.match(b):
                        break
                    k += 1
                body = ' '.join(body_lines)
                body = re.sub(r"\s+", ' ', body).strip()
                if topic and body:
                    # Truncate body, keep meaningful prose only
                    rule_body = body[:600]
                    cat = f"KELLY:CHAPTER_{current_chapter}"
                    rule_text = f"{topic}: {rule_body}"
                    if dedup.add_rule(
                        category=cat,
                        rule_text=rule_text,
                        examples=None,
                        source='Kelly Grammar OCR (manx_soc_gramm.txt)',
                    ):
                        rules_added += 1
                i = k
                continue
            i += 1
    else:
        print("  manx_soc_gramm.txt not found")

    # ---- 8b: verb_syntax.txt (Thomson) ----
    if os.path.exists(VERB_SYNTAX):
        with open(VERB_SYNTAX, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
        # Section headings in Thomson are short lines, often numbered like "I.", "II.", "1.", "2."
        section_re = re.compile(r"^\s*(?:[IVX]+\.|\d+\.)\s+[A-Z][^\n]{5,80}$", re.MULTILINE)
        # We extract rule-like declarative sentences mentioning key terminology.
        keywords = re.compile(
            r"\b(verb|verbal noun|particle|tense|mood|aspect|VSO|word order|"
            r"dependent|independent|relative|periphrastic|copula|preterite|"
            r"imperfect|perfect|conditional|future|imperative|subjunctive|"
            r"agreement|negation)\b",
            re.IGNORECASE,
        )

        # Split into sentences via simple regex
        sentences = re.split(r"(?<=[.!?])\s+", text)
        emitted = 0
        for s in sentences:
            s = s.strip()
            if len(s) < 40 or len(s) > 400:
                continue
            # OCR garbage filter
            non_alpha = sum(1 for c in s if not (c.isalnum() or c.isspace()
                                                  or c in ".,;:'-—()/"))
            if non_alpha / max(1, len(s)) > 0.15:
                continue
            if not keywords.search(s):
                continue
            s_norm = re.sub(r"\s+", ' ', s)
            cat = 'VERB:SYNTAX:THOMSON'
            if dedup.add_rule(
                category=cat,
                rule_text=s_norm,
                examples=None,
                source='Thomson 1950 Syntax of the Verb (OCR)',
            ):
                rules_added += 1
                emitted += 1
                if emitted >= 40:
                    break
    else:
        print("  verb_syntax.txt not found")

    return infl_added, rules_added


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
SOURCE_FUNCS = [
    ('Source 1 (Wheeler Noun Plurals)',   ingest_source_1),
    ('Source 2 (Wheeler Noun Paradigms)', ingest_source_2),
    ('Source 3 (Wheeler Adjectives)',     ingest_source_3),
    ('Source 4 (Wheeler Verbs)',          ingest_source_4),
    ('Source 5 (Wheeler Mutations)',      ingest_source_5),
    ('Source 6 (Kelly Ch.9 Nouns)',       ingest_source_6_kelly_ch9),
    ('Source 7 (Kelly Ch.11 Adjectives)', ingest_source_7_kelly_ch11),
    ('Source 8 (OCR Grammars)',           ingest_source_8),
]


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest_wheeler_kelly.py path/to/manx.db")
        sys.exit(1)
    db_path = sys.argv[1]
    if not os.path.exists(db_path):
        print(f"DB file not found: {db_path}")
        sys.exit(1)

    only = set(sys.argv[2:])  # optional: list of source indices to run

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    dedup = DedupInserter(conn)

    print(f"Existing inflections: {len(dedup.infl_keys):,}")
    print(f"Existing grammar_rules: {len(dedup.rule_keys):,}")
    print()

    summary: list[tuple[str, int, int]] = []
    for idx, (label, fn) in enumerate(SOURCE_FUNCS, start=1):
        if only and str(idx) not in only:
            continue
        print(f"=== {label} ===")
        try:
            infl, rules = fn(conn, dedup)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"  ERROR in {label}: {e}")
            import traceback
            traceback.print_exc()
            infl, rules = 0, 0
        print(f"  +{infl} inflections, +{rules} grammar_rules")
        summary.append((label, infl, rules))
        print()

    total_i = sum(s[1] for s in summary)
    total_r = sum(s[2] for s in summary)
    cur_i = conn.execute("SELECT COUNT(*) FROM inflections").fetchone()[0]
    cur_r = conn.execute("SELECT COUNT(*) FROM grammar_rules").fetchone()[0]

    print("=" * 60)
    print("=== INGESTION SUMMARY ===")
    print("=" * 60)
    for label, i, r in summary:
        print(f"{label:38s} +{i:6d} inflections, +{r:4d} grammar_rules")
    print("-" * 60)
    print(f"{'TOTAL NEW:':38s} +{total_i:6d} inflections, +{total_r:4d} grammar_rules")
    print(f"{'DB TOTALS:':38s}  {cur_i:6d} inflections,  {cur_r:4d} grammar_rules")
    conn.close()


if __name__ == '__main__':
    main()
