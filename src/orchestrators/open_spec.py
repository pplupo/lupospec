"""
open_spec.py — Orchestrator for OpenSpec (``openspec``).

Maps to ``lupo propose`` and ``lupo archive``.
Handles day-to-day feature deltas and documentation archiving.
"""

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BINARY = "openspec"
DOCS_DIR = Path("docs") / "architecture"
# OpenSpec's default active-changes directory
ACTIVE_CHANGES_DIR = Path(".openspec") / "active"

INSTALL_HINT = (
    f"'{BINARY}' was not found in your PATH.\n"
    "Install OpenSpec via npm:\n"
    "  npm install -g @fission-ai/openspec\n"
    "See https://github.com/fission-ai/openspec for details."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_binary() -> None:
    """Abort with a helpful message if ``openspec`` is not installed."""
    if shutil.which(BINARY) is None:
        print(f"✘ {INSTALL_HINT}", file=sys.stderr)
        raise SystemExit(1)


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command, streaming output to the terminal."""
    return subprocess.run(cmd, check=True, **kwargs)


def _find_delta_specs() -> list[Path]:
    """Return a list of active Delta Spec markdown files."""
    if not ACTIVE_CHANGES_DIR.exists():
        return []
    return sorted(ACTIVE_CHANGES_DIR.glob("*.md"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def propose(feature_description: str) -> Path | None:
    """Create a Delta Spec for a proposed feature.

    Execution flow (per spec §5 — Command 2):
        1. Read existing blueprints from ``docs/architecture/``.
        2. Execute ``openspec /opsx:propose "<feature_description>"``.
        3. Verify a Delta Spec markdown file was generated.

    Returns:
        The path to the generated Delta Spec, or None on failure.
    """
    _ensure_binary()

    if not DOCS_DIR.exists():
        print(
            f"⚠ {DOCS_DIR}/ not found. Run 'lupo init' first to bootstrap "
            "the architecture documents.",
            file=sys.stderr,
        )

    before = set(_find_delta_specs())

    print(f"\n▸ Proposing feature via OpenSpec …\n")
    _run([BINARY, "/opsx:propose", feature_description])

    after = set(_find_delta_specs())
    new_specs = after - before

    if new_specs:
        delta = sorted(new_specs)[0]
        print(f"\n✔ Delta Spec generated: {delta}\n")
        return delta
    else:
        print(
            "\n⚠ No new Delta Spec file detected in "
            f"{ACTIVE_CHANGES_DIR}/. Check OpenSpec output above.",
            file=sys.stderr,
        )
        return None


def archive() -> None:
    """Archive the implemented Delta Spec and merge docs.

    Execution flow (per spec §5 — Command 4):
        1. Run ``openspec /opsx:archive``.
        2. Verify the Delta Spec is deleted and master docs are updated.
    """
    _ensure_binary()

    print("\n▸ Archiving via OpenSpec …\n")
    _run([BINARY, "/opsx:archive"])

    remaining = _find_delta_specs()
    if remaining:
        print(
            f"\n⚠ {len(remaining)} Delta Spec(s) still present in "
            f"{ACTIVE_CHANGES_DIR}/. Manual cleanup may be needed.",
            file=sys.stderr,
        )
    else:
        print("\n✔ Delta Spec archived. Master docs updated.\n")

    if DOCS_DIR.exists():
        print(f"  Architecture docs in {DOCS_DIR}/:")
        for f in sorted(DOCS_DIR.iterdir()):
            print(f"    • {f.name}")
    print()
