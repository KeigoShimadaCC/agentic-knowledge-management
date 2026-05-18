from __future__ import annotations

from dataclasses import dataclass
from string import Formatter

from app.ai import prompts
from app.services import career_ai_prompts

EXTRACT_PROJECT_SYSTEM = """You extract a single, well-structured PROJECT record.

A "project" is a bounded effort the person worked on with measurable scope:
problem solved, actions taken, results achieved, metrics where available,
skills exercised, and a time period.

Return JSON matching this schema (no prose, no markdown, no code fences):
{
  "title": string,
  "description": string | null,
  "period_start": string | null,
  "period_end": string | null,
  "role": string | null,
  "organization": string | null,
  "problem": string | null,
  "actions": string | null,
  "results": string | null,
  "metrics": object,
  "skills": string[],
  "confidence": number
}

Rules:
- If the source mentions multiple distinct projects, pick the one most prominent
  by space/specificity. Do not merge two projects.
- If the source is not about a project (e.g. a generic discussion), return
  confidence <= 0.2 and minimal fields.
- Do not invent dates, employers, or metrics. Use null/empty when unknown.
- Lowercase skills. Strip leading/trailing whitespace.
"""

INLINE_COMPLETE_CONTINUE = (
    "You are a writing assistant. Continue the text naturally."
    " Return only the continuation, no preamble."
)
INLINE_COMPLETE_EXPAND = (
    "You are a writing assistant. Expand the text with more detail."
    " Return only the expanded continuation."
)
INLINE_TRANSFORM_IMPROVE = (
    "You are an editor. Improve the clarity and flow of the text. Return only the improved version."
)
INLINE_TRANSFORM_CONCISE = (
    "You are an editor. Make the text more concise without losing meaning."
    " Return only the revised version."
)
INLINE_TRANSFORM_GRAMMAR = (
    "You are a proofreader. Fix all grammar and spelling errors. Return only the corrected version."
)
INLINE_TRANSFORM_SUMMARIZE = (
    "You are an editor. Write a one-paragraph summary of the text. Return only the summary."
)


@dataclass(frozen=True)
class PromptDefinition:
    key: str
    display_name: str
    default_template: str
    variables: tuple[str, ...]
    response_contract: str


@dataclass(frozen=True)
class FeatureDefinition:
    key: str
    display_name: str
    agent_types: tuple[str, ...]
    default_provider: str | None = None
    default_model: str | None = None
    default_temperature: float | None = None
    default_max_tokens: int | None = None
    supports_effort: bool = False


def _vars(template: str) -> tuple[str, ...]:
    names = {
        field_name.split(".")[0].split("[")[0]
        for _, field_name, _, _ in Formatter().parse(template)
        if field_name
    }
    return tuple(sorted(names))


PROMPT_DEFINITIONS: dict[str, PromptDefinition] = {
    "summarize.page": PromptDefinition(
        "summarize.page",
        "Summarize Page",
        prompts.SUMMARIZE_PAGE,
        _vars(prompts.SUMMARIZE_PAGE),
        "Plain text summary, 3-5 sentences.",
    ),
    "summarize.source": PromptDefinition(
        "summarize.source",
        "Summarize Source",
        prompts.SUMMARIZE_SOURCE,
        _vars(prompts.SUMMARIZE_SOURCE),
        "Plain text summary, 3-5 sentences.",
    ),
    "extract.claims": PromptDefinition(
        "extract.claims",
        "Extract Claims",
        prompts.EXTRACT_CLAIMS,
        _vars(prompts.EXTRACT_CLAIMS),
        "JSON array of claims.",
    ),
    "extract.tasks": PromptDefinition(
        "extract.tasks",
        "Extract Tasks",
        prompts.EXTRACT_TASKS,
        _vars(prompts.EXTRACT_TASKS),
        "JSON array of tasks.",
    ),
    "suggest.links": PromptDefinition(
        "suggest.links",
        "Suggest Links",
        prompts.SUGGEST_LINKS,
        _vars(prompts.SUGGEST_LINKS),
        "JSON array of link suggestions.",
    ),
    "answer.kb": PromptDefinition(
        "answer.kb",
        "Answer From Knowledge Base",
        prompts.ANSWER_QUESTION,
        _vars(prompts.ANSWER_QUESTION),
        "Plain text answer ending with Sources: [ids].",
    ),
    "answer.kb_web": PromptDefinition(
        "answer.kb_web",
        "Answer With Web Search",
        prompts.ANSWER_QUESTION_WITH_WEB,
        _vars(prompts.ANSWER_QUESTION_WITH_WEB),
        "Plain text answer with KB source IDs and inline web references.",
    ),
    "triage.object": PromptDefinition(
        "triage.object",
        "Triage Object",
        prompts.TRIAGE_OBJECT,
        _vars(prompts.TRIAGE_OBJECT),
        "JSON object with tags, optional title, and summary.",
    ),
    "inline.complete.continue": PromptDefinition(
        "inline.complete.continue",
        "Inline Complete: Continue",
        INLINE_COMPLETE_CONTINUE,
        (),
        "Plain text continuation only.",
    ),
    "inline.complete.expand": PromptDefinition(
        "inline.complete.expand",
        "Inline Complete: Expand",
        INLINE_COMPLETE_EXPAND,
        (),
        "Plain text expanded continuation only.",
    ),
    "inline.transform.improve": PromptDefinition(
        "inline.transform.improve",
        "Inline Transform: Improve",
        INLINE_TRANSFORM_IMPROVE,
        (),
        "Plain text replacement only.",
    ),
    "inline.transform.concise": PromptDefinition(
        "inline.transform.concise",
        "Inline Transform: Concise",
        INLINE_TRANSFORM_CONCISE,
        (),
        "Plain text replacement only.",
    ),
    "inline.transform.grammar": PromptDefinition(
        "inline.transform.grammar",
        "Inline Transform: Grammar",
        INLINE_TRANSFORM_GRAMMAR,
        (),
        "Plain text replacement only.",
    ),
    "inline.transform.summarize": PromptDefinition(
        "inline.transform.summarize",
        "Inline Transform: Summarize",
        INLINE_TRANSFORM_SUMMARIZE,
        (),
        "Plain text summary only.",
    ),
    "extract.project": PromptDefinition(
        "extract.project",
        "Extract Project",
        EXTRACT_PROJECT_SYSTEM,
        (),
        "JSON object matching ExtractedProjectDraft fields.",
    ),
    "career.resume_bullets": PromptDefinition(
        "career.resume_bullets",
        "Generate Resume Bullets",
        career_ai_prompts.RESUME_BULLETS_SYSTEM_PROMPT,
        _vars(career_ai_prompts.RESUME_BULLETS_SYSTEM_PROMPT),
        "JSON object with bullets array.",
    ),
    "career.interview_story": PromptDefinition(
        "career.interview_story",
        "Generate Interview Story",
        career_ai_prompts.INTERVIEW_STORY_SYSTEM_PROMPT,
        _vars(career_ai_prompts.INTERVIEW_STORY_SYSTEM_PROMPT),
        "JSON object with STAR story fields.",
    ),
}

FEATURE_DEFINITIONS: dict[str, FeatureDefinition] = {
    "summarize": FeatureDefinition(
        "summarize", "Summarization", ("summarize",), default_temperature=0.2
    ),
    "extract_claims": FeatureDefinition(
        "extract_claims", "Extract Claims", ("extract_claims",), default_temperature=0.1
    ),
    "extract_tasks": FeatureDefinition(
        "extract_tasks", "Extract Tasks", ("extract_tasks",), default_temperature=0.1
    ),
    "suggest_links": FeatureDefinition(
        "suggest_links", "Suggest Links", ("suggest_links",), default_temperature=0.2
    ),
    "answer": FeatureDefinition(
        "answer", "Knowledge Base Answer", ("answer",), default_temperature=0.2
    ),
    "triage": FeatureDefinition("triage", "Inbox Triage", ("triage",), default_temperature=0.2),
    "inline_ai": FeatureDefinition(
        "inline_ai",
        "Inline Editor AI",
        ("inline_ai_complete", "inline_ai_transform"),
    ),
    "extract_project": FeatureDefinition(
        "extract_project", "Extract Project", ("extract-project",), default_temperature=0.2
    ),
    "career_ai": FeatureDefinition(
        "career_ai",
        "Career AI",
        ("generate_resume_bullets", "generate_interview_story"),
        default_temperature=0.3,
    ),
    "embeddings_search": FeatureDefinition(
        "embeddings_search",
        "Embeddings/Search",
        (),
        default_provider="openai",
        default_model=None,
    ),
}

AGENT_TYPE_TO_FEATURE: dict[str, str] = {
    agent_type: feature.key
    for feature in FEATURE_DEFINITIONS.values()
    for agent_type in feature.agent_types
}

PROVIDER_CAPABILITIES: dict[str, dict[str, bool]] = {
    "openai": {"effort": False},
    "anthropic": {"effort": False},
}
