# User & AI Agent Surface Subsystem

The user and AI agent surface in Mốc Nghề is built on the principle of **Dual-Interface Parity**: every operational capability available to human engineers via the Command Line Interface (`CLI`) is equally accessible to autonomous AI agents through shell tools or concise Slash Commands, adhering to identical validation rules.

---

## 1. High-Level Architecture

```
                 +-------------------------------------------------------------+
                 |                      HUMAN USER / AI AGENT                  |
                 +------------------------------+------------------------------+
                                                |
                        +-----------------------+-----------------------+
                        |                                               |
                        v                                               v
        [ Human Engineer ]                               [ Autonomous AI Agent ]
        - Terminal Shell (Bash/Zsh)                      - Hermes Agent
        - CI/CD Pipelines / Makefiles                    - Cursor / Claude Code / OpenCode
                        |                                               |
                        | (Explicit CLI syntax)                         | (Slash Commands / Prompts)
                        |                                               |
                        |       /crawl, /onboard, /triage, /tailor, /track
                        |                               |
                        +---------------+---------------+
                                        |
                                        v
                        +-------------------------------+
                        |       Agent Dispatch Layer    |
                        |   .cursor/rules/mocnghe.md    |
                        |   .agents/skills/mocnghe/     |
                        |   ~/.hermes/skills/mocnghe/   |
                        +---------------+---------------+
                                        |
                                        v
                        +-------------------------------+
                        |       Typer CLI Engine        |
                        |         (src/mocnghe/cli.py)  |
                        +---------------+---------------+
                                        |
         +------------------------------+------------------------------+
         |                              |                              |
         v                              v                              v
  [ jobs Subcommand ]          [ profile Subcommand ]        [ evaluate Subcommand ]
  - crawl / search / ingest    - confirm-file / validation   - triage / export-packet
         |                              |                              |
         +------------------------------+------------------------------+
                                        |
                                        v
                        [ cv / draft / track Subcommands ]
                        - create / revise / approve / export
                        - track / apply
```

---

## 2. Component Details

### 2.1. Typer CLI Engine (`src/mocnghe/cli.py`)
Mốc Nghề uses `typer` to deliver structured, discoverable CLI subcommands:
- **Hierarchical Subcommand Apps:**
  - `jobs_app`: Job posting operations (`crawl`, `search`, `ingest`, `list`, `show`).
  - `profile_app`: Candidate profile lifecycle (`confirm-file`, `validation`, `answer`, `review`, `correct`, `confirm`).
  - `evaluate_app`: Alignment evaluation and packet import/export (`triage`, `export-packet`, `import-report`).
  - `cv_app`: CV authoring, revision, cryptographic review, approval, and PDF rendering (`create`, `revise`, `review`, `approve`, `export`, `export-packet`, `import-response`).
  - `draft_app`: Application letter and form response mapping (`create`, `review`, `approve`, `export`).
  - `applications_app` & `track` / `apply`: Linear state machine progression.
- **Strict Option Mutual Exclusion:** Conflicting flags (e.g. `--file`, `--stdin`, and `--url` in `import-jd`) are validated upfront with clear exit codes.

### 2.2. Agent Rules & Skills Layer
To enable autonomous agents (Cursor, Claude Code, OpenCode) to operate Mốc Nghề without prompting human users for syntax:
- **`.cursor/rules/mocnghe.md`**: Injected automatically into Cursor workspaces, routing commands like `/crawl` or `/tailor` directly to `uv run mocnghe ...`.
- **`.agents/skills/mocnghe/SKILL.md`**: Universal standard skill definition for autonomous coding agents.
- **Hermes Global Skill (`~/.hermes/skills/productivity/mocnghe/`)**: System-wide skill enabling Hermes to invoke CLI commands across any session.

---

## 3. Safety Guardrails for Agent-Driven Execution

1. **Machine-Readable Structured Outputs:**
   - Operational commands (`review`, `track`, `validation`) output clean JSON or structured key-value pairs, allowing agents to parse state without regex guessing.
2. **Untrusted Content Isolation:**
   - All external text (scraped JDs, web pages) is treated strictly as passive data, never executed as shell instructions, preventing **Indirect Prompt Injection**.
3. **Cryptographic Approval Gate:**
   - Agents can propose claim revisions (`cv revise`) or application drafts, but cannot publish or export PDFs without an explicit SHA-256 hash confirmation (`--hash <content_hash>`).
   - The final `apply` command remains strictly human-controlled.
