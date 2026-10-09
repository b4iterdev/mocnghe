# Architecture & Operations Guide — Mốc Nghề (mocnghe)

Mốc Nghề is a **local-first career operations** platform designed to streamline and manage the end-to-end job search lifecycle: automated job ingestion, fit triage, evidence-grounded CV tailoring, application drafting, and submission tracking.

This document is crafted for humans (developers, job seekers, and admins) to clearly understand system architecture, data models, and operation alongside AI agents.

---

## 1. Core Design Principles

1. **Local-First & Data Privacy:**
   - Candidate facts, application logs, and profile records remain strictly on local storage (`SQLite`).
   - No automatic emails or form submissions. The candidate retains ultimate authority (`human-controlled submissions`).
2. **Evidence-Grounded:**
   - Every bullet or claim in a CV must trace directly to a verified record (`CandidateEvidence`).
   - Zero tolerance for hallucinated metrics; volunteer or project work is never falsely framed as full-time employment.
3. **Audit & Tamper-Evident:**
   - Every CV revision and application snapshot is fingerprinted with SHA-256 (`content_hash`). Unreviewed manual modifications directly to the database fail integrity checks.
4. **Agent & CLI Parity:**
   - Every operation is accessible either via direct command line (`Typer CLI`) or conversational AI agents via Slash Commands.

---

## 2. System Architecture Diagram

```
                                    +-----------------------------------------+
                                    |         User & AI Agent Surface         |
                                    |  (CLI / Cursor Rules / Hermes Skills)   |
                                    +--------------------+--------------------+
                                                         |
                                 +-----------------------+-----------------------+
                                 |                                               |
                                 v                                               v
                     [ Ingestion Subsystem ]                         [ Candidate & Career Subsystem ]
            +---------------------------------------+               +---------------------------------------+
            |  - Modular Site Adapters:             |               |  - Profile: Evidence & Facts Storage  |
            |    * Greenhouse, ITviec, Indeed       |               |  - Triage Engine: Fit Evaluation      |
            |    * Generic Fallback (Metadata/DOM)  |               |  - CV Engine: Revisions & PDF Render  |
            |  - Playwright Headless Engine         |               |  - Application Drafts & Form Mapping  |
            +-------------------+-------------------+               +-------------------+-------------------+
                                |                                                       |
                                +---------------------------+---------------------------+
                                                            |
                                                            v
                                            +-------------------------------+
                                            |     Local Database (Storage)  |
                                            |   - SQLite (careerviet.sqlite3)
                                            |   - SHA-256 Content Validation|
                                            +-------------------------------+
```

### 📚 Deep-Dive Technical References
To inspect source-level implementations and runtime lifecycles across each subsystem:
- 📑 [CV Processing Lifecycle](cv_processing_lifecycle_en.md) — 6-step breakdown from raw CV upload to publication PDF.
- 🖥️ [User & AI Agent Surface](internals/surface_en.md) — Typer CLI architecture, Agent Skills dispatch layer, Slash Commands, and prompt injection guardrails.
- 💾 [Local Database & Storage](internals/storage_en.md) — SQLite schema relational layout, backward compatibility, read-time SHA-256 tamper checks, and diagnostics.
- 🌐 [Ingestion & Web Crawlers](internals/ingestion_en.md) — Site adapters, headless Playwright runner, and content deduplication.
- 👤 [Profile & Grounded Evidence](internals/profile_en.md) — Atomic evidence model, profile immutability, and fact requirement gates.
- 🎯 [Triage & Evaluation](internals/evaluation_en.md) — Heading/bullet extractor, offline screening, and PII-stripped evaluation packets.
- 📄 [CV Tailoring & PDF Render](internals/cv_render_en.md) — Structured claims, cryptographic approval gates, and ReportLab canvas limits.
- 📊 [Application Tracking](internals/tracking_en.md) — Unidirectional state machine, submission audit snapshots, and human-in-the-loop apply gates.

---

## 3. Standard End-to-End Workflow

The 5-step lifecycle from discovering a job to recording an application:

```
[1. Ingest JD]   ==>   [2. Triage Fit]   ==>   [3. Tailor CV]   ==>   [4. Create Draft]   ==>   [5. Tracking]
  /crawl URL            /triage <id>           /tailor <id>           /draft create            /track ready
```

### Step 1: Ingest Job Description (`Ingestion`)
Specialized adapters extract structured fields directly from URLs, falling back to Playwright if the target relies on client-side rendering (SPA) or anti-bot challenges.

- **Slash command:** `/crawl <URL>`
- **CLI:**
  ```bash
  uv run mocnghe jobs crawl "https://itviec.com/it-jobs/..."
  # Add --browser for dynamic JavaScript pages
  uv run mocnghe jobs crawl "https://indeed.com/viewjob?jk=..." --browser
  ```

### Step 2: Fit Evaluation (`Triage`)
Matches automatically extracted requirements from the JD against verified proof points in `profile.json`.

- **Slash command:**
  - Onboard/Confirm: `/onboard`
  - Evaluate: `/triage <job_id>`
- **CLI:**
  ```bash
  uv run mocnghe profile confirm-file
  uv run mocnghe evaluate triage <job_id>
  ```
- **Triage Verdicts:**
  - `practical_fit`: Strong evidence match across requirements.
  - `evaluate_with_unknowns`: Acceptable, but requires manual confirmation on unstated constraints.
  - `not_fit`: Hard violations (location mismatch, employment type, salary floor).

### Step 3: CV Tailoring & PDF Export
Produces a version-controlled CV revision bound to the target JD ID, extracts relevant evidence, and renders clean A4 PDFs:

- **Slash command:** `/tailor <job_id>`
- **CLI:**
  ```bash
  # 1. Create initial CV draft with selected evidence IDs
  uv run mocnghe cv create --profile-version 1.0 --language en --job-id <job_id> \
    --identity full_name --identity email --identity linkedin \
    --evidence ev_edu --evidence ev_exp_web --evidence ev_skills_db

  # 2. Review generated content and extract approval hash
  uv run mocnghe cv review <cv_id>

  # 3. Approve exact content and export PDF
  uv run mocnghe cv approve <cv_id> --hash <content_hash>
  uv run mocnghe cv export <cv_id> --output cv_output.pdf --max-pages 2
  ```

### Step 4: Application Draft & Form Mapping
Maps ATS application questions (Greenhouse, Lever, Indeed) to approved CV citations:

- **CLI:**
  ```bash
  uv run mocnghe draft create <cv_id> --job-id <job_id> \
    --subject "Application for Software Engineer" \
    --route "https://job-boards.eu.greenhouse.io/..." \
    --questions questions.json

  uv run mocnghe draft review <draft_id>
  uv run mocnghe draft approve <draft_id> --hash <content_hash>
  uv run mocnghe draft export <draft_id> --output application_bundle/
  ```

### Step 5: Application Lifecycle Tracking
Enforces strict linear state machine transitions:
`discovered` ➔ `shortlisted` ➔ `drafting` ➔ `ready` ➔ `applied` ➔ `interviewing` ➔ `offer`/`rejected`.

- **Slash command:** `/track <job_id> <state>`
- **CLI:**
  ```bash
  # Mark application as ready for manual submission
  uv run mocnghe track <job_id> --state ready --cv <cv_id>

  # Record confirmation once user submits manually:
  uv run mocnghe apply <job_id> --cv <cv_id> --confirm
  ```

---

## 4. Directory Layout

```
mocnghe/
├── src/mocnghe/
│   ├── ingestion/             # Job extraction & parsing
│   │   ├── adapters/          # Modular site-specific handlers
│   │   │   ├── base.py        # BaseJobAdapter (standard interface)
│   │   │   ├── greenhouse.py  # Greenhouse ATS adapter
│   │   │   ├── itviec.py      # ITviec adapter
│   │   │   ├── indeed.py      # Indeed adapter (JSON-LD / state parser)
│   │   │   ├── generic.py     # Generic HTML fallback
│   │   │   ├── browser.py     # Playwright headless runner
│   │   │   └── registry.py    # Auto-routing URL registry
│   │   ├── manual.py          # Legacy file/stdin parser
│   │   └── results.py         # Ingestion status schemas
│   ├── models/                # Pydantic data contracts
│   │   ├── job.py             # Job, Salary, Provenance models
│   │   ├── profile.py         # CandidateProfile, Evidence, Facts
│   │   └── cv.py              # Claim, CV Revision, Validation
│   ├── storage/
│   │   └── repository.py      # SQLite repository + hash audit
│   ├── cv_render.py           # ReportLab A4 PDF renderer
│   ├── evaluation_runtime.py  # Structured requirement extraction & triage
│   └── cli.py                 # Typer CLI entrypoints
│
├── .agents/skills/mocnghe/    # AI agent skill definition (OpenCode, Claude Code)
├── .cursor/rules/             # Cursor IDE rules
├── tests/                     # 134+ automated unit & integration tests
└── pyproject.toml             # Packaging & dependencies (uv)
```

---

## 5. Integrating with Other AI Agents

To equip another autonomous agent (such as Claude Code, OpenCode, or Codex) with Mốc Nghề:

1. **Provide Context:**
   - Link the agent to `.agents/skills/mocnghe/SKILL.md` or `.cursor/rules/mocnghe.md`.
2. **Execution Permissions:**
   - Grant terminal execution access (`uv run mocnghe ...`). All CLI outputs return structured text or JSON.
3. **Headless Browser Crawler:**
   - To enable dynamic crawling capabilities:
     ```bash
     uv pip install -e ".[browser]"
     uv run playwright install chromium
     ```
