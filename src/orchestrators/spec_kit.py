"""
spec_kit.py — Orchestrator for GitHub Spec Kit (``specify``).

Maps to ``lupo init <project_name>``.
Handles greenfield bootstrap: initialising a project with Spec Kit,
defining the constitution, and generating the PRD + architecture plan.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BINARY = "specify"
DOCS_DIR = Path("docs") / "architecture"

INSTALL_HINT = (
    f"'{BINARY}' was not found in your PATH.\n"
    "Install GitHub Spec Kit via uv:\n"
    "  uv tool install spec-kit\n"
    "See https://github.com/github/spec-kit for details."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_binary() -> None:
    """Abort with a helpful message if ``specify`` is not installed."""
    if shutil.which(BINARY) is None:
        print(f"✘ {INSTALL_HINT}", file=sys.stderr)
        raise SystemExit(1)


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command, streaming output to the terminal."""
    return subprocess.run(cmd, check=True, **kwargs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init_project(project_name: str) -> None:
    """Bootstrap a new project with Spec Kit.

    Execution flow (per spec §5 — Command 1):
        1. ``specify init <project_name>``
        2. Trigger ``/speckit.constitution`` for static rules.
        3. Trigger ``/speckit.specify`` and ``/speckit.plan`` for PRD +
           architecture constraints.
        4. Ensure artifacts land in ``docs/architecture/`` so OpenSpec can
           consume them later.
    """
    _ensure_binary()

    print(f"\n▸ Initialising project '{project_name}' with Spec Kit …\n")

    # Step 1 — scaffold
    _run([BINARY, "init", project_name])

    # Step 2 — constitution
    print("\n▸ Defining project constitution …\n")
    _run([BINARY, "constitution"])

    # Step 3 — PRD & architecture plan
    print("\n▸ Generating PRD (specify) …\n")
    _run([BINARY, "specify"])

    print("\n▸ Generating architecture plan …\n")
    _run([BINARY, "plan"])

    # Step 4 — ensure docs/architecture/ exists for OpenSpec
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # Move any spec-kit output into the canonical location if it wasn't
    # placed there automatically.
    spec_output = Path(".spec")
    if spec_output.exists():
        for item in spec_output.iterdir():
            dest = DOCS_DIR / item.name
            if not dest.exists():
                shutil.move(str(item), str(dest))
        print(f"\n✔ Architecture artifacts saved to {DOCS_DIR}/")
    else:
        print(f"\n✔ Artifacts expected in {DOCS_DIR}/")

    print(f"✔ Project '{project_name}' initialised.\n")
