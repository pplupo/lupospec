#!/usr/bin/env python3
"""
The Evolution Engine v2 (sync_repos.py)

An intelligent dependency scanner that:
  1. Scans Lupo Spec's ``/src/core/*.py`` for Traceability Headers.
  2. Pulls upstream repositories.
  3. Diffs any changed repos and cross-references with tracked lines.
  4. Generates ``evolution_map.json`` listing stale traceability blocks.
  5. Copies CLAUDE.md → src/prompts/lupospec_BEHAVIOUR.md.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent

TARGET_REPOS = {
    "spec-kit": "https://github.com/github/spec-kit.git",
    "openspec": "https://github.com/fission-ai/openspec.git",
    "superpowers": "https://github.com/obra/superpowers.git",
    "karpathy-skills": {
        "url": "https://github.com/forrestchang/andrej-karpathy-skills.git",
        "local_dir": "andrej-karpathy-skills",
    },
}

EVOLUTION_MAP_PATH = ROOT_DIR / "evolution_map.json"
KARPATHY_SOURCE = ROOT_DIR / "andrej-karpathy-skills" / "CLAUDE.md"
KARPATHY_DEST = ROOT_DIR / "src" / "prompts" / "lupospec_BEHAVIOUR.md"
CORE_DIR = ROOT_DIR / "src" / "core"

# ---------------------------------------------------------------------------
# Traceability header regex
# ---------------------------------------------------------------------------

# Matches blocks like:
#   # LUPO SPEC TRACEABILITY
#   # Source Repository: fission-ai/openspec
#   # Source File: src/commands/change.ts
#   # Original Lines: 242 - 260
#   # Purpose: ...
_TRACE_BLOCK_RE = re.compile(
    r"^# ={3,}\n"
    r"# LUPO SPEC TRACEABILITY\n"
    r"# Source Repository:\s*(?P<repo>.+)\n"
    r"# Source File:\s*(?P<file>.+)\n"
    r"# Original Lines:\s*(?P<start>\d+)\s*-\s*(?P<end>\d+)\n"
    r"# Purpose:\s*(?P<purpose>.+?)(?:\n#\s{10,}.+)*\n"
    r"# ={3,}",
    re.MULTILINE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a subprocess command and return the result."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def _get_head(repo_path: Path) -> str:
    """Return the current HEAD revision of a git repository."""
    result = _run(["git", "rev-parse", "HEAD"], cwd=repo_path)
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Step 1: Scan Lupo Spec for Traceability Headers
# ---------------------------------------------------------------------------


def scan_traceability_blocks() -> list[dict[str, Any]]:
    """Read all ``.py`` files in ``src/core/`` and extract Traceability blocks.

    Returns a list of dicts with keys:
        lupo_file, repo, source_file, start_line, end_line, purpose
    """
    blocks: list[dict[str, Any]] = []

    if not CORE_DIR.exists():
        return blocks

    for py_file in sorted(CORE_DIR.glob("*.py")):
        content = py_file.read_text(encoding="utf-8")
        for m in _TRACE_BLOCK_RE.finditer(content):
            blocks.append({
                "lupo_file": str(py_file.relative_to(ROOT_DIR)),
                "repo": m.group("repo").strip(),
                "source_file": m.group("file").strip(),
                "start_line": int(m.group("start")),
                "end_line": int(m.group("end")),
                "purpose": m.group("purpose").strip(),
            })

    return blocks


# ---------------------------------------------------------------------------
# Step 2 & 3: Sync repos and capture diffs
# ---------------------------------------------------------------------------

# Map from traceability repo names to local directory names
_REPO_TO_LOCAL = {
    "github/spec-kit": "spec-kit",
    "fission-ai/openspec": "openspec",
    "obra/superpowers": "superpowers",
    "forrestchang/andrej-karpathy-skills": "andrej-karpathy-skills",
}


def sync_repo(name: str, url: str, local_dir: str) -> dict[str, Any]:
    """Clone or pull a single repository and return its sync entry."""
    repo_path = ROOT_DIR / local_dir

    if not repo_path.exists() or not (repo_path / ".git").exists():
        print(f"  [clone] {name} → {local_dir}/")
        _run(["git", "clone", url, str(repo_path)])
        current_revision = _get_head(repo_path)
        return {
            "name": name,
            "local_dir": local_dir,
            "url": url,
            "status": "cloned",
            "previous_revision": None,
            "current_revision": current_revision,
        }
    else:
        previous_revision = _get_head(repo_path)
        print(f"  [pull]  {name} ({previous_revision[:8]}…)")
        _run(["git", "pull"], cwd=repo_path)
        current_revision = _get_head(repo_path)
        status = "updated" if previous_revision != current_revision else "up-to-date"
        return {
            "name": name,
            "local_dir": local_dir,
            "url": url,
            "status": status,
            "previous_revision": previous_revision,
            "current_revision": current_revision,
        }


def sync_all() -> list[dict[str, Any]]:
    """Iterate through all target repositories and sync them."""
    report: list[dict[str, Any]] = []

    for name, value in TARGET_REPOS.items():
        if isinstance(value, dict):
            url = value["url"]
            local_dir = value["local_dir"]
        else:
            url = value
            local_dir = name

        try:
            entry = sync_repo(name, url, local_dir)
        except subprocess.CalledProcessError as exc:
            print(f"  [ERROR] {name}: {exc.stderr.strip()}", file=sys.stderr)
            entry = {
                "name": name,
                "local_dir": local_dir,
                "url": url,
                "status": "error",
                "previous_revision": None,
                "current_revision": None,
                "error": exc.stderr.strip(),
            }
        report.append(entry)

    return report


# ---------------------------------------------------------------------------
# Step 4: Intersection Check — find stale traceability blocks
# ---------------------------------------------------------------------------


def _get_changed_files(repo_path: Path, prev_rev: str, curr_rev: str) -> set[str]:
    """Return set of file paths changed between two revisions."""
    try:
        result = _run(
            ["git", "diff", "--name-only", prev_rev, curr_rev],
            cwd=repo_path,
        )
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except subprocess.CalledProcessError:
        return set()


def _get_changed_lines(
    repo_path: Path,
    prev_rev: str,
    curr_rev: str,
    file_path: str,
) -> set[int]:
    """Return set of line numbers affected in *file_path* between two revisions.

    Parses the unified diff hunk headers to extract changed line ranges.
    """
    try:
        result = _run(
            ["git", "diff", "-U0", prev_rev, curr_rev, "--", file_path],
            cwd=repo_path,
        )
    except subprocess.CalledProcessError:
        return set()

    changed: set[int] = set()
    for line in result.stdout.splitlines():
        # Hunk header format: @@ -old_start,old_count +new_start,new_count @@
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? ", line)
        if m:
            start = int(m.group(1))
            count = int(m.group(2)) if m.group(2) else 1
            changed.update(range(start, start + count))
    return changed


def check_staleness(
    blocks: list[dict[str, Any]],
    sync_report: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Cross-reference traceability blocks with upstream diffs.

    Returns a list of stale blocks (those whose tracked source lines
    were modified upstream).
    """
    # Build a quick lookup: repo_short_name → sync entry
    repo_sync: dict[str, dict] = {}
    for entry in sync_report:
        repo_sync[entry["name"]] = entry
        # Also index by local_dir for flexible matching
        repo_sync[entry["local_dir"]] = entry

    stale: list[dict[str, Any]] = []

    for block in blocks:
        repo_name = block["repo"]
        local_dir = _REPO_TO_LOCAL.get(repo_name)

        if local_dir is None:
            continue

        entry = repo_sync.get(local_dir)
        if entry is None:
            continue

        prev = entry.get("previous_revision")
        curr = entry.get("current_revision")
        if prev is None or curr is None or prev == curr:
            continue  # freshly cloned or no changes

        repo_path = ROOT_DIR / local_dir

        # Check if the specific source file was changed
        changed_files = _get_changed_files(repo_path, prev, curr)
        if block["source_file"] not in changed_files:
            continue

        # Check if the specific line range was affected
        changed_lines = _get_changed_lines(
            repo_path, prev, curr, block["source_file"]
        )
        tracked_range = set(range(block["start_line"], block["end_line"] + 1))

        if changed_lines & tracked_range:
            stale.append({
                **block,
                "upstream_repo": local_dir,
                "previous_revision": prev,
                "current_revision": curr,
                "stale": True,
            })

    return stale


# ---------------------------------------------------------------------------
# Step 5: Generate evolution_map.json
# ---------------------------------------------------------------------------


def write_evolution_map(
    blocks: list[dict[str, Any]],
    stale: list[dict[str, Any]],
    sync_report: list[dict[str, Any]],
) -> None:
    """Write the ``evolution_map.json`` report."""
    evolution_map = {
        "total_traceability_blocks": len(blocks),
        "stale_blocks": len(stale),
        "sync_report": sync_report,
        "stale_details": stale,
    }
    EVOLUTION_MAP_PATH.write_text(
        json.dumps(evolution_map, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  Report written to {EVOLUTION_MAP_PATH.name}")


# ---------------------------------------------------------------------------
# Step 6: Prompt injection
# ---------------------------------------------------------------------------


def inject_prompts() -> None:
    """Copy CLAUDE.md → src/prompts/lupospec_BEHAVIOUR.md."""
    if not KARPATHY_SOURCE.exists():
        print(
            "  [WARN] andrej-karpathy-skills/CLAUDE.md not found — "
            "skipping prompt injection.",
            file=sys.stderr,
        )
        return

    KARPATHY_DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(KARPATHY_SOURCE, KARPATHY_DEST)
    print(f"  Injected {KARPATHY_SOURCE.name} → {KARPATHY_DEST.relative_to(ROOT_DIR)}")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------


def main() -> None:
    print("╔══════════════════════════════════════════╗")
    print("║   Lupo Spec — Evolution Engine v2        ║")
    print("╚══════════════════════════════════════════╝\n")

    # Step 1: Scan traceability blocks
    print("▸ Scanning traceability blocks in src/core/ …")
    blocks = scan_traceability_blocks()
    print(f"  Found {len(blocks)} traceability block(s).\n")

    # Step 2: Sync upstream repos
    print("▸ Syncing upstream repositories …")
    sync_report = sync_all()

    # Step 3 & 4: Diff + intersection check
    print("\n▸ Checking for stale traceability blocks …")
    stale = check_staleness(blocks, sync_report)
    if stale:
        print(f"  ⚠ {len(stale)} block(s) are out-of-date:")
        for s in stale:
            print(f"    • {s['lupo_file']}: {s['source_file']} L{s['start_line']}-{s['end_line']}")
    else:
        print("  ✔ All traceability blocks are current.")

    # Step 5: Write evolution_map.json
    print("\n▸ Writing evolution map …")
    write_evolution_map(blocks, stale, sync_report)

    # Step 6: Inject behavioral prompts
    print("\n▸ Injecting behavioral prompts …")
    inject_prompts()

    print("\n✔ Evolution Engine v2 complete.\n")


if __name__ == "__main__":
    main()
