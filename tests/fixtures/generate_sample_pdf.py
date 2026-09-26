"""One-time generator for tests/fixtures/sample.pdf.

Run manually with `python tests/fixtures/generate_sample_pdf.py` whenever the
fixture needs regenerating. The output is committed to the repo so tests
don't depend on reportlab at test-run time (only this generator does).
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

OUTPUT = Path(__file__).parent / "sample.pdf"


def build() -> None:
    c = canvas.Canvas(str(OUTPUT), pagesize=LETTER)
    width, height = LETTER

    # Page 1: title + intro section
    c.setFont("Helvetica-Bold", 18)
    c.drawString(1 * inch, height - 1 * inch, "Efficient Retrieval for Local Language Models")
    c.setFont("Helvetica-Bold", 13)
    c.drawString(1 * inch, height - 1.5 * inch, "1. Introduction")
    c.setFont("Helvetica", 11)
    text1 = c.beginText(1 * inch, height - 1.9 * inch)
    for line in [
        "Retrieval augmented generation combines a document index with a",
        "language model so that answers can be grounded in source text.",
        "This paper studies retrieval strategies suited to small, locally",
        "hosted language models running under tight memory budgets.",
    ]:
        text1.textLine(line)
    c.drawText(text1)
    c.showPage()

    # Page 2: method section
    c.setFont("Helvetica-Bold", 13)
    c.drawString(1 * inch, height - 1 * inch, "2. Method")
    c.setFont("Helvetica", 11)
    text2 = c.beginText(1 * inch, height - 1.4 * inch)
    for line in [
        "We combine dense retrieval with a sparse BM25 index and merge the",
        "two ranked lists using reciprocal rank fusion. Reciprocal rank",
        "fusion assigns each document a score equal to the sum of one over",
        "the rank of that document across the contributing ranked lists.",
        "The fused ranking is optionally refined with a cross-encoder",
        "reranker before the top results are passed to the language model.",
    ]:
        text2.textLine(line)
    c.drawText(text2)
    c.showPage()

    # Page 3: results section
    c.setFont("Helvetica-Bold", 13)
    c.drawString(1 * inch, height - 1 * inch, "3. Results")
    c.setFont("Helvetica", 11)
    text3 = c.beginText(1 * inch, height - 1.4 * inch)
    for line in [
        "On a held-out set of technical documentation questions, the fused",
        "retrieval pipeline improved recall at five over dense-only",
        "retrieval by a wide margin, while keeping memory usage low enough",
        "to run entirely on consumer hardware without a discrete GPU.",
    ]:
        text3.textLine(line)
    c.drawText(text3)
    c.showPage()

    c.save()
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
