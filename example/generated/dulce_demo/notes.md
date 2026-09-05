# AutoSchemaKG Dulce Demo — Observation Notes

**Date:** 2026-09-05  
**Setup:** `deepseek-chat` via DeepSeek API; input `example/example_data/Dulce.json`; script `run_dulce_demo.py`  
**Output scale:** GraphML validated with **1238 nodes / 2826 edges**. Extraction produced **5 chunks**, **45** entity-relation triples, **154** event-entity records, **118** event-relation triples. Node CSV: **104 entities + 278 events**.

## What worked

- End-to-end pipeline ran successfully: triple extraction → CSV → concept induction → GraphML.
- Some relations are useful and grounded, e.g. `Sam Rivera —combed through→ transmission logs`, `Jordan Hayes —supports→ Agent Alex Mercer`, `Operation: Dulce —involves→ Agent Alex Mercer`.
- Concept induction for key entities is sometimes reasonable, e.g. `Agent Alex Mercer → person, character, agent, operative`; `Operation: Dulce → operation, mission, conspiracy, project`.



## Main issues observed

1. **Over-fine / low-value relations**
  Many triples capture transient narrative actions rather than stable knowledge:  
   `Agent Alex Mercer —scanned→ projectors`, `Agent Alex Mercer —thumbed→ folder`.  
   These are faithful to text but noisy for a KG.
2. **Entity name inconsistency**
  The same character appears as multiple entity nodes, e.g.  
  - Alex: `Agent Alex Mercer` / `Alex Mercer` / `Alex` / `Agent Mercer`  
  - Sam: `Sam Rivera` / `Sam`  
  - Jordan: `Dr. Jordan Hayes` / `Jordan Hayes` / `Jordan`  
   Also noisy entities like `Taylor Cruz's voice`, compound nodes like `Agent Alex Mercer and Dr. Jordan Hayes`.
3. **Event explosion**
  Events dominate the graph (278 events vs 104 entities). Many are near-sentence copies (`Alex flickered a strained smile.`), so the graph becomes a narrative paraphrase graph more than a compact fact graph.
4. **Extraction instability across chunks**
  Chapter 1 appears in multiple chunks with different relationalizations of the same scene (action-level vs more abstract verbs like `questions` / `supports`). Same passage → different schema-ish choices.
5. **Concept quality is mixed**
  Useful abstractions coexist with generic or odd ones (e.g. `Taylor Cruz → person, actor, character, performer, artist`). Event concepts often just restate mood (`nervousness, discomfort...`) without helping cross-document linking much on this tiny corpus.



## Tentative takeaway

AutoSchemaKG is easy to run and good at *covering* narrative detail, but on literary text the bottleneck is **precision / canonicalization**, not recall: entity resolution, relation filtering, and event aggregation look like the highest-leverage next steps before trusting the graph for multi-hop QA.

## Mini-experiment: rule-based entity resolution

**Script:** `entity_resolve_dulce.py`  
**Method:** high-confidence alias table for 4 main characters → normalize node/edge IDs → deduplicate nodes and `(start, relation, end)` edges.  
**Outputs:** `entity_resolved/nodes_resolved.csv`, `edges_resolved.csv`, `metrics.json`, `alias_table.json`

### Before → After

| Metric | Before | After |
|--------|--------|-------|
| Entity nodes | 104 | 95 (−9) |
| Total nodes | 382 | 373 (−9) |
| Edges | 469 | 449 (−20 duplicate edges) |
| Self-loops dropped | — | 0 |

| Character | Variants before | After |
|-----------|-----------------|-------|
| Alex Mercer | 5 (`Agent Alex Mercer`, `Alex Mercer`, `Alex`, `Agent Mercer`, `Mercer`) | 1 |
| Sam Rivera | 2 (`Sam Rivera`, `Sam`) | 1 |
| Jordan Hayes | 3 (`Dr. Jordan Hayes`, `Jordan Hayes`, `Jordan`) | 1 |
| Taylor Cruz | 3 (`Taylor Cruz`, `Taylor`, `Agent Cruz`) | 1 |

### Conclusion

Alias merging is effective on this demo: character mentions collapse to canonical nodes and 20 redundant edges disappear, so the graph becomes more compact. Limitations: dictionary-only (not context-aware), covers only 4 protagonists, and QA impact is not measured yet. Next step could be embedding recall + LLM verification for broader entity resolution, plus a small before/after retrieval probe.