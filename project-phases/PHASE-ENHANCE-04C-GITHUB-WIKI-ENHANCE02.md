# PHASE-ENHANCE-04C — GitHub Wiki Enhance02

## 0. North Star

Add the next operational layer to the published KnowledgeOS GitHub Wiki: runbooks,
end-to-end workflows, documentation maintenance rules, and known limitations.

The existing wiki now has architecture, API, runtime, systems, sources, security, cost, and
reference material. This phase should make it more useful during real maintenance and AI-agent
work by documenting how to operate, debug, and safely change the system.

Published wiki URL:

`https://github.com/OWNER/agentic-knowledge-management/wiki`

## 1. Starting Point

Phase 04A created and published the first flat GitHub Wiki.

Phase 04B deepened the API, data model, runtime, security, systems, contribution, and reference
pages. A later wiki update added `reference--cost-estimate.md`.

The remaining gap is practical operating knowledge: symptom-driven runbooks and user/agent
workflows that connect the existing reference pages into task-oriented procedures.

## 2. Source of Truth

Use this precedence when documenting behavior:

1. Current source code, configs, tests, scripts, and CI.
2. Current published wiki pages.
3. `PROGRESS.md`.
4. `docs/`.
5. `README.md`.
6. `project-phases/` for background and planned/future context.

Do not invent features. If a workflow depends on planned behavior, label it planned/future.

## 3. Non-Breakage Contract

- Do not change application code.
- Do not change tests, configs, migrations, package files, or app docs unless a wiki validation
  helper is explicitly added in a later phase.
- Preserve the flat GitHub Wiki filename convention.
- Preserve existing wiki pages and navigation groups.
- Add new pages instead of rewriting broad existing sections.
- Update `_Sidebar.md` so every generated page is reachable.
- Update `reference.md` for new reference pages.
- Keep all wiki links local and extensionless, for example `[Runbooks](runbooks)`.
- If the main repo is dirty, do not touch unrelated files.

## 4. Target Wiki Pages

Add these pages to the wiki repo:

| Section | Page | Purpose |
| --- | --- | --- |
| Runbooks | `runbooks.md` | Index of operational runbooks. |
| Runbooks | `runbooks--restore-backup.md` | Restore/backup operating procedure and safe recovery boundaries. |
| Runbooks | `runbooks--reindex-search.md` | Search/chunk/Qdrant reindex runbook. |
| Runbooks | `runbooks--debug-ai-disabled.md` | Diagnose AI-disabled or AI-failing behavior. |
| Runbooks | `runbooks--recover-worker-ingestion.md` | Recover stuck/failed source ingestion and worker jobs. |
| Runbooks | `runbooks--mcp-tool-failures.md` | Diagnose MCP server, tool, auth, write-gate, and redaction failures. |
| Workflows | `workflows.md` | Index of end-to-end workflows. |
| Workflows | `workflows--source-to-answer.md` | Source upload/ingestion/search/answer workflow. |
| Workflows | `workflows--chat-import-to-structured-summary.md` | Chat import, structured summary preview, and apply workflow. |
| Workflows | `workflows--career-project-to-resume-bullets.md` | Career project evidence to generated resume bullet artifact workflow. |
| Workflows | `workflows--mcp-agent-write-flow.md` | MCP write-tool safety and audit workflow. |
| Reference | `reference--documentation-maintenance.md` | How to keep wiki pages synchronized with source files and commands. |
| Reference | `reference--known-limitations.md` | Current limitations, non-goals, and planned/future caveats. |

## 5. Content Requirements

### Runbook Pages

Each runbook must include:

- Symptom.
- Likely causes.
- Commands to verify.
- Source files or tables to inspect.
- Safe fix path.
- Unsafe actions to avoid.
- Related tests or validation commands.
- Related wiki links.

Runbooks should be concrete. Prefer actual commands and real file paths over generic advice.

### Workflow Pages

Each workflow page must include:

- User or agent goal.
- Entry point in UI, API, script, or MCP.
- Data flow across frontend/API/service/database/worker/index surfaces.
- Persisted state created or changed.
- Trust boundary or untrusted-data notes.
- Related tests.
- Modification entry points.

Use Mermaid diagrams where they clarify sequence or data flow.

### Documentation Maintenance Page

`reference--documentation-maintenance.md` must include:

- Wiki validation checklist.
- Source-of-truth mapping from wiki sections to repo files.
- When to update wiki pages during a code change.
- How to recompute counts if `by-the-numbers.md` changes.
- How to publish the wiki repo.
- Rules for labeling planned/future work.

### Known Limitations Page

`reference--known-limitations.md` must include:

- Local-first deployment limits.
- No documented high-availability or multi-instance production plan.
- Qdrant/vector index rebuild assumptions.
- AI output trust limits.
- MCP write-tool risk and gating.
- External URL ingestion and DNS rebinding caveat.
- Dirty/in-progress phase caveats when documenting from a non-clean checkout.

## 6. Sidebar and Reference Updates

Update `_Sidebar.md` with two new reader-intent groups:

```md
- Runbooks
  - [Runbooks](runbooks)
  - [Restore and Backup](runbooks--restore-backup)
  - [Reindex Search](runbooks--reindex-search)
  - [Debug AI Disabled](runbooks--debug-ai-disabled)
  - [Recover Worker Ingestion](runbooks--recover-worker-ingestion)
  - [MCP Tool Failures](runbooks--mcp-tool-failures)
- Workflows
  - [Workflows](workflows)
  - [Source to Answer](workflows--source-to-answer)
  - [Chat Import to Structured Summary](workflows--chat-import-to-structured-summary)
  - [Career Project to Resume Bullets](workflows--career-project-to-resume-bullets)
  - [MCP Agent Write Flow](workflows--mcp-agent-write-flow)
```

Also link `reference--documentation-maintenance.md` and `reference--known-limitations.md` from
the existing Reference group and from `reference.md`.

## 7. Validation Checklist

Before committing the wiki repo:

- Every generated page has exactly one H1.
- `_Sidebar.md` links every generated page except itself.
- Every local wiki link targets an existing generated page and omits `.md`.
- No generated page is empty.
- Every page remains reachable from `_Sidebar.md` or from a linked section page.
- Planned/future work is labeled planned/future.
- Run `git diff --check` in the wiki clone.
- Verify the published wiki URL returns HTTP 200 after push.
- Verify at least one newly added page returns HTTP 200 after push.

## 8. Suggested Implementation Order

1. Refresh the wiki repo:

   ```bash
   git -C /private/tmp/agentic-knowledge-management.wiki fetch
   git -C /private/tmp/agentic-knowledge-management.wiki pull --ff-only
   ```

2. Re-read current wiki pages that the new runbooks will link to:
   - `deployment.md`
   - `security.md`
   - `systems--search-and-indexing.md`
   - `systems--sources-and-ingestion.md`
   - `systems--ai-workflows.md`
   - `api--mcp-tools.md`
   - `reference--configuration.md`

3. Re-read the source files and tests behind each runbook before writing content.
4. Add the new runbook and workflow pages.
5. Add documentation maintenance and known limitations pages.
6. Update `_Sidebar.md` and `reference.md`.
7. Run wiki structural validation.
8. Commit:

   ```bash
   git commit -m "docs(wiki): add operational runbooks and workflows"
   ```

9. Push the wiki repo and verify the published URLs.

## 9. Acceptance Criteria

- The wiki gains operational procedures, not just more reference inventory.
- A maintainer can use the runbooks to diagnose backup/restore, search reindex, AI-disabled,
  ingestion-worker, and MCP-tool failures.
- A contributor or AI agent can use workflow pages to understand source-to-answer, chat summary,
  career generation, and MCP write flows end to end.
- Documentation maintenance instructions make future wiki drift easier to prevent.
- Known limitations are explicit and do not overstate production readiness.
- The final handoff includes:
  - wiki URL,
  - wiki commit hash,
  - validation results,
  - changed/added page list,
  - any caveats caused by dirty main-repo state.
