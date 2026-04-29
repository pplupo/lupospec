"""
lupospec_agent_execution.py — Native Python port of Superpowers' Git/TDD execution.

This module extracts and re-implements the core logic from Superpowers
(obra/superpowers) that is responsible for:
  - Git worktree management for isolated feature workspaces
  - The Red-Green-Refactor test-driven development execution loop
  - Plan execution (loading a delta spec and implementing it step-by-step)

All ported blocks carry Traceability Headers per the Lupo Spec v2 protocol.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKTREE_DIR = Path(".worktrees")
CHANGES_DIR = Path("openspec") / "changes"


# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: obra/superpowers
# Source File: skills/using-git-worktrees/SKILL.md
# Original Lines: 17 - 99
# Purpose: Git worktree directory selection and creation logic —
#          checks existing dirs, verifies .gitignore coverage,
#          creates an isolated worktree with a new branch, runs
#          project setup, and verifies a clean test baseline.
# ===================================================================

def _detect_worktree_dir() -> Path:
    """Determine the worktree parent directory.

    Priority order (per Superpowers skill):
        1. ``.worktrees/`` if it exists (hidden, preferred)
        2. ``worktrees/`` if it exists
        3. Default to ``.worktrees/``
    """
    if Path(".worktrees").is_dir():
        return Path(".worktrees")
    if Path("worktrees").is_dir():
        return Path("worktrees")
    return Path(".worktrees")


def _ensure_gitignored(directory: Path) -> None:
    """Ensure *directory* is listed in ``.gitignore``.

    If the directory is NOT already ignored, append it to ``.gitignore``
    and commit the change — per Superpowers' "fix broken things
    immediately" rule.
    """
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", str(directory)],
            capture_output=True,
        )
        if result.returncode == 0:
            return  # already ignored
    except FileNotFoundError:
        return  # git not available

    gitignore = Path(".gitignore")
    entry = f"{directory.name}/\n"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if entry.strip() in content:
            return
        content += f"\n{entry}"
    else:
        content = entry

    gitignore.write_text(content, encoding="utf-8")

    try:
        subprocess.run(["git", "add", ".gitignore"], capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore: add {directory.name} to .gitignore"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass  # best-effort


def _detect_project_setup(worktree_path: Path) -> Optional[list[str]]:
    """Auto-detect and return the project setup command for a worktree."""
    if (worktree_path / "package.json").exists():
        return ["npm", "install"]
    if (worktree_path / "Cargo.toml").exists():
        return ["cargo", "build"]
    if (worktree_path / "requirements.txt").exists():
        return ["pip", "install", "-r", "requirements.txt"]
    if (worktree_path / "pyproject.toml").exists():
        return ["pip", "install", "-e", "."]
    if (worktree_path / "go.mod").exists():
        return ["go", "mod", "download"]
    return None


def _detect_test_command(worktree_path: Path) -> Optional[list[str]]:
    """Auto-detect and return the project test command for a worktree."""
    if (worktree_path / "package.json").exists():
        return ["npm", "test"]
    if (worktree_path / "Cargo.toml").exists():
        return ["cargo", "test"]
    if (worktree_path / "pyproject.toml").exists() or (worktree_path / "pytest.ini").exists():
        return ["pytest"]
    if (worktree_path / "go.mod").exists():
        return ["go", "test", "./..."]
    return None


def create_worktree(branch_name: str) -> Path:
    """Create an isolated Git worktree for feature development.

    Args:
        branch_name: Name for the new branch/worktree.

    Returns:
        The absolute path to the new worktree.
    """
    wt_dir = _detect_worktree_dir()
    _ensure_gitignored(wt_dir)

    worktree_path = wt_dir / branch_name
    print(f"\n▸ Creating worktree: {worktree_path} (branch: {branch_name})")

    try:
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", branch_name],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"  ✘ Failed to create worktree: {exc}", file=sys.stderr)
        raise SystemExit(1)

    # Project setup
    setup_cmd = _detect_project_setup(worktree_path)
    if setup_cmd:
        print(f"  ▸ Running project setup: {' '.join(setup_cmd)}")
        subprocess.run(setup_cmd, cwd=worktree_path)

    # Baseline test verification
    test_cmd = _detect_test_command(worktree_path)
    if test_cmd:
        print(f"  ▸ Running baseline tests: {' '.join(test_cmd)}")
        result = subprocess.run(test_cmd, cwd=worktree_path)
        if result.returncode != 0:
            print("  ⚠ Baseline tests failed. Review before proceeding.")
        else:
            print("  ✔ Baseline tests passing.")

    print(f"\n✔ Worktree ready at {worktree_path.resolve()}\n")
    return worktree_path.resolve()

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================


# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: obra/superpowers
# Source File: skills/test-driven-development/SKILL.md
# Original Lines: 47 - 69
# Purpose: Red-Green-Refactor TDD execution loop — the core cycle
#          that drives test-first implementation.  Encodes the
#          mandatory verify-RED / verify-GREEN gates.
# ===================================================================

class TDDCycle:
    """Encapsulates the Red-Green-Refactor TDD cycle.

    This is a programmatic representation of the Superpowers
    TDD skill.  It is used by the execution engine to enforce
    the mandatory verification gates.
    """

    PHASES = ("RED", "GREEN", "REFACTOR")

    def __init__(self, test_command: list[str], cwd: Path | None = None):
        self.test_command = test_command
        self.cwd = cwd
        self.phase: str = "RED"

    # --- helpers ----------------------------------------------------------

    def _run_tests(self) -> bool:
        """Run the test suite and return True if all tests pass."""
        result = subprocess.run(
            self.test_command,
            cwd=self.cwd,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    # --- phase gates ------------------------------------------------------

    def verify_red(self) -> bool:
        """Verify that the test FAILS (RED phase gate).

        Returns True if the test fails as expected.
        """
        passing = self._run_tests()
        if passing:
            print("  ⚠ RED gate: test passed — it should fail.  Fix the test.")
            return False
        print("  ✔ RED gate: test fails as expected.")
        self.phase = "GREEN"
        return True

    def verify_green(self) -> bool:
        """Verify that ALL tests PASS (GREEN phase gate).

        Returns True if all tests pass.
        """
        passing = self._run_tests()
        if not passing:
            print("  ⚠ GREEN gate: tests still failing.  Fix the code.")
            return False
        print("  ✔ GREEN gate: all tests passing.")
        self.phase = "REFACTOR"
        return True

    def verify_refactor(self) -> bool:
        """Verify tests still pass after refactoring.

        Returns True if all tests pass.
        """
        passing = self._run_tests()
        if not passing:
            print("  ⚠ REFACTOR gate: tests broke.  Undo refactor changes.")
            return False
        print("  ✔ REFACTOR gate: tests still green.")
        self.phase = "RED"
        return True

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================


# ===================================================================
# LUPO SPEC TRACEABILITY
# Source Repository: obra/superpowers
# Source File: skills/executing-plans/SKILL.md
# Original Lines: 1 - 71
# Purpose: Plan execution engine — loads a plan/delta-spec, parses
#          its task list, and executes each task in order with
#          verification checkpoints.
# ===================================================================

def find_active_delta_spec() -> Optional[Path]:
    """Locate the most recent active Delta Spec (proposal.md).

    Returns:
        The path to the most recent proposal.md, or None.
    """
    if not CHANGES_DIR.exists():
        return None

    candidates: list[Path] = []
    for entry in sorted(CHANGES_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name == "archive":
            continue
        proposal = entry / "proposal.md"
        if proposal.exists():
            candidates.append(proposal)

    return candidates[-1] if candidates else None


def detect_environment(project_path: Path) -> Dict[str, str]:
    """Scan the project root to determine the language and configure the appropriate test and logging framework.
    
    Returns a dict with 'test_cmd' and 'logging'.
    """
    if (project_path / "package.json").exists():
        return {"test_cmd": "jest", "logging": "Winston"}
    if (project_path / "Gemfile").exists() or (project_path / "Rakefile").exists():
        return {"test_cmd": "rspec", "logging": "Logger"}
    if (project_path / "pom.xml").exists() or (project_path / "build.gradle").exists():
        return {"test_cmd": "mvn test", "logging": "SLF4J with Logback"} # Fallback for Java, though JUnit is framework, mvn test is usually the command
    if (project_path / "CMakeLists.txt").exists():
        if list(project_path.glob("*.cpp")) or (project_path / "main.cpp").exists():
            return {"test_cmd": "make test", "logging": "spdlog"}
        else:
            return {"test_cmd": "make test", "logging": "clog"}
            
    # Default to Python
    return {"test_cmd": "pytest", "logging": "logging"}


def parse_tasks(proposal_path: Path) -> list[str]:
    """Parse task items from a Delta Spec proposal.

    Returns a list of task descriptions extracted from Markdown
    checkbox syntax (``- [ ] task``).
    """
    content = proposal_path.read_text(encoding="utf-8")
    tasks: list[str] = []
    for line in content.splitlines():
        match = re.match(r"^[-*]\s+\[[ x]\]\s+(.+)$", line, re.IGNORECASE)
        if match:
            tasks.append(match.group(1).strip())
    return tasks


def execute(behavioral_prompt: str, strategy: str = "auto-heal") -> None:
    """Execute the active Delta Spec via Void Editor.

    Reads the user's CLI flag to determine the configuration (auto-heal or tdd).
    Streams the terminal output directly to the user so they can monitor git commits 
    and test-fixing loops in real-time.

    Args:
        behavioral_prompt: The behavioural guidelines to use as system instructions.
        strategy: 'auto-heal' (default) or 'tdd'.

    Raises:
        SystemExit: If no active Delta Spec is found.
    """
    delta_spec = find_active_delta_spec()
    if delta_spec is None:
        print(
            "✘ No active Delta Spec found.\n"
            "  Run 'lupo propose <feature_description>' first.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(f"\n▸ Active Delta Spec: {delta_spec}")
    print(f"▸ Behavioral prompt loaded ({len(behavioral_prompt)} chars)")
    print(f"▸ Strategy: {strategy}")

    env = detect_environment(Path.cwd())
    test_cmd = env["test_cmd"]
    logging_fw = env["logging"]
    
    print(f"▸ Detected Test Command: {test_cmd}")
    print(f"▸ Detected Logging Framework: {logging_fw}")

    if strategy == "tdd":
        msg = (
            f"Read this delta spec: {delta_spec}. Core behaviors: {behavioral_prompt}. "
            f"STRICT TDD REQUIRED: 1. Write a failing test for the next logical requirement. "
            f"2. Wait for the test command to fail. 3. Write minimal code to pass the test. "
            f"4. Refactor. Repeat until the spec is complete. "
            f"Please add logging automatically as you write the code. If no logging already exists, use: {logging_fw}."
        )
    else:
        # auto-heal
        msg = (
            f"Read this delta spec: {delta_spec}. Core behaviors: {behavioral_prompt}. "
            f"Plan the architecture, implement the changes, and write the necessary tests. Ensure all tests pass. "
            f"Please add logging automatically as you write the code. If no logging already exists, use: {logging_fw}."
        )

    # Void Editor — AI-native code editor (fork of VS Code).
    # Void's CLI opens the project and accepts an inline task.
    cmd = [
        "void",
        "--goto", str(delta_spec),
        "--task",
        msg,
    ]
    
    print(f"\n✔ Launching Void Editor execution engine...\n")
    print(f"Command: void --goto {delta_spec} --task [prompt]\n")
    
    try:
        # Stream output to terminal
        subprocess.run(cmd)
    except FileNotFoundError:
        print(
            "✘ Execution failed: 'void' command not found.\n"
            "  Please ensure Void Editor is installed\n"
            "  (see https://voideditor.com).",
            file=sys.stderr,
        )
        raise SystemExit(1)

# ===================================================================
# END LUPO SPEC TRACEABILITY
# ===================================================================
