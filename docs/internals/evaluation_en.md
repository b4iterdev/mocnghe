# Triage & Evaluation Subsystem

The `evaluation` subsystem evaluates the degree of alignment between employer requirements and candidate evidence. It consists of two layers: **deterministic local triage** and an **audited AI Agent evaluation contract**.

---

## 1. Structured Requirement Extraction (`_requirements_from_job`)

Instead of passing unparsed, massive JDs to an LLM (which is cost-inefficient and vulnerable to prompt injection), Mốc Nghề uses a deterministic heading-and-bullet parser (`evaluation_runtime.py`):

1. **Heading Boundary Detection:**
   - **Required:** `required qualifications`, `must have`, `yêu cầu`, `kỹ năng yêu cầu`...
   - **Preferred:** `good to have`, `nice to have`, `preferred`, `ưu tiên`, `bonus`...
   - **Stop Markers:** `benefits`, `what we offer`, `phúc lợi`, `quyền lợi`...
2. **Bullet Isolation (`_is_bullet`):**
   - Automatically detects bullet characters: `-`, `•`, `*`, `·`, `▪`, `▸`.
   - Assigns sequential IDs: `req_001`, `req_002`, `req_003`...
   - Binds importance tags: `required_status: "required" | "preferred"`.

---

## 2. Deterministic Local Triage Engine (`triage.py`)

Provides immediate offline screening without requiring internet connectivity or API credentials:

```
[ Confirmed Profile ] + [ Stored Job ]
                   |
                   v
         triage_job(profile, job)
                   |
                   +---> Hard Constraint Checking:
                   |       - Compensation floor violations
                   |       - Industry exclusions
                   |       - Regulated mandatory licenses (e.g. Registered Nurse)
                   |
                   +---> Unknown Context Flags:
                   |       - Uncategorized employment type (intern vs full-time)
                   |       - Ambiguous workplace location
                   |
                   v
         Verdict:
           * practical_fit: No violations, constraints fully met
           * evaluate_with_unknowns: Viable, but contains unconfirmed attributes
           * not_fit: Hard constraint violation triggered
```

---

## 3. Audited AI Agent Protocol (`EvaluationPacket`)

When delegating evaluation to remote models or AI coding agents, Mốc Nghề enforces strict isolation:

### 3.1. Packet Export (`export-packet`)
- **PII Stripping:** Strips all candidate identity attributes (names, email, phone numbers) and any evidence flagged as `provenance == "identity"`.
- **Integrity Anchoring:** Encodes `profile_content_hash` and `jd_content_hash` to bind the packet immutably to exact local database states.

### 3.2. Response Verification (`import-report`)
Upon receiving candidate evaluations, `validate_evaluation_response` enforces strict verification:
1. **Exact ID Alignment:** Must score every `req_xxx` exactly once in its canonical sequence.
2. **Exact Quotation Matching:** Any assertion of `status: "supported"` must reproduce the exact `source_quote` stored in the evaluation packet.
3. **Lexical Overlap Gate (`_has_conservative_overlap`):** Enforces token overlap between the requirement text and the cited evidence quote, preventing arbitrary citation stuffing.
