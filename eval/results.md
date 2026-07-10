# Retrieval eval results

30 hand-labeled questions; 30 dense candidates per question; identical candidate pool with and without Rerank.

| Metric | Embed only | Embed + Rerank |
|---|---|---|
| hit@1 | 60.0% | 53.3% |
| hit@3 | 90.0% | 90.0% |
| hit@5 | 93.3% | 90.0% |
| MRR | 0.760 | 0.709 |

## Per-question ranks (rank of gold clause, 1 = best)

| Question | Gold clause | Dense rank | Reranked rank |
|---|---|---|---|
| q01 | B-9.8.8.3. | 1 | 1 |
| q02 | B-9.8.8.1. | 2 | 2 |
| q03 | B-9.8.8.5. | 5 | 9 |
| q04 | B-9.8.2.1. | 1 | 1 |
| q05 | B-9.8.2.2. | 1 | 3 |
| q06 | B-9.8.7.4. | 1 | 1 |
| q07 | B-9.8.7.1. | 1 | 1 |
| q08 | B-9.9.10.1. | 1 | 1 |
| q09 | B-9.9.10.1. | 2 | 2 |
| q10 | B-9.5.3.1. | 1 | 1 |
| q11 | B-9.10.19.1. | 1 | 1 |
| q12 | B-9.10.19.3. | 2 | 2 |
| q13 | B-9.3.1.7. | 1 | 1 |
| q14 | B-9.12.2.2. | 2 | 1 |
| q15 | B-9.11.1.1. | 2 | 2 |
| q16 | B-3.2.5.12. | 1 | 2 |
| q17 | B-3.8.3.3. | 1 | 1 |
| q18 | B-3.1.10.2. | 2 | 1 |
| q19 | B-3.4.3.2. | 2 | 2 |
| q20 | B-3.4.6.4. | 1 | 3 |
| q21 | B-4.1.5.3. | 1 | 2 |
| q22 | B-4.1.6.2. | 1 | 2 |
| q23 | B-9.4.2.2. | 2 | 3 |
| q24 | A-1.4.1.2. | miss | miss |
| q25 | C-2.2.1.1. | 1 | 1 |
| q26 | B-9.9.9.1. | 1 | 1 |
| q27 | B-9.32.3.3. | 2 | 1 |
| q28 | B-9.36.2.6. | 9 | 6 |
| q29 | B-9.35.2.1. | 1 | 1 |
| q30 | B-9.8.4.2. | 1 | 1 |
