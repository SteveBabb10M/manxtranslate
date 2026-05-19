# Manx Translation Toolkit

SQLite-backed reference toolkit for translating *The Revestment* into Manx Gaelic.

## What's in the database

| Table | Rows | Source |
|-------|------|--------|
| dictionary | 22,351 | Scannell gv2ga.po (Manx→Irish→English) |
| inflections | 8,213 | Scannell focloir.txt (verb/noun/adj forms) |
| parallel_sentences | 136,497 | JSONL corpus + manx-search-data CSVs |
| grammar_rules | 73 | Wheeler studies, Coonceil ny Gaelgey |
| phrases | 40,919 | Scannell multi-gv.txt |
| mutations | 27,349 | Computed lenition/eclipsis from focloir.txt |

## Quick start

```bash
# Clone (includes pre-built DB via Git LFS)
git clone https://github.com/SteveBabb10M/manxtranslate.git
cd manxtranslate

# Use the translation helper
python -c "
import sys; sys.path.insert(0, 'scripts')
from translate_helper import TranslationHelper
h = TranslationHelper('data/processed/manx.db')
print(h.lookup('house'))
"
```

## Rebuilding the database

To rebuild from source data (optional — the LFS-tracked DB is ready to use):

```bash
# Optional: clone manx-search-data alongside for +5K extra parallel sentences
git clone https://github.com/david-allison/manx-search-data.git ../manx-search-data

python scripts/build_all.py
```

## Project structure

```
scripts/
  build_all.py          # Comprehensive DB builder (all 6 tables)
  translate_helper.py   # Query interface for translation sessions
  yn-caaghstan-screeuee.md  # Manx writing standard v0.3
data/
  scannell/             # Source lexicon files (focloir, pairs, multi-word)
  raw/                  # Cleaned JSONL parallel corpora
  processed/manx.db     # Built database (Git LFS)
```

## Related resources

- HuggingFace models: [manx-mt-en-gv](https://huggingface.co/SteveBabb10M/manx-mt-en-gv) (BLEU 24.83) / [manx-mt-gv-en](https://huggingface.co/SteveBabb10M/manx-mt-gv-en) (BLEU 34.81)
- Live translator: [revestment1765.com/manx-translator.html](https://revestment1765.com/manx-translator.html)
- Corpus source: [david-allison/manx-search-data](https://github.com/david-allison/manx-search-data)
