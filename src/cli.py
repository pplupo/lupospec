#!/usr/bin/env python3
"""
cli.py — Lupo Spec CLI

The main entry point for the Lupo Spec CLI tool.  Routes user intent
through Spec Kit, OpenSpec, and OpenCode/Superpowers via a clean Typer
interface.

Usage:
    lupo init <project_name>
    lupo propose <feature_description>
    lupo execute
    lupo archive
"""

import sys
from pathlib import Path

import typer

# ---------------------------------------------------------------------------
# Ensure the project root is importable regardless of how the CLI is invoked
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.orchestrators import spec_kit, open_spec
from src.orchestrators import superpowers as superpowers_orch
from src.prompts.karpathy_loader import load_behavioral_prompt

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="lupo",
    help=(
        "Lupo Spec — a hybrid Spec-Driven Development CLI.\n\n"
        "Orchestrates GitHub Spec Kit, OpenSpec, and OpenCode/Superpowers "
        "to take a project from architectural blueprint through "
        "test-driven implementation."
    ),
    add_completion=False,
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# Command 1: lupo init <project_name>
# ---------------------------------------------------------------------------

@app.command()
def init(
    project_name: str = typer.Argument(
        ...,
        help="Name of the new project to bootstrap.",
    ),
) -> None:
    """Bootstrap a greenfield project with GitHub Spec Kit.

    Runs ``specify init``, defines the constitution, generates the PRD
    and architecture plan, and ensures artifacts are saved to
    ``docs/architecture/`` for downstream consumption by OpenSpec.
    """
    spec_kit.init_project(project_name)


# ---------------------------------------------------------------------------
# Command 2: lupo propose <feature_description>
# ---------------------------------------------------------------------------

@app.command()
def propose(
    feature_description: str = typer.Argument(
        ...,
        help="A short description of the feature to propose.",
    ),
) -> None:
    """Propose a feature delta via OpenSpec.

    Reads the existing architecture blueprints, invokes
    ``openspec /opsx:propose``, and verifies that a Delta Spec
    markdown file has been generated.
    """
    delta = open_spec.propose(feature_description)
    if delta is None:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Command 3: lupo execute
# ---------------------------------------------------------------------------

@app.command()
def execute() -> None:
    """Execute the active Delta Spec via OpenCode + Superpowers.

    Locates the active Delta Spec, loads the behavioral guidelines
    from CLAUDE.md, and launches OpenCode with the Superpowers agent
    to implement the spec using strict TDD.
    """
    try:
        behavioral_prompt = load_behavioral_prompt()
    except FileNotFoundError as exc:
        typer.echo(f"✘ {exc}", err=True)
        raise typer.Exit(code=1)

    superpowers_orch.execute(behavioral_prompt)


# ---------------------------------------------------------------------------
# Command 4: lupo archive
# ---------------------------------------------------------------------------

@app.command()
def archive() -> None:
    """Archive the implemented Delta Spec and update master docs.

    Runs ``openspec /opsx:archive`` to delete the temporary Delta Spec
    and merge changes back into the master architecture documents.
    """
    open_spec.archive()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
