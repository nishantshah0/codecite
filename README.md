# CodeCite

Citation-grounded RAG over the **National Building Code of Canada 2020**, built on the full Cohere stack: **Embed v4** for retrieval, **Rerank 3.5** for precision, **Command A** for grounded generation with clause-level citations.

Ask it a building-code question and it answers from the Code itself, citing the exact Articles and Sentences:

```
$ codecite ask "What is the minimum height for a guardrail on a residential deck?"

Guards must generally be not less than 1 070 mm high. However, exterior guards
serving not more than one dwelling unit may be 900 mm high where the walking
surface is not more than 1 800 mm above finished ground level. ...

--- Citations ---
  Division B, Article 9.8.8.3. (Height of Guards), PDF p. 844
```

## Why this exists

Building codes are exactly the kind of document RAG is hard on: 1,500 pages, deeply nested legal numbering (Division B → Part 9 → Section 9.8 → Subsection 9.8.8 → Article 9.8.8.3 → Sentence (2)), two-column typesetting, cross-references everywhere, and answers that must be *exact* — "not less than 1 070 mm" is a legal requirement, not a vibe. As a civil engineering student I wanted the reference tool I wish existed, and it doubles as a testbed for measuring what each stage of a retrieval pipeline actually contributes.

## Architecture

```
NBC 2020 PDF (1,528 pages)
   │  column-aware extraction (PyMuPDF text blocks sorted into reading order)
   ▼
clause parser  ──  Division / Part / Section / Subsection / Article hierarchy,
   │               appendix notes (A-x.x.x.x), TOC + attribution-table filtering
   ▼
~3,000 structure-aware chunks  ──  one chunk per Article, each prefixed with a
   │                               context header carrying its full clause path
   ▼
Cohere Embed v4 (search_document) ──► local vector index (NumPy, exact cosine)
                                      or Postgres + pgvector (optional backend)

query ──► Embed v4 (search_query) ──► top-30 dense candidates
                 ──► Cohere Rerank 3.5 ──► top-8
                 ──► Command A with documents= ──► answer + span-level citations
                       mapped back to clause IDs and PDF pages
```

### Design decisions worth discussing

- **Chunk = Article, not fixed-size windows.** Clause boundaries are the citation boundaries. A 512-token window that straddles Articles 9.8.8.2 and 9.8.8.3 can't be cited honestly; a chunk that *is* Article 9.8.8.3 can.
- **Context headers close the vocabulary gap.** A user asks about "deck railing height"; Sentence text says "1 070 mm high" and only the headings say "Guards". Prepending `Division B, Part 9 (Housing and Small Buildings), … Article 9.8.8.3 (Height of Guards)` to the embedded text puts the heading vocabulary into the vector.
- **The parser has to fight the PDF.** Real problems handled: two-column reading order, running headers/footers, a copyright watermark mid-page, per-Part tables of contents whose entries look exactly like article headings (filtered by dot leaders), attribution tables that re-list every article number with objective codes (would have shadowed every real article — skipped), and a table cell that reads "Appendix C, °C" and must not be mistaken for the start of Appendix C.
- **Duplicate clause numbers are real.** Division A, B and C each have a Part 1, so "1.4.1.2." is ambiguous — every chunk is keyed by division + clause.
- **Known limitation: tables.** Numeric table cells (span tables, snow-load tables) scramble under text extraction. Table *prose* (notes, conditions) survives and lands in the right chunk; cell-accurate table QA would need a layout-aware table extractor.

## Eval: what does Rerank buy?

`eval/questions.jsonl` holds 30 hand-written question → answer → gold-clause triples, each verified against the extracted corpus (the answer's key quantity literally appears in the gold chunk). The harness retrieves the same 30 dense candidates per question and scores the ranking with and without Rerank — same pool, same k, so the delta is attributable to Rerank alone.

```
python eval/run_eval.py
```

| Metric | Embed only | Embed + Rerank |
|---|---|---|
| hit@1 | _run the eval_ | _run the eval_ |
| hit@3 | _run the eval_ | _run the eval_ |
| hit@5 | _run the eval_ | _run the eval_ |
| MRR | _run the eval_ | _run the eval_ |

Results are written to `eval/results.md` with per-question ranks. (Numbers pending: the harness runs against a live index; see Quickstart.)

## Quickstart

```bash
git clone https://github.com/nishantshah0/codecite && cd codecite
pip install -e .[dev]

# 1. get the corpus (free from the Government of Canada; ~24 MB)
python scripts/download_nbc.py

# 2. get a free trial key at https://dashboard.cohere.com/api-keys
export COHERE_API_KEY=...        # Windows: setx COHERE_API_KEY "..."

# 3. parse, chunk, embed, index (~3,000 chunks, ~35 embed calls)
codecite ingest

# 4. ask questions
codecite ask "How wide does an exit stair in a house need to be?"
codecite ask "Do I need a smoke alarm in every bedroom?" --show-hits
codecite ask "..." --no-rerank    # feel the difference yourself

# 5. reproduce the eval table
python eval/run_eval.py
```

Optional Postgres/pgvector backend (e.g. Supabase): `pip install -e .[pg]` and set `CODECITE_DATABASE_URL` — the same `ingest`/`ask` commands then index and search in Postgres.

## Tests

`pytest` runs fully offline: extraction is tested against synthetic two-column PDFs generated in-test, the parser against constructed page text covering every filtering rule above, and the retrieve→rerank→generate pipeline against a fake Cohere client — plus integrity checks on the eval set. CI runs on every push.

## Legal

The NBC 2020 is © NRC; it is free to access but not redistributable, so this repo ships the *pipeline*, not the Code — the download script fetches the official PDF from publications.gc.ca. This tool is a study aid, not a substitute for the Code or professional judgment; verify anything that matters against the official text and your province's amendments (Ontario, Quebec, BC and Alberta administer their own variants).
