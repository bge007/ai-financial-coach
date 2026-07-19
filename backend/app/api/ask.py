"""Ask the Coach (SSE) and direct agent analyze endpoints."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_agents
from app.agents.router import route_query
from app.core.auth import get_current_user
from app.core.db import get_db
from app.core.rate_limit import ask_limiter, client_key
from app.models.user import User

router = APIRouter(prefix="/api", tags=["agents"])

VALID_AGENTS = {
    "budget_agent",
    "investment_agent",
    "portfolio_agent",
    "tax_agent",
    "debt_agent",
    "coach_agent",
}


class AskIn(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    params: dict[str, Any] = Field(default_factory=dict)


class AnalyzeIn(BaseModel):
    query: str = Field(default="Analyze my finances", max_length=4000)
    params: dict[str, Any] = Field(default_factory=dict)


@router.post("/ask")
async def ask_coach(
    request: Request,
    body: AskIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ask_limiter.check(client_key(request, user.id))
    result = await run_agents(db, user.id, body.query, params=body.params)

    async def event_stream():
        meta = {
            "route": result["route"],
            "citations": [
                {
                    "source_file": c["source_file"],
                    "page": c["page"],
                    "score": c["score"],
                }
                for c in result["rag_chunks"]
            ],
        }
        if result.get("llm_warning"):
            meta["llm_warning"] = result["llm_warning"]
        yield f"event: meta\ndata: {json.dumps(meta)}\n\n"
        answer = result["answer"]
        text = answer["summary"]
        # Stream in chunks after guardrails
        step = 80
        for i in range(0, len(text), step):
            yield f"event: token\ndata: {json.dumps({'text': text[i:i+step]})}\n\n"
        yield f"event: done\ndata: {json.dumps(answer)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/agents/{name}/analyze")
async def analyze_agent(
    name: str,
    body: AnalyzeIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if name not in VALID_AGENTS:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{name}'")
    result = await run_agents(
        db,
        user.id,
        body.query,
        params=body.params,
        force_routes=[name],
    )
    return {
        "agent": name,
        "route": result["route"],
        "tool_results": result["tool_results"],
        "answer": result["answer"],
        "rag_chunks": result["rag_chunks"],
        "llm_warning": result.get("llm_warning"),
    }


@router.get("/agents/route-preview")
async def route_preview(q: str, user: User = Depends(get_current_user)):
    return {"query": q, "route": route_query(q)}
