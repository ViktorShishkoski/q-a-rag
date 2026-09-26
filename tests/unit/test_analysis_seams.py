"""V2 seam contracts: the NoOp implementations must be inert and truthful so
the wiring can ship before the real backends exist."""

from __future__ import annotations

from app.analysis.compare import DocumentComparer, NoOpDocumentComparer
from app.analysis.extraction import NoOpStructuredExtractor, StructuredExtractor
from app.ingestion.ocr import NoOpOcrEngine, OcrEngine
from app.ingestion.tables import NoOpTableExtractor, TableExtractor
from app.models.domain import ExtractionField, ExtractionSchema, TextBlock


def test_noop_ocr_engine_satisfies_protocol_and_recovers_nothing():
    engine = NoOpOcrEngine()
    assert isinstance(engine, OcrEngine)
    assert engine.enabled is False
    assert engine.ocr_page(b"\x89PNG...") is None


def test_noop_table_extractor_satisfies_protocol_and_finds_nothing():
    extractor = NoOpTableExtractor()
    assert isinstance(extractor, TableExtractor)
    assert extractor.enabled is False
    tables = extractor.extract(
        document_id="doc1",
        file_bytes=b"%PDF-1.4",
        filename="a.pdf",
        blocks=[TextBlock(text="hi", page=1)],
    )
    assert tables == []


def test_noop_structured_extractor_reports_not_implemented():
    extractor = NoOpStructuredExtractor()
    assert isinstance(extractor, StructuredExtractor)
    schema = ExtractionSchema(fields=[ExtractionField(name="title", description="the title")])
    result = extractor.extract(document_id="doc1", schema=schema)
    assert result.document_id == "doc1"
    assert result.implemented is False
    assert result.values == []


def test_noop_document_comparer_reports_not_implemented():
    comparer = NoOpDocumentComparer()
    assert isinstance(comparer, DocumentComparer)
    result = comparer.compare(document_ids=["a", "b"], question="which is faster?")
    assert result.document_ids == ["a", "b"]
    assert result.question == "which is faster?"
    assert result.implemented is False
    assert result.citations == []
