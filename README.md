# Lupo Spec

Lupo Spec is a standalone, native Python framework designed for **Spec-Driven Development (SDD)**. It evolves away from relying on heavy Node.js or `uv` package subprocess wrappers and instead natively implements the core logics from upstream SDD repositories (Spec Kit, OpenSpec, Superpowers, and Andrej Karpathy's behavioral skills). 

By using strict **Traceability Headers** across its source code, Lupo Spec functions autonomously while remaining a clearly attributed derivative work. It features an intelligent **Evolution Engine** (`sync_repos.py`) that syncs and cross-references your Python framework code against the upstream repositories to let you know exactly when your logic is out of date.

## 📁 Repository Organization

The project strictly adheres to the following layout:

```text
/lupospec
  ├── sync_repos.py                     # Evolution Engine for updating traceability blocks
  ├── evolution_map.json                # JSON report of stale traceability blocks
  ├── /spec-kit                         # Cloned GitHub Spec Kit (upstream)
  ├── /openspec                         # Cloned OpenSpec (upstream)
  ├── /superpowers                      # Cloned Superpowers (upstream)
  ├── /andrej-karpathy-skills           # Cloned Karpathy Skills (upstream)
  ├── /docs                             # Project documentation
  └── /src                              # Lupo Spec Native Source Code
      ├── lupospec_cli.py               # Typer CLI router (`lupo`)
      ├── core/
      │   ├── lupospec_init.py          # Port of Spec Kit's PRD/Architecture generation
      │   ├── lupospec_workflow.py      # Port of OpenSpec's propose/archive logic
      │   └── lupospec_agent_execution.py # Port of Superpowers' Git/TDD execution
      └── prompts/
          └── lupospec_BEHAVIOUR.md     # CLAUDE.md auto-injected from karpathy-skills
```

### Core Modules

* **`lupospec_init.py`:** Bootstraps a greenfield project. It natively creates a `docs/architecture/` directory, writes a Constitution, a PRD template (`spec.md`), an implementation plan template (`plan.md`), and optionally initializes a Git repository.
* **`lupospec_workflow.py`:** Replaces `openspec propose` and `openspec archive`. It scans existing architecture docs, creates new Markdown change proposals (Delta Specs) in `openspec/changes/`, and subsequently moves completed changes into `openspec/changes/archive/` with a date prefix.
* **`lupospec_agent_execution.py`:** The powerhouse script that acts as the proxy for **Void Editor** (AI-native code editor, fork of VS Code, invoked via the `void` CLI). It auto-detects your testing environment and your logging framework, loads your behavioral instructions, parses your tasks, and kicks off your chosen execution strategy directly in your terminal.
* **`lupospec_cli.py`:** The router script that exposes the `lupo` command-line tool.

---

## 🛠️ Getting Started

### 1. Installation

To install Lupo Spec, install it locally into a virtual environment or using `pipx`:

```bash
# From the lupospec root directory
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Evolution Engine (`sync_repos.py`)

Run the Evolution Engine to verify your local code isn't out of date compared to the upstream reference repos:

```bash
python sync_repos.py
```

This will:
1. Scan `src/core/*.py` for `LUPO SPEC TRACEABILITY` blocks.
2. Run `git pull` on the 4 upstream repositories.
3. Compare `git diff` on the upstream against the tracked line numbers to check if the upstream framework changed any logic Lupo Spec relies on.
4. Export `evolution_map.json` marking any out-of-date blocks.
5. Inject the latest `CLAUDE.md` from Karpathy's skills into `src/prompts/lupospec_BEHAVIOUR.md`.

---

## 🚀 CLI Usage

Once installed, use the `lupo` command:

### 1. Initialize a Project

```bash
lupo init <project_name>
```
Creates `docs/architecture/constitution.md`, `plan.md`, and `spec.md`. It automatically initializes git for you.

### 2. Propose a Feature

```bash
lupo propose "Add a simple hello world CLI"
```
Creates a new Delta Spec under `openspec/changes/add-a-simple-hello-world-cli/proposal.md` pre-filled with context tags pointing to your architecture docs.

### 3. Execute the Delta Spec

```bash
lupo execute [--strategy <auto-heal|tdd>]
```
Scans for the active Delta Spec, determines the testing/logging environment, injects the behavioral prompt, and executes your agent (`aider`).

### 4. Archive a Feature

```bash
lupo archive
```
Moves the completed Delta Spec into `openspec/changes/archive/2026-XX-YY-change-name` so you keep your workspace clean.

---

## 🤖 Autodetection & Agent Execution

When you run `lupo execute`, Lupo Spec automatically scans your project's root directory to determine what language and tools you are using.

### 1. Testing Frameworks
It configures the appropriate test command (`--test-cmd`) based on what it finds:

* **JavaScript/Node:** `jest` (Triggered by `package.json`)
* **Ruby:** `rspec` (Triggered by `Gemfile` or `Rakefile`)
* **Java:** `mvn test` running JUnit (Triggered by `pom.xml` or `build.gradle`)
* **C/C++:** `make test` running GoogleTest (Triggered by `CMakeLists.txt` and `.cpp` files)
* **Python (Default):** `pytest` (Fallback for Python or generic environments)

### 2. Logging Frameworks
The agent is explicitly instructed to automatically add logging as it writes the code using the canonical framework for your language:

* **JavaScript/Node:** `Winston`
* **Ruby:** `Logger`
* **Java:** `SLF4J with Logback`
* **C++:** `spdlog`
* **C:** `clog`
* **Python (Default):** `logging`

---

## ⚙️ Execution Strategies

Lupo Spec exposes two execution strategies. The strategy changes the prompt delivered to the agent (`aider`) modifying its runtime behavior:

### Strategy A: Auto-Heal (Default)
**Command:** `lupo execute` or `lupo execute --strategy auto-heal`

* **Behavior:** The agent implements the required architecture and changes first, writes the necessary tests, and then continuously runs tests—automatically healing the code until the entire test suite passes.
* **Prompt Logic:** "Plan the architecture, implement the changes, and write the necessary tests. Ensure all tests pass."

### Strategy B: Strict TDD
**Command:** `lupo execute --strategy tdd`

* **Behavior:** Enforces a strict **Red-Green-Refactor** loop natively within the chat flow. The agent will not jump ahead. It will write a failing test, pause for the test to fail, write the minimal passing code, and then refactor.
* **Prompt Logic:** "STRICT TDD REQUIRED: 1. Write a failing test for the next logical requirement. 2. Wait for the test command to fail. 3. Write minimal code to pass the test. 4. Refactor. Repeat until the spec is complete."

Because Lupo Spec uses Python `subprocess` without capturing output directly, all agent interactions, git commits, and test-fixing loops are **streamed in real-time** to your terminal.
