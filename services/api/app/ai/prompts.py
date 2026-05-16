SUMMARIZE_PAGE = (
    "You are a concise knowledge assistant. Summarize the following page content in 3-5 sentences."
    " Be factual and specific. Return only the summary text, no preamble.\n\nContent:\n{content}"
)

SUMMARIZE_SOURCE = (
    "Summarize the following document in 3-5 sentences."
    " Focus on key facts, findings, and important details."
    " Return only the summary text.\n\nContent:\n{content}"
)

EXTRACT_CLAIMS = (
    "Extract factual claims from the following text."
    " Return a JSON array only, no markdown fences, no explanation."
    ' Each item: {{"text": "<claim>", "confidence": "high"|"medium"|"low"}}.'
    " Maximum 10 claims. If no clear claims exist, return [].\n\nText:\n{content}"
)

EXTRACT_TASKS = (
    "Extract action items and tasks from the following text."
    " Return a JSON array only, no markdown fences, no explanation."
    ' Each item: {{"title": "<task>", "due_hint": "<hint or null>"}}.'
    " Maximum 10 tasks. If no tasks, return [].\n\nText:\n{content}"
)

SUGGEST_LINKS = (
    "Given an object and candidate objects from a knowledge base,"
    " identify the most meaningful connections."
    " Return a JSON array only, no markdown fences."
    ' Each item: {{"target_id": "<id>", "reason": "<1 sentence>", "confidence": 0.0-1.0}}.'
    " Return at most {limit} items. Only include genuinely meaningful connections.\n\n"
    "Object:\nTitle: {title}\nContent: {content}\n\nCandidates:\n{candidates}"
)

ANSWER_QUESTION = (
    "Answer the following question using ONLY the provided knowledge base context."
    " Be concise and cite your sources."
    " At the end, on a new line, list the IDs of sources you used as: Sources: [id1, id2, ...]."
    " If the context doesn't contain the answer, say so.\n\n"
    "Question: {question}\n\nContext:\n{context}"
)

ANSWER_QUESTION_WITH_WEB = (
    "Answer the following question using the knowledge base context and web search results."
    " Be concise. Cite KB sources with their IDs as: Sources: [id1, id2, ...]."
    " For web results, reference them inline (e.g. '[Web: title]') but do NOT include them"
    " in Sources: list."
    " If neither context contains the answer, say so.\n\n"
    "Question: {question}\n\nKnowledge base:\n{kb_context}\n\nWeb results:\n{web_context}"
)

TRIAGE_OBJECT = (
    "Analyze the following knowledge item and return a JSON object only, no markdown fences:"
    ' {{"suggested_tags": ["tag1", "tag2"], "suggested_title": "<improved title or null if fine>",'
    ' "summary": "<2-3 sentence description>"}}.'
    " Tags should be lowercase, 1-3 words each. Maximum 5 tags.\n\n"
    "Title: {title}\nContent: {content}"
)
