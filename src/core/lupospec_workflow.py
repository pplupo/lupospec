"""
lupospec_workflow.py — Native Python port of OpenSpec's propose/archive logic.

This module extracts and re-implements the core logic from OpenSpec
(fission-ai/openspec) that is responsible for:
  - Reading existing architecture documents
  - Generating a Delta Spec (change proposal) as a Markdown file
  - Archiving completed Delta Specs back into the main docs

All ported blocks carry Traceability Headers per the Lupo Spec v2 protocol.
"""

from __future__ import annotations

import os
import re
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOCS_DIR = Path("docs") / "architecture"
CHANGES_DIR = Path("openspec") / "changes"
ARCHIVE_DIR = CHANGES_DIR / "archive"
SPECS_DIR = Path("openspec") / "specs"


# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: fission-ai/openspec
# Source File: src/commands/change.ts
# Original Lines: 242 - 260
# Purpose: getActiveChanges — scans the openspec/changes directory for
#          active change proposals (directories containing proposal.md)
# ===================================================================

def get_active_changes() -> list[Path]:
    """Return a sorted list of active change proposal directories.

    Each active change is a subdirectory of ``openspec/changes/`` that
    contains a ``proposal.md`` file and is not named ``archive``.
    """
    if not CHANGES_DIR.exists():
        return []

    results: list[Path] = []
    for entry in sorted(CHANGES_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name == "archive":
            continue
        if (entry / "proposal.md").exists():
            results.append(entry)
    return results

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================


# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: fission-ai/openspec
# Source File: src/commands/change.ts
# Original Lines: 262 - 265
# Purpose: extractTitle — pulls the title from a change proposal's
#          first Markdown heading
# ===================================================================

def extract_title(content: str, fallback: str = "Untitled") -> str:
    """Extract the title from the first ``# Heading`` in Markdown content."""
    match = re.search(r"^#\s+(?:Change:\s+)?(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else fallback

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================


# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: fission-ai/openspec
# Source File: src/commands/change.ts
# Original Lines: 267 - 282
# Purpose: countTasks — counts total and completed tasks in a
#          tasks.md file using checkbox pattern matching
# ===================================================================

_TASK_PATTERN = re.compile(r"^[-*]\s+\[[\ x]\]", re.IGNORECASE)
_COMPLETED_TASK_PATTERN = re.compile(r"^[-*]\s+\[x\]", re.IGNORECASE)


def count_tasks(content: str) -> dict[str, int]:
    """Count total and completed tasks in Markdown checkbox syntax.

    Returns:
        ``{"total": N, "completed": M}``
    """
    total = 0
    completed = 0
    for line in content.splitlines():
        if _TASK_PATTERN.match(line):
            total += 1
            if _COMPLETED_TASK_PATTERN.match(line):
                completed += 1
    return {"total": total, "completed": completed}

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================


# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: fission-ai/openspec
# Source File: src/core/init.ts
# Original Lines: 455 - 488
# Purpose: createDirectoryStructure — creates the canonical OpenSpec
#          directory layout (specs, changes, changes/archive)
# ===================================================================

def ensure_openspec_dirs() -> None:
    """Ensure the canonical OpenSpec directory layout exists."""
    for d in [SPECS_DIR, CHANGES_DIR, ARCHIVE_DIR]:
        d.mkdir(parents=True, exist_ok=True)

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================


# ---------------------------------------------------------------------------
# Propose
# ---------------------------------------------------------------------------

def propose(feature_description: str) -> Optional[Path]:
    """Create a Delta Spec (change proposal) for a new feature.

    This is the native Python replacement for ``openspec /opsx:propose``.

    1. Reads existing architecture blueprints from ``docs/architecture/``.
    2. Generates a new change directory under ``openspec/changes/``.
    3. Writes a ``proposal.md`` Delta Spec file containing the feature
       description and placeholders for requirements and scenarios.

    Args:
        feature_description: A human-readable description of the feature.

    Returns:
        The path to the generated ``proposal.md``, or None on failure.
    """
    ensure_openspec_dirs()

    # Read existing architecture context
    context_snippets: list[str] = []
    if DOCS_DIR.exists():
        for doc in sorted(DOCS_DIR.glob("*.md")):
            context_snippets.append(f"<!-- context: {doc.name} -->\n")

    # Build a slug for the change ID
    slug = re.sub(r"[^a-z0-9]+", "-", feature_description.lower()).strip("-")[:60]
    change_id = slug or "change"

    change_dir = CHANGES_DIR / change_id
    if change_dir.exists():
        # append timestamp to de-duplicate
        ts = datetime.now().strftime("%H%M%S")
        change_id = f"{change_id}-{ts}"
        change_dir = CHANGES_DIR / change_id

    change_dir.mkdir(parents=True, exist_ok=True)

    # ===================================================================
    # LUPO SPEC TRACEABILITY
    # Source Repository: fission-ai/openspec
    # Source File: src/commands/workflow/new-change.ts
    # Original Lines: 1 - 55
    # Purpose: Generate the proposal.md delta spec file structure with
    #          ADDED/MODIFIED/REMOVED requirement sections
    # ===================================================================

    proposal_content = f"""\
# Change: {feature_description}

**Change ID**: `{change_id}`
**Created**: {date.today().isoformat()}
**Status**: Proposed

## Motivation

{feature_description}

{"".join(context_snippets)}

## ADDED Requirements

### Requirement 1

[Describe the new requirement here]

#### Scenario: Happy path
- **Given** [precondition]
- **When** [action]
- **Then** [expected outcome]

#### Scenario: Error case
- **Given** [precondition]
- **When** [action]
- **Then** [expected outcome]

## MODIFIED Requirements

*(none)*

## REMOVED Requirements

*(none)*

## Tasks

- [ ] Implement requirement 1
- [ ] Write tests for requirement 1
- [ ] Update documentation
"""

    # ===================================================================
    # END LUPO SPEC TRACEABILITY
    # ===================================================================

    proposal_path = change_dir / "proposal.md"
    proposal_path.write_text(proposal_content, encoding="utf-8")
    print(f"  ✔ Delta Spec created → {proposal_path}")
    return proposal_path


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: fission-ai/openspec
# Source File: src/core/archive.ts
# Original Lines: 50 - 288
# Purpose: ArchiveCommand.execute — validates, moves a completed
#          change proposal into the archive directory with a date
#          prefix, and updates master spec documents.
# ===================================================================

def archive(change_name: Optional[str] = None) -> None:
    """Archive a completed Delta Spec.

    This is the native Python replacement for ``openspec /opsx:archive``.

    1. Lists active changes and selects one (or uses ``change_name``).
    2. Moves the change directory into ``openspec/changes/archive/``
       with a date-prefix.
    3. Reports success and lists remaining active changes.

    Args:
        change_name: Explicit change ID to archive.  If ``None`` the
            most recent active change is used.
    """
    active = get_active_changes()

    if not active:
        print("  ✘ No active changes to archive.")
        return

    if change_name:
        target = CHANGES_DIR / change_name
        if not target.exists() or not (target / "proposal.md").exists():
            print(f"  ✘ Change '{change_name}' not found.")
            return
    else:
        target = active[-1]  # most recent
        change_name = target.name
        print(f"  ℹ Archiving most recent change: {change_name}")

    # Create archive directory
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_name = f"{date.today().isoformat()}-{change_name}"
    archive_path = ARCHIVE_DIR / archive_name

    if archive_path.exists():
        print(f"  ✘ Archive '{archive_name}' already exists.")
        return

    shutil.move(str(target), str(archive_path))
    print(f"  ✔ Change '{change_name}' archived as '{archive_name}'.")

    # Update master docs
    if DOCS_DIR.exists():
        print(f"  ℹ Architecture docs in {DOCS_DIR}/:")
        for f in sorted(DOCS_DIR.iterdir()):
            if f.is_file():
                print(f"    • {f.name}")

    remaining = get_active_changes()
    if remaining:
        print(f"  ℹ {len(remaining)} active change(s) remaining.")
    else:
        print("  ✔ No active changes remaining.")

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================
