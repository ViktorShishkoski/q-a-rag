from __future__ import annotations

from pydantic import BaseModel, Field

from app.evaluation.dataset import EvalCase
from app.evaluation.metrics import citation_presence, lexical_overlap, mrr, recall_at_k
from app.generation.service import GenerationService
from app.retrieval.service import RetrievalService


class CaseResult(BaseModel):
    question: str
    recall_at_k: float
    mrr: float
    lexical_overlap: float
    citation_present: bool
    answer: str


class BenchmarkReport(BaseModel):
    case_results: list[CaseResult] = Field(default_factory=list)
    mean_recall_at_k: float = 0.0
    mean_mrr: float = 0.0
    mean_lexical_overlap: float = 0.0
    citation_presence_rate: float = 0.0


def run_benchmark(
    cases: list[EvalCase],
    retrieval_service: RetrievalService,
    generation_service: GenerationService,
    *,
    top_k: int = 5,
) -> BenchmarkReport:
    results: list[CaseResult] = []

    for case in cases:
        scored_chunks = retrieval_service.search(case.question, top_k)
        retrieved = [sc.chunk for sc in scored_chunks]
        answer_result = generation_service.answer(case.question, scored_chunks)

        results.append(
            CaseResult(
                question=case.question,
                recall_at_k=recall_at_k(retrieved, case.expected_document or "", top_k),
                mrr=mrr(retrieved, case.expected_document or ""),
                lexical_overlap=lexical_overlap(answer_result.answer, case.expected_answer_keywords),
                citation_present=citation_presence(
                    answer_result.citations, case.expected_document, case.expected_page
                ),
                answer=answer_result.answer,
            )
        )

    n = len(results) or 1
    return BenchmarkReport(
        case_results=results,
        mean_recall_at_k=sum(r.recall_at_k for r in results) / n,
        mean_mrr=sum(r.mrr for r in results) / n,
        mean_lexical_overlap=sum(r.lexical_overlap for r in results) / n,
        citation_presence_rate=sum(1 for r in results if r.citation_present) / n,
    )
