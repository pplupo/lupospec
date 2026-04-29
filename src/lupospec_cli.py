#!/usr/bin/env python3
"""
lupospec_cli.py — Lupo Spec Native CLI (v2)

The main entry point for the Lupo Spec CLI tool.  Routes user commands
to the native Python implementations in ``core/``.

Usage:
    lupo init <project_name>
    lupo propose <feature_description>
    lupo execute
    lupo archive [change_name]
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

# ---------------------------------------------------------------------------
# Ensure the project root is importable regardless of invocation method
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core import lupospec_init, lupospec_workflow, lupospec_agent_execution
from src.prompts.karpathy_loader import load_behavioral_prompt

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="lupo",
    help=(
        "Lupo Spec — a native Spec-Driven Development framework.\n\n"
        "Orchestrates project initialisation, feature proposals, "
        "test-driven execution, and documentation archiving without "
        "any external subprocess dependencies."
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
    """Bootstrap a greenfield project with architecture scaffolding.

    Creates the project directory, generates the constitution, PRD
    template, and architecture plan, and initialises Git.
    """
    print(f"\n▸ Initialising project '{project_name}' …\n")
    project_path = lupospec_init.init_project(project_name)
    print(f"\n✔ Project '{project_name}' ready at {project_path}\n")


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
    """Propose a feature delta.

    Generates a Delta Spec (change proposal) containing the feature
    description, requirement placeholders, and a task checklist.
    """
    print(f"\n▸ Proposing feature: {feature_description}\n")
    delta = lupospec_workflow.propose(feature_description)
    if delta is None:
        raise typer.Exit(code=1)
    print()


# ---------------------------------------------------------------------------
# Command 3: lupo execute
# ---------------------------------------------------------------------------

@app.command()
def execute(
    strategy: str = typer.Option(
        "auto-heal",
        "--strategy",
        help="Execution strategy to use: 'auto-heal' (default) or 'tdd'.",
    )
) -> None:
    """Execute the active Delta Spec using the chosen strategy.

    Locates the active Delta Spec, loads the behavioural guidelines,
    and launches the agent execution engine (e.g. aider) to implement
    the changes and fix tests natively.
    """
    try:
        behavioral_prompt = load_behavioral_prompt()
    except FileNotFoundError as exc:
        typer.echo(f"✘ {exc}", err=True)
        raise typer.Exit(code=1)

    lupospec_agent_execution.execute(behavioral_prompt, strategy=strategy)


# ---------------------------------------------------------------------------
# Command 4: lupo archive [change_name]
# ---------------------------------------------------------------------------

@app.command()
def archive(
    change_name: str = typer.Argument(
        None,
        help="Change ID to archive.  If omitted, the most recent is used.",
    ),
) -> None:
    """Archive a completed Delta Spec and update master docs.

    Moves the change proposal into the archive directory with a
    date-prefix and reports the remaining active changes.
    """
    print("\n▸ Archiving Delta Spec …\n")
    lupospec_workflow.archive(change_name)
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
