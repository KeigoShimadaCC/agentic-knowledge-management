"""Optional startup seed: demo pages, web source, chat import, graph edges.

Controlled by Settings.seed_demo_examples. Idempotent via objects.tags marker demo_seed_v1.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.schemas.object import ObjectUpdate
from app.schemas.page import PageCreate, PageUpdate
from app.schemas.source import SourceCreate
from app.services import chat_service, edge_service, object_service, page_service, source_service

logger = logging.getLogger(__name__)

DEMO_TAG_SEED = "demo_seed_v1"
# LEGACY: Earlier dev seeds used demo@knowledgeos.local. pydantic EmailStr rejects ".local",
# so on startup migrate_legacy_demo_email renames any existing row to settings.DEMO_SEED_EMAIL.
# Safe to remove when all known local databases have been re-seeded (target: after v0.3 release).
# Last touched 2026-05-15.
LEGACY_DEMO_EMAIL = "demo@knowledgeos.local"
DEFAULT_WEB_SOURCE_URL = "https://spec.modelcontextprotocol.io/"
CHAT_MARKDOWN = (
    "## Human\n\n"
    "What is KnowledgeOS?\n\n"
    "## Assistant\n\n"
    "KnowledgeOS is a local-first knowledge base: Postgres as source of truth, Tiptap pages, "
    "typed sources (PDF/web/CSV), keyword + hybrid search, graph edges between objects, "
    "and optional chat imports like this one.\n\n"
    "## Human\n\n"
    "Does MCP ship yet?\n\n"
    "## Assistant\n\n"
    "Phase 7 plans an MCP adapter over stdio that calls the FastAPI API with audited writes "
    "later on.\n"
)


def _doc(*blocks: dict[str, Any]) -> dict[str, Any]:
    return {"type": "doc", "content": list(blocks)}


def _text(value: str, *, marks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {"type": "text", "text": value}
    if marks:
        node["marks"] = marks
    return node


def _paragraph(*inline: dict[str, Any]) -> dict[str, Any]:
    return {"type": "paragraph", "content": list(inline)}


def _heading(level: int, text_value: str) -> dict[str, Any]:
    return {"type": "heading", "attrs": {"level": level}, "content": [_text(text_value)]}


def _bullet_list(items: list[str]) -> dict[str, Any]:
    lis = []
    for item in items:
        lis.append({"type": "listItem", "content": [_paragraph(_text(item))]})
    return {"type": "bulletList", "content": lis}


def _link_paragraph(label: str, page_id: uuid.UUID) -> dict[str, Any]:
    href = f"/app/pages/{page_id}"
    return _paragraph(
        _text(label, marks=[{"type": "link", "attrs": {"href": href, "target": "_self"}}]),
    )


def _citation(source_id: uuid.UUID, title: str) -> dict[str, Any]:
    return {"type": "citation", "attrs": {"sourceId": str(source_id), "sourceTitle": title}}


async def migrate_legacy_demo_email(db: AsyncSession) -> None:
    """Rename legacy demo@knowledgeos.local to settings.demo_seed_email if needed."""
    target = settings.demo_seed_email.strip()
    if target.lower() == LEGACY_DEMO_EMAIL.lower():
        return
    has_target = await db.execute(select(User.id).where(User.email == target).limit(1))
    if has_target.scalar_one_or_none():
        return
    result = await db.execute(select(User).where(User.email == LEGACY_DEMO_EMAIL))
    legacy = result.scalar_one_or_none()
    if legacy is None:
        return
    legacy.email = target
    await db.flush()
    logger.info("Renamed demo login email from %s to %s", LEGACY_DEMO_EMAIL, target)


async def _get_or_create_demo_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == settings.demo_seed_email))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    user = User(
        email=settings.demo_seed_email,
        display_name=settings.demo_seed_display_name,
        password_hash=hash_password(settings.demo_seed_password),
    )
    db.add(user)
    await db.flush()
    logger.info("Created demo login user %s", settings.demo_seed_email)
    return user


async def ensure_local_user(db: AsyncSession) -> User:
    """Make sure at least one non-deleted user exists for the single-user desktop profile.

    If any user already exists, return the first one (don't shadow the user's identity).
    Otherwise create the demo user so the no-auth fallback in core/deps.py has someone
    to return. Called from the lifespan on startup when KOS_PROFILE != "mobile".
    """
    result = await db.execute(select(User).where(User.deleted_at.is_(None)).limit(1))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    return await _get_or_create_demo_user(db)


async def seed_demo_examples(db: AsyncSession) -> list[uuid.UUID]:
    """Seed demo content if enabled and not already present. Returns object IDs to reindex."""
    if not settings.seed_demo_examples:
        return []

    user = await _get_or_create_demo_user(db)

    marker = await object_service.list_objects(db, user.id, tag=DEMO_TAG_SEED, limit=1, page=1)
    if marker.total >= 1:
        logger.info("Demo examples already seeded (tag %s); skipping.", DEMO_TAG_SEED)
        return []

    titles = {
        "hub": "[Demo] Knowledge OS hub",
        "reading": "[Demo] Reading notes: MCP specification",
        "decision": "[Demo] Decision log — Postgres vs SQLite",
        "concept": "[Demo] Concept sheet — Soft delete & audit",
        "chat_notes": "[Demo] After importing a ChatGPT export",
    }

    ids: dict[str, uuid.UUID] = {}
    for key, title in titles.items():
        _, page = await page_service.create_page(
            db,
            user.id,
            PageCreate(title=title, content_json={}),
        )
        ids[key] = page.id

    src_title = "[Demo] MCP Specification (spec.modelcontextprotocol.io)"
    _, source = await source_service.create_source(
        db,
        user.id,
        SourceCreate(
            source_type="web",
            title=src_title,
            description="Official MCP specification — used for Sources + citations demo.",
            tags=["demo", "kos"],
            url=DEFAULT_WEB_SOURCE_URL,
        ),
    )

    chat_rows = await chat_service.import_chats(
        db,
        user.id,
        content=CHAT_MARKDOWN.encode("utf-8"),
        provider="markdown",
        raw_format="md",
        title="[Demo] Sample assistant conversation",
        source_filename=None,
    )
    chat_id = chat_rows[0][0].id

    hub_intro = (
        "This hub ties together five demo pages that showcase KnowledgeOS today: rich pages, "
        "sources + citations, search-friendly prose, typed graph edges, and imported chats."
    )
    hub_doc = _doc(
        _heading(1, titles["hub"]),
        _paragraph(_text(hub_intro)),
        _heading(2, "Jump in"),
        _bullet_list(
            [
                "Reading notes grounded in a web Source (citations)",
                "Decision log tuned for Postgres vs SQLite keyword search",
                "Concept sheet paired across the graph with that decision log",
                "Notes after importing a short ChatGPT-style Markdown transcript",
            ]
        ),
        _heading(2, "Pages"),
        _link_paragraph(titles["reading"], ids["reading"]),
        _link_paragraph(titles["decision"], ids["decision"]),
        _link_paragraph(titles["concept"], ids["concept"]),
        _link_paragraph(titles["chat_notes"], ids["chat_notes"]),
    )
    hub_text = (
        f"{titles['hub']} {hub_intro} {titles['reading']} {titles['decision']} "
        f"{titles['concept']} {titles['chat_notes']}"
    )
    await page_service.update_page(
        db,
        ids["hub"],
        user.id,
        PageUpdate(content_json=hub_doc, content_text=hub_text),
    )

    reading_intro = (
        "Structured notes while reading the MCP specification on the web. "
        "The citation chip below points at the imported Source record."
    )
    reading_doc = _doc(
        _heading(1, titles["reading"]),
        _paragraph(_text(reading_intro)),
        _heading(2, "Summary"),
        _bullet_list(
            [
                "MCP connects hosts (IDEs, assistants) to tools via JSON-RPC.",
                "Capabilities negotiation avoids mismatched prompts.",
                "stdio transport fits local subprocess integrations.",
            ]
        ),
        _heading(2, "Primary source"),
        _paragraph(_text("Embedded citation: "), _citation(source.id, src_title)),
        _heading(2, "Open questions"),
        _bullet_list(
            [
                "Which capability bundles matter most for KnowledgeOS Phase 7?",
                "How strict should SSRF checks stay for agent-triggered URL ingestion?",
            ]
        ),
    )
    reading_text = (
        f"{titles['reading']} {reading_intro} MCP JSON-RPC hosts assistants "
        "capabilities negotiation stdio transport SSRF ingestion Open questions"
    )
    await page_service.update_page(
        db,
        ids["reading"],
        user.id,
        PageUpdate(content_json=reading_doc, content_text=reading_text),
    )

    decision_doc = _doc(
        _heading(1, titles["decision"]),
        _paragraph(
            _text(
                "Running decisions comparing Postgres vs SQLite for a browser-backed Mac "
                "dockerized knowledge appliance."
            )
        ),
        _heading(3, "2026-05-01 — Primary datastore"),
        _paragraph(_text("Decision: Standardize on Postgres 16.")),
        _paragraph(_text("Alternatives considered: SQLite for simplicity.")),
        _paragraph(
            _text(
                "Consequences: Better concurrency headroom for LAN multi-pane futures; "
                "heavier footprint but Docker already ships Postgres alongside Redis and Qdrant."
            )
        ),
        _heading(3, "2026-05-02 — SQLite revisit"),
        _paragraph(_text("Decision: Defer SQLite niche experiments.")),
        _paragraph(
            _text(
                "Alternatives: Embedded SQLite with WAL for single-user laptops "
                "(would simplify backups)."
            )
        ),
        _paragraph(
            _text(
                "Consequences: Keep migrations aligned with SQLAlchemy async patterns tested here; "
                "mention Postgres FTS + LAN concurrency explicitly so keyword search demos "
                "stay grounded."
            )
        ),
    )
    decision_text = (
        f"{titles['decision']} Postgres SQLite concurrency LAN Docker FTS backups SQLAlchemy async "
        "knowledge appliance browser-backed Mac multi-pane migrations"
    )
    await page_service.update_page(
        db,
        ids["decision"],
        user.id,
        PageUpdate(content_json=decision_doc, content_text=decision_text),
    )

    concept_doc = _doc(
        _heading(1, titles["concept"]),
        _paragraph(
            _text(
                "KnowledgeOS never hard-deletes user-owned rows: soft delete uses deleted_at "
                "timestamps so trash + restore remain honest."
            )
        ),
        _heading(2, "Audit posture"),
        _bullet_list(
            [
                "Every future MCP write should record agent identity plus payloads in agent_runs.",
                "Revision history (object_revisions) gates destructive edits / rollback UX.",
                "Secrets stay server-side — MCP responses must redact API keys.",
            ]
        ),
        _paragraph(
            _text(
                "Together these policies mirror MCP safety guidance: least privilege tools, "
                "auditable mutations, local appliance assumptions."
            )
        ),
    )
    concept_text = (
        f"{titles['concept']} soft delete deleted_at trash restore agent_runs object_revisions MCP "
        "redaction audit secrets KnowledgeOS policies least privilege local appliance"
    )
    await page_service.update_page(
        db,
        ids["concept"],
        user.id,
        PageUpdate(content_json=concept_doc, content_text=concept_text),
    )

    chat_notes_intro = (
        "Phase 6A Chat Import Lite stores Markdown transcripts as searchable chat objects. "
        "Structured extraction (claims/tasks/projects) stays on the Phase 5 AI roadmap."
    )
    chat_notes_doc = _doc(
        _heading(1, titles["chat_notes"]),
        _paragraph(_text(chat_notes_intro)),
        _heading(2, "What we imported"),
        _bullet_list(
            [
                "Short Markdown transcript labeled Human / Assistant.",
                "Appears under Chats with parsed turns + plain-text indexing.",
                "Link graph connects this write-up back to the transcript.",
            ]
        ),
        _heading(2, "Next steps"),
        _bullet_list(
            [
                "Cmd+K search for KnowledgeOS should surface both this page and the chat.",
                "Later Phase 5 flows could summarize chats into linked pages automatically.",
            ]
        ),
    )
    chat_notes_text = (
        f"{titles['chat_notes']} {chat_notes_intro} Chat Import Lite Markdown transcript "
        "Chats Cmd+K KnowledgeOS Phase 5 summarize linked pages graph"
    )
    await page_service.update_page(
        db,
        ids["chat_notes"],
        user.id,
        PageUpdate(content_json=chat_notes_doc, content_text=chat_notes_text),
    )

    hub = ids["hub"]
    await edge_service.create_edge(db, hub, ids["reading"], kind="links_to", user_id=user.id)
    await edge_service.create_edge(db, hub, ids["decision"], kind="links_to", user_id=user.id)
    await edge_service.create_edge(db, hub, ids["concept"], kind="links_to", user_id=user.id)
    await edge_service.create_edge(db, hub, ids["chat_notes"], kind="links_to", user_id=user.id)
    await edge_service.create_edge(db, hub, ids["decision"], kind="mentions", user_id=user.id)
    await edge_service.create_edge(
        db, ids["decision"], ids["concept"], kind="supports", user_id=user.id
    )
    await edge_service.create_edge(
        db, ids["reading"], ids["concept"], kind="related_to", user_id=user.id
    )
    await edge_service.create_edge(db, ids["reading"], source.id, kind="cites", user_id=user.id)
    await edge_service.create_edge(
        db, ids["chat_notes"], chat_id, kind="created_from", user_id=user.id
    )

    hub_obj = await object_service.get_object_or_404(db, hub, user.id)
    await object_service.update_object(
        db,
        hub_obj,
        ObjectUpdate(tags=["demo", "kos", DEMO_TAG_SEED], is_pinned=True),
    )

    reindex_ids = [
        ids["hub"],
        ids["reading"],
        ids["decision"],
        ids["concept"],
        ids["chat_notes"],
        source.id,
        chat_id,
    ]
    logger.info(
        "Demo examples seeded. Log in as %s (password from DEMO_SEED_PASSWORD / defaults). "
        "Open hub page id=%s",
        settings.demo_seed_email,
        ids["hub"],
    )
    return reindex_ids
