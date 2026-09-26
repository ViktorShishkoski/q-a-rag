"""Document-analysis layer: features that operate on an already-ingested
document rather than on a single retrieval turn.

- outline.py    - table-of-contents extraction (V1)
- compare.py    - cross-document comparison (V2, minimal first cut)
- extraction.py - structured field extraction (V2, interface + NoOp)

Like retrieval/ and generation/, nothing here imports FastAPI; the API layer
calls these through service classes.
"""
