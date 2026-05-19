#!/usr/bin/env python3
"""
Translation helper — query interface for use during translation sessions.

Provides methods to look up vocabulary, find parallel examples, and search
grammar rules from the SQLite database.

Usage (interactive):
    python scripts/translate_helper.py "search term"

Usage (from Claude sessions):
    from translate_helper import TranslateHelper
    helper = TranslateHelper()
    helper.find_parallel("the king believed")
    helper.lookup_word("king")
"""

import sqlite3
import os
import sys
import json


class TranslateHelper:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..', 'data', 'processed', 'manx.db'
            )
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def find_parallel(self, query, limit=10):
        """
        Full-text search across parallel sentences.
        Searches both English and Manx sides.
        Returns matching sentence pairs ranked by relevance.
        """
        cursor = self.conn.execute("""
            SELECT p.english, p.manx, p.source, p.domain
            FROM parallel_fts fts
            JOIN parallel_sentences p ON p.id = fts.rowid
            WHERE parallel_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        results = [dict(row) for row in cursor.fetchall()]
        return results
    
    def find_parallel_like(self, query, limit=10):
        """
        Fallback LIKE search when FTS doesn't match well.
        Useful for partial words or Manx lookups.
        """
        pattern = f'%{query}%'
        cursor = self.conn.execute("""
            SELECT english, manx, source, domain
            FROM parallel_sentences
            WHERE english LIKE ? OR manx LIKE ?
            LIMIT ?
        """, (pattern, pattern, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def lookup_word(self, word, limit=10):
        """Look up a word in the dictionary (English or Manx)."""
        cursor = self.conn.execute("""
            SELECT english, manx, part_of_speech, gender, notes
            FROM dictionary
            WHERE english LIKE ? OR manx LIKE ?
            LIMIT ?
        """, (f'%{word}%', f'%{word}%', limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def find_inflection(self, word, limit=10):
        """Find inflection forms for a base word."""
        cursor = self.conn.execute("""
            SELECT base_form, inflected_form, inflection_type, part_of_speech, pattern_class
            FROM inflections
            WHERE base_form LIKE ? OR inflected_form LIKE ?
            LIMIT ?
        """, (f'%{word}%', f'%{word}%', limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def find_grammar(self, query, limit=5):
        """Search grammar rules by category or content."""
        pattern = f'%{query}%'
        cursor = self.conn.execute("""
            SELECT category, rule_text, examples
            FROM grammar_rules
            WHERE category LIKE ? OR rule_text LIKE ?
            LIMIT ?
        """, (pattern, pattern, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def find_phrase(self, query, limit=10):
        """Search phrases and idioms."""
        pattern = f'%{query}%'
        cursor = self.conn.execute("""
            SELECT english, manx, category
            FROM phrases
            WHERE english LIKE ? OR manx LIKE ?
            LIMIT ?
        """, (pattern, pattern, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def stats(self):
        """Show database statistics."""
        tables = ['dictionary', 'inflections', 'parallel_sentences', 
                  'grammar_rules', 'phrases', 'mutations']
        stats = {}
        for table in tables:
            try:
                cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            except:
                stats[table] = 0
        return stats
    
    def close(self):
        self.conn.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python translate_helper.py <search_term> [--type parallel|word|grammar|phrase]")
        print("\nExamples:")
        print('  python translate_helper.py "the king"')
        print('  python translate_helper.py "genitive" --type grammar')
        print('  python translate_helper.py "ree" --type word')
        sys.exit(0)
    
    query = sys.argv[1]
    search_type = 'parallel'
    if '--type' in sys.argv:
        idx = sys.argv.index('--type')
        if idx + 1 < len(sys.argv):
            search_type = sys.argv[idx + 1]
    
    helper = TranslateHelper()
    
    print(f"\n{'='*60}")
    print(f"Database stats: {json.dumps(helper.stats(), indent=2)}")
    print(f"{'='*60}")
    
    if search_type == 'parallel':
        print(f"\nParallel sentences matching '{query}':\n")
        results = helper.find_parallel(query)
        if not results:
            results = helper.find_parallel_like(query)
            if results:
                print("(via LIKE fallback)\n")
        for r in results:
            print(f"  EN: {r['english']}")
            print(f"  GV: {r['manx']}")
            print(f"  [{r['source']}]\n")
    
    elif search_type == 'word':
        print(f"\nDictionary entries for '{query}':\n")
        for r in helper.lookup_word(query):
            print(f"  {r['english']} = {r['manx']} ({r['part_of_speech'] or '?'}, {r['gender'] or '?'})")
    
    elif search_type == 'grammar':
        print(f"\nGrammar rules matching '{query}':\n")
        for r in helper.find_grammar(query):
            print(f"  [{r['category']}] {r['rule_text'][:120]}")
    
    elif search_type == 'phrase':
        print(f"\nPhrases matching '{query}':\n")
        for r in helper.find_phrase(query):
            print(f"  {r['english']} = {r['manx']}")
    
    helper.close()


if __name__ == '__main__':
    main()
