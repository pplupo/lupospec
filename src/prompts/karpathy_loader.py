"""
karpathy_loader.py

Exposes a function that reads the dynamically-injected behavioural
guidelines. This content is prepended as the system instructions for all
LLM calls made during the ``execute`` phase.

The v2 spec renames the file to ``lupospec_BEHAVIOUR.md``.  For
backward compatibility we fall back to ``CLAUDE.md`` if the new name
is not found.
"""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent
_BEHAVIOUR_V2 = _PROMPTS_DIR / "lupospec_BEHAVIOUR.md"
_BEHAVIOUR_V1 = _PROMPTS_DIR / "CLAUDE.md"


def load_behavioral_prompt() -> str:
    """Read and return the contents of the behavioural guidelines.

    Checks for ``lupospec_BEHAVIOUR.md`` first (v2), then falls back
    to ``CLAUDE.md`` (v1).

    Returns:
        The full text of the behavioural-guidelines file.

    Raises:
        FileNotFoundError: If neither file exists.
            Run ``python sync_repos.py`` from the project root first.
    """
    for candidate in (_BEHAVIOUR_V2, _BEHAVIOUR_V1):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")

    raise FileNotFoundError(
        f"Behavioral prompt not found at {_BEHAVIOUR_V2} or {_BEHAVIOUR_V1}.\n"
        "Run 'python sync_repos.py' from the project root to inject it."
    )
