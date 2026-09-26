from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from app.core.dependencies import get_generation_service, get_retrieval_service
from app.generation.service import GenerationService
from app.models.requests import QueryRequest
from app.models.responses import ContextInfo, QueryResponse
from app.retrieval.service import RetrievalService

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    generation_service: GenerationService = Depends(get_generation_service),
) -> QueryResponse:
    t0 = time.perf_counter()
    chunks = retrieval_service.search(
        request.question, request.top_k, filters=request.filters, rerank=request.rerank
    )
    t1 = time.perf_counter()
    result = generation_service.answer(request.question, chunks)
    t2 = time.perf_counter()

    return QueryResponse(
        answer=result.answer,
        citations=result.citations,
        retrieved_chunks=chunks,
        context=ContextInfo(
            truncated=result.context_truncated,
            chunks_used=result.chunks_used,
            chunk_ids=result.included_chunk_ids,
        ),
        model=result.model,
        timing_ms={"retrieval_ms": (t1 - t0) * 1000, "generation_ms": (t2 - t1) * 1000},
    )
