"""
lupospec_init.py — Native Python port of Spec Kit's PRD/Architecture generation.

This module extracts and re-implements the core logic from GitHub Spec Kit
(github/spec-kit) that is responsible for:
  - Scaffolding a new project directory
  - Generating the constitution (project governing principles)
  - Generating the Product Requirements Document (PRD / spec)
  - Generating the architecture/implementation plan

All ported blocks carry Traceability Headers per the Lupo Spec v2 protocol.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import date
from pathlib import Path
from typing import Optional

# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: github/spec-kit
# Source File: templates/constitution-template.md
# Original Lines: 1 - 51
# Purpose: Constitution template used to scaffold project governing principles
# ===================================================================

CONSTITUTION_TEMPLATE = """\
# {project_name} Constitution

## Core Principles

### I. Quality-First
All deliverables must meet defined acceptance criteria before being
considered complete.  Testing is mandatory — not optional.

### II. Incremental Delivery
Features are broken into independently testable, independently deployable
slices ordered by business priority.

### III. Traceability
Every requirement, plan entry, and task must link back to its originating
user story so nothing is lost in translation.

### IV. Test-Driven Development
TDD is the default workflow: failing test → minimal code → refactor.
Exceptions must be explicitly justified.

### V. Simplicity
Start with the simplest approach (YAGNI).  Complexity is only added when
a concrete requirement demands it.

## Governance

This constitution supersedes ad-hoc practices.  Amendments require
documentation and explicit approval.

**Version**: 1.0.0 | **Ratified**: {today}
"""

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================


# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: github/spec-kit
# Source File: templates/spec-template.md
# Original Lines: 1 - 129
# Purpose: PRD / feature specification template with user stories and
#          acceptance scenarios
# ===================================================================

SPEC_TEMPLATE = """\
# Feature Specification: {feature_name}

**Feature Branch**: `001-{feature_slug}`
**Created**: {today}
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 – [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### Edge Cases

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST [specific capability]
- **FR-002**: System MUST [specific capability]
- **FR-003**: Users MUST be able to [key interaction]

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: [Measurable metric]
- **SC-002**: [Measurable metric]

## Assumptions

- [Assumption about target users]
- [Assumption about scope boundaries]
"""

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================


# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: github/spec-kit
# Source File: templates/plan-template.md
# Original Lines: 1 - 105
# Purpose: Implementation plan template with technical context and
#          project structure guidance
# ===================================================================

PLAN_TEMPLATE = """\
# Implementation Plan: {feature_name}

**Branch**: `001-{feature_slug}` | **Date**: {today} | **Spec**: specs/001-{feature_slug}/spec.md

## Summary

[Primary requirement + technical approach]

## Technical Context

**Language/Version**: [e.g., Python 3.11]
**Primary Dependencies**: [e.g., FastAPI, Typer]
**Storage**: [if applicable]
**Testing**: [e.g., pytest]
**Target Platform**: [e.g., Linux]

## Constitution Check

*GATE: Must pass before Phase 0 research.*

[Verify against constitution]

## Project Structure

```text
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| (none)    | —          | —                                    |
"""

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================


# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: github/spec-kit
# Source File: src/specify_cli/__init__.py
# Original Lines: 843 - 877
# Purpose: ensure_constitution_from_template — copies the constitution
#          template into the project's memory directory so the project
#          has a set of governing principles from day one.
# ===================================================================

def ensure_constitution(project_path: Path) -> Path:
    """Write the constitution template into the project's docs directory.

    If a constitution already exists it is preserved (idempotent).

    Returns:
        The path to the constitution file.
    """
    constitution_path = project_path / "docs" / "architecture" / "constitution.md"

    if constitution_path.exists():
        print(f"  ⏭ Constitution already exists — preserved ({constitution_path.name})")
        return constitution_path

    constitution_path.parent.mkdir(parents=True, exist_ok=True)
    constitution_path.write_text(
        CONSTITUTION_TEMPLATE.format(
            project_name=project_path.name,
            today=date.today().isoformat(),
        ),
        encoding="utf-8",
    )
    print(f"  ✔ Constitution created → {constitution_path.relative_to(project_path)}")
    return constitution_path

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================


# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: github/spec-kit
# Source File: src/specify_cli/__init__.py
# Original Lines: 938 - 1100
# Purpose: init() — the main scaffolding function that creates the project
#          directory, initialises git, and writes all template files
#          (constitution, spec, plan) into docs/architecture/.
# ===================================================================

def init_project(project_name: str) -> Path:
    """Natively bootstrap a new Lupo Spec project.

    This is the pure-Python replacement for ``specify init``.
    It creates the project directory (or uses CWD), generates the
    constitution, PRD template, and architecture plan template,
    and ensures everything lands in ``docs/architecture/``.

    Args:
        project_name: Name for the new project directory.

    Returns:
        The absolute path to the bootstrapped project root.
    """
    project_path = Path.cwd() / project_name
    docs_dir = project_path / "docs" / "architecture"

    # --- scaffold ---------------------------------------------------------
    if project_path.exists():
        print(f"  ⚠ Directory '{project_name}' already exists — merging.")
    else:
        project_path.mkdir(parents=True)
        print(f"  ✔ Created project directory: {project_name}/")

    docs_dir.mkdir(parents=True, exist_ok=True)

    # --- constitution -----------------------------------------------------
    ensure_constitution(project_path)

    # --- PRD (spec) -------------------------------------------------------
    spec_path = docs_dir / "spec.md"
    if not spec_path.exists():
        feature_slug = project_name.lower().replace(" ", "-")
        spec_path.write_text(
            SPEC_TEMPLATE.format(
                feature_name=project_name,
                feature_slug=feature_slug,
                today=date.today().isoformat(),
            ),
            encoding="utf-8",
        )
        print(f"  ✔ PRD template created → {spec_path.relative_to(project_path)}")
    else:
        print(f"  ⏭ spec.md already exists — preserved.")

    # --- architecture plan ------------------------------------------------
    plan_path = docs_dir / "plan.md"
    if not plan_path.exists():
        feature_slug = project_name.lower().replace(" ", "-")
        plan_path.write_text(
            PLAN_TEMPLATE.format(
                feature_name=project_name,
                feature_slug=feature_slug,
                today=date.today().isoformat(),
            ),
            encoding="utf-8",
        )
        print(f"  ✔ Architecture plan created → {plan_path.relative_to(project_path)}")
    else:
        print(f"  ⏭ plan.md already exists — preserved.")

    # --- git init ---------------------------------------------------------
    git_dir = project_path / ".git"
    if not git_dir.exists() and shutil.which("git"):
        try:
            subprocess.run(
                ["git", "init"],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True,
            )
            subprocess.run(
                ["git", "add", "."],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial commit from Lupo Spec"],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True,
            )
            print("  ✔ Git repository initialised.")
        except subprocess.CalledProcessError as exc:
            print(f"  ⚠ Git init failed: {exc.stderr.strip()}")
    elif git_dir.exists():
        print("  ⏭ Git repo already exists — preserved.")

    return project_path

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================
