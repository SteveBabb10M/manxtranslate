# Synthetic Sentence Generation from Kelly Fockleyreen

## Process
Same as the previous high-value lexicon generation (now complete).

Feed rows to a free AI (Gemini/Mistral) in batches of 20.
For each row, generate 3 natural English-Manx parallel sentence pairs 
that use the given word/phrase in context.

## Prompt template
For each batch of 20 rows from the TSV, use:

---
Given these English-Manx vocabulary items, generate 3 natural parallel 
sentence pairs for each that demonstrate the word in everyday modern context.

Format each as JSONL:
{"source": "English sentence", "target": "Manx sentence"}

The Manx should use modern standard orthography. Vary sentence structure 
and context. Include a mix of statements, questions, and negatives.

Vocabulary:
[paste 20 rows here]
---

## Output
JSONL format matching manx_en_combined.jsonl:
{"source": "English sentence", "target": "Manx sentence", "ref": "kelly-synthetic"}

## Scale
8,000 entries × 3 pairs = ~24,000 new parallel sentences
At 20 per batch = 400 batches
