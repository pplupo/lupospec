# Lupo Spec Evolution Guide

This document outlines the standard operating procedure for maintaining and updating Lupo Spec when its upstream repositories evolve. Because Lupo Spec natively implements logic from external repositories using a strict **Traceability Protocol**, it relies on the **Evolution Engine** (`sync_repos.py`) to detect upstream changes and the **Self-Patch Protocol** to adapt to them.

## 1. Running the Evolution Engine

The `sync_repos.py` script acts as an intelligent dependency scanner. You must run this script periodically to verify that Lupo Spec's internal Python logic is synchronized with the upstream frameworks.

**Command:**
```bash
python sync_repos.py
```

### What `sync_repos.py` does:

1. **Scans Lupo Spec:** Reads all `.py` files inside `/src/core/`. Using regular expressions, it extracts all `LUPO SPEC TRACEABILITY` blocks to build an internal map of: `Repository -> Source File -> Tracked Lines`.
2. **Updates Upstream Repositories:** Iterates through the cloned repositories in your project root (`spec-kit`, `openspec`, `superpowers`, `andrej-karpathy-skills`) and performs a `git pull` on each.
3. **Diff Analysis:** If a repository was updated, it executes a `git diff` against the previous revision.
4. **Intersection Check:** Cross-references the `git diff` output against the internal map of tracked lines. This identifies if an upstream update altered any of the specific source files and line ranges that Lupo Spec currently relies on.
5. **Generates the Report:** Outputs an `evolution_map.json` file. This JSON details exactly which Traceability Blocks in Lupo Spec are now out-of-date or "stale", and includes a full sync report containing the repo names, sync status, `previous_revision`, and `current_revision` for all upstream sources.
6. **Prompt Injection:** Automatically copies the latest `CLAUDE.md` from the Karpathy skills repository into `/src/prompts/lupospec_BEHAVIOUR.md`.

## 2. Antigravity Self-Patch Protocol

If `evolution_map.json` reports that there are stale Traceability Blocks, you must prompt the AI agent (Antigravity) to initiate the Self-Patch Protocol.

The agent must strictly follow these steps to update Lupo Spec:

1. **Read the Report:** Parse `evolution_map.json` to identify the flagged traceability blocks.
2. **Locate Upstream Changes:** For each flagged block, locate the newly updated source file in the cloned upstream repository.
3. **Analyze the Logic:** Determine how the upstream logic has changed (e.g., did OpenSpec alter its proposing logic? Did Superpowers change its test-runner behavior?).
4. **Re-transpile:** Port the updated upstream logic into native Python.
5. **Replace the Stale Block:** Edit the target `/src/core/` file and replace the outdated Python block with the newly transpiled logic.
6. **Update the Traceability Header:** Modify the `Original Lines: [Start Line] - [End Line]` field within the `LUPO SPEC TRACEABILITY` header to accurately reflect the new state and location of the logic in the upstream repository.

By following this protocol, Lupo Spec guarantees that it never drifts out of sync with the industry standards it wraps, while remaining a fast, dependency-free native framework.
