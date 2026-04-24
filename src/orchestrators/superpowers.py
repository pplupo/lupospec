"""
superpowers.py — Orchestrator for OpenCode + Superpowers.

Maps to ``lupo execute``.
Handles test-driven, agentic implementation by launching OpenCode
with the Superpowers plugin and streaming output to the terminal.
"""

import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BINARY = "opencode"
ACTIVE_CHANGES_DIR = Path(".openspec") / "active"

INSTALL_HINT = (
    f"'{BINARY}' was not found in your PATH.\n"
    "Install OpenCode CLI and ensure the Superpowers plugin is configured:\n"
    "  go install github.com/sst/opencode@latest\n"
    "See https://github.com/sst/opencode for details."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_binary() -> None:
    """Abort with a helpful message if ``opencode`` is not installed."""
    if shutil.which(BINARY) is None:
        print(f"✘ {INSTALL_HINT}", file=sys.stderr)
        raise SystemExit(1)


def _find_active_delta_spec() -> Path | None:
    """Locate the most recent active Delta Spec markdown file.

    Returns:
        Path to the Delta Spec, or None if none exists.
    """
    if not ACTIVE_CHANGES_DIR.exists():
        return None
    specs = sorted(ACTIVE_CHANGES_DIR.glob("*.md"))
    return specs[-1] if specs else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def execute(behavioral_prompt: str) -> None:
    """Launch OpenCode with Superpowers to implement the active Delta Spec.

    Execution flow (per spec §5 — Command 3):
        1. Locate the active Delta Spec from the ``propose`` step.
        2. Receive the behavioral prompt (loaded externally via
           ``karpathy_loader``).
        3. Construct and run the ``opencode`` command with the
           ``--agent powers`` flag, the delta-spec context, and the
           system prompt.
        4. Stream terminal output so the user can watch Superpowers
           manage Git worktrees and tests.

    Args:
        behavioral_prompt: The contents of CLAUDE.md to use as the
            system prompt.

    Raises:
        SystemExit: If no active Delta Spec is found (instructs the
            user to run ``lupo propose`` first).
    """
    _ensure_binary()

    delta_spec = _find_active_delta_spec()
    if delta_spec is None:
        print(
            "✘ No active Delta Spec found.\n"
            "  Run 'lupo propose <feature_description>' first to "
            "generate one.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(f"\n▸ Executing Delta Spec: {delta_spec}")
    print("▸ Launching OpenCode with Superpowers agent …\n")

    cmd = [
        BINARY,
        "--agent", "powers",
        "--context", str(delta_spec),
        "--system-prompt", behavioral_prompt,
        "Implement this delta spec using strict TDD.",
    ]

    try:
        # Stream output directly to the user's terminal
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(
            f"\n✘ OpenCode exited with code {exc.returncode}.",
            file=sys.stderr,
        )
        raise SystemExit(exc.returncode)

    print("\n✔ Execution complete.\n")
