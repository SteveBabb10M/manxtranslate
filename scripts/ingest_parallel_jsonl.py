#!/usr/bin/env python3
"""
Ingest parallel sentences from JSONL files into the database.

Expected format (one JSON object per line):
    {"source": "English text", "target": "Manx text", "ref": "source_name"}

Deduplicates on (english, manx) pairs during ingestion.

Usage:
    python scripts/ingest_parallel_jsonl.py data/raw/manx_parallel_sentences_clean.jsonl

Or called automatically by build_db.py for any *parallel*.jsonl file found in the project.
"""

import json
import sqlite3
import os
import sys


def ingest_jsonl(conn, filepath, domain='general', quality='unreviewed'):
    """
    Ingest a JSONL parallel sentences file into the database.
    
    Returns the number of sentences inserted.
    """
    cursor = conn.cursor()
    
    # Get existing pairs to avoid duplicates
    cursor.execute("SELECT english, manx FROM parallel_sentences")
    existing = set((r[0].lower(), r[1].lower()) for r in cursor.fetchall())
    initial_existing = len(existing)
    
    inserted = 0
    skipped_dupes = 0
    skipped_empty = 0
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print(f"  Warning: bad JSON on line {line_num}, skipping")
                continue
            
            english = obj.get('source', '').strip()
            manx = obj.get('target', '').strip()
            source = obj.get('ref', os.path.basename(filepath))
            
            if not english or not manx:
                skipped_empty += 1
                continue
            
            key = (english.lower(), manx.lower())
            if key in existing:
                skipped_dupes += 1
                continue
            
            existing.add(key)
            cursor.execute(
                "INSERT INTO parallel_sentences (english, manx, source, domain, quality) VALUES (?, ?, ?, ?, ?)",
                (english, manx, source, domain, quality)
            )
            inserted += 1
    
    print(f"  {os.path.basename(filepath)}:")
    print(f"    Inserted: {inserted}")
    if skipped_dupes:
        print(f"    Skipped (duplicates): {skipped_dupes}")
    if skipped_empty:
        print(f"    Skipped (empty): {skipped_empty}")
    if initial_existing:
        print(f"    Already in DB: {initial_existing}")
    
    return inserted


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python ingest_parallel_jsonl.py <file.jsonl> [db_path]")
        sys.exit(1)
    
    filepath = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'processed', 'manx.db'
    )
    
    conn = sqlite3.connect(db_path)
    count = ingest_jsonl(conn, filepath)
    conn.commit()
    conn.close()
    print(f"\nDone. {count} sentences added to {db_path}")
