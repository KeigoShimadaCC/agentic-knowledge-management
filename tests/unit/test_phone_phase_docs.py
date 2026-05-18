from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PHONE_DOCS = [
    ROOT / "PROGRESS.md",
    ROOT / "docs" / "MOBILE_API_CONTRACT.md",
    ROOT / "docs" / "MOBILE_NETWORKING.md",
    ROOT / "project-phases" / "IDEA-iPHONE-APP.md",
    *sorted((ROOT / "project-phases").glob("PHASE-PHONE-*.md")),
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phone_docs_do_not_use_stale_markers() -> None:
    forbidden = [
        "NOT YET IMPLEMENTED",
        "xcodebuild ...",
        "**Status:** Planned",
        "**Worktree:** `../kos-phone",
        "PHASE-PHONE-10-SIMULATOR-AUTOMATION-AND-QA",
        "PHASE-PHONE-11-DEVICE-INSTALL-AND-PRIVATE-RELEASE",
    ]

    failures: list[str] = []
    for path in PHONE_DOCS:
        body = read(path)
        for marker in forbidden:
            if marker in body:
                failures.append(f"{path.relative_to(ROOT)} contains {marker!r}")

    assert failures == []


def test_phone_06_remains_device_smoke_pending() -> None:
    progress = read(ROOT / "PROGRESS.md")
    phase = read(ROOT / "project-phases" / "PHASE-PHONE-06-DEVICE-INSTALL-AND-PRIVATE-RELEASE.md")

    assert (
        "## Phase PHONE-06 — Device Install & Private Release 🚧 Device Smoke Pending" in progress
    )
    assert "- [ ] Real-device smoke is still required" in progress
    assert "**Status:** Device Smoke Pending" in phase
    assert "Keep PHONE-06 incomplete until the real physical-device smoke succeeds." in phase


def test_phone_07_contract_doc_exists_and_uses_current_worktree() -> None:
    phase = read(ROOT / "project-phases" / "PHASE-PHONE-07-MOBILE-HARDENING-AND-CONTRACT-REPAIR.md")

    assert "**Worktree:** `worktrees/kos-phone-07`" in phase
    assert "/api/v1/assets/{asset_id}/download" in phase
    assert "Application Support" in phase


def test_phone_08_parity_plan_exists_and_records_hard_gate() -> None:
    phase = read(ROOT / "project-phases" / "PHASE-PHONE-08-CROSS-PLATFORM-PARITY.md")
    progress = read(ROOT / "PROGRESS.md")

    assert "**Status:** Draft" in phase
    assert "**Worktree:** `worktrees/kos-phone-08`" in phase
    assert "Mac surface, meaning the existing Next.js web app in `apps/web`" in phase
    assert "docs/CROSS_PLATFORM_PARITY.md" in phase
    assert "critical-gap-fixed-in-phone-08" in phase
    assert "Use `ios-simulator` MCP after boot." in phase
    assert "iPhone 16 simulator build, test, MCP UI describe, and screenshot acceptance all pass." in phase
    assert "PHASE-PHONE-08-CROSS-PLATFORM-PARITY.md" in progress

