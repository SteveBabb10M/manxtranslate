#!/usr/bin/env python3
"""
Build the Manx translation toolkit SQLite database.

Creates the schema and runs all available ingestion scripts.
Safe to re-run — it rebuilds from scratch each time.

Usage:
    python scripts/build_db.py
"""

import sqlite3
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_DIR, 'data', 'processed', 'manx.db')

SCHEMA = """
-- Core dictionary: English to Manx word lookup
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

-- Inflection forms
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

-- Parallel sentences: aligned English-Manx pairs
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

-- Full-text search on parallel sentences
CREATE VIRTUAL TABLE IF NOT EXISTS parallel_fts USING fts5(
    english, manx, content='parallel_sentences', content_rowid='id'
);

-- Triggers to keep FTS in sync
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

-- Grammar rules
CREATE TABLE IF NOT EXISTS grammar_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    rule_text TEXT NOT NULL,
    examples TEXT,
    source TEXT
);
CREATE INDEX IF NOT EXISTS idx_gram_cat ON grammar_rules(category);

-- Phrases and idioms
CREATE TABLE IF NOT EXISTS phrases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    english TEXT NOT NULL,
    manx TEXT NOT NULL,
    category TEXT,
    source TEXT
);
CREATE INDEX IF NOT EXISTS idx_phrase_english ON phrases(english);

-- Mutations reference
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


def build():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # Remove old DB for clean rebuild
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing database")

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    print(f"Created database schema at {DB_PATH}")

    # Run ingestion scripts
    ingested = []

    # Parallel sentences from JSONL
    from ingest_parallel_jsonl import ingest_jsonl
    jsonl_files = []
    # Check project root and data directories
    for search_dir in [PROJECT_DIR, os.path.join(PROJECT_DIR, 'data', 'raw')]:
        for f in os.listdir(search_dir):
            if f.endswith('.jsonl') and 'parallel' in f.lower():
                jsonl_files.append(os.path.join(search_dir, f))
    
    for jf in jsonl_files:
        count = ingest_jsonl(conn, jf)
        ingested.append(f"  {os.path.basename(jf)}: {count} parallel sentences")

    conn.commit()
    conn.close()

    print(f"\nIngestion complete:")
    for line in ingested:
        print(line)
    print(f"\nDatabase: {DB_PATH}")


if __name__ == '__main__':
    # Add scripts dir to path so imports work
    sys.path.insert(0, SCRIPT_DIR)
    build()
