"""Persistence helpers for MCP/agent audit rows (`agent_runs`)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun


async def create_agent_run(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    agent_type: str,
    input_payload: dict[str, Any],
    model: str | None = None,
) -> AgentRun:
    """Insert a new agent run (typically status *running* until finished).

    MCP write tools should call `finish_agent_run` after the operation completes.
    """
    run = AgentRun(
        user_id=user_id,
        agent_type=agent_type,
        input=input_payload,
        status="running",
        model=model,
        started_at=datetime.now(UTC),
    )
    db.add(run)
    await db.flush()
    return run


async def finish_agent_run(
    db: AsyncSession,
    run: AgentRun,
    *,
    status: str,
    output: dict[str, Any] | None = None,
    error: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cost_usd: Decimal | None = None,
) -> AgentRun:
    run.status = status
    run.output = output
    run.error = error
    run.input_tokens = input_tokens
    run.output_tokens = output_tokens
    run.cost_usd = cost_usd
    run.finished_at = datetime.now(UTC)
    await db.flush()
    return run


async def complete(
    db: AsyncSession,
    run: AgentRun,
    output: dict[str, Any] | None = None,
) -> AgentRun:
    """Mark run as success with optional output payload."""
    return await finish_agent_run(db, run, status="success", output=output)


async def fail(
    db: AsyncSession,
    run: AgentRun,
    error: str,
) -> AgentRun:
    """Mark run as failed with error message."""
    return await finish_agent_run(db, run, status="failed", error=error)
