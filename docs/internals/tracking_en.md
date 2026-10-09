# Application Tracking Subsystem

The `applications` subsystem manages job application states and persists immutable submission audit snapshots under strict human-in-the-loop control.

---

## 1. Linear State Machine

State transitions follow a strict unidirectional state machine:

```
[ discovered ] (Job discovered or crawled)
      |
      v
[ shortlisted ] (Candidate selected for targeting)
      |
      v
[ drafting ] (CV tailoring & cover letter generation)
      |
      v
[ ready ] (Approved CV attached, bundle complete)
      |
      +---> [ applied ] (Candidate manually submitted)
      |         |
      |         +---> [ interviewing ] (Interview pipeline active)
      |         |         |
      |         |         +---> [ offer ] (Job offer extended)
      |         |         +---> [ rejected ] (Application rejected)
      |         |
      |         +---> [ withdrawn ] (Candidate withdrew)
      |
      +---> [ archived ] (Closed / Archived)
```

---

## 2. Immutable Submission Snapshots

Transitioning an application to `ready` captures an immutable audit payload (`submission_json`):
- The exact approved CV revision and its content hash.
- The base candidate profile version.
- The parsed job description and its canonical hash.

The complete payload is cryptographically sealed with `submission_hash`. This preserves a forensically verifiable record of the exact application materials prepared for the employer, immune to subsequent profile edits or web JD deletions.

---

## 3. Human-in-the-Loop Confirmation (`apply`)

The `track` command is explicitly prohibited from transitioning directly to `applied`.

Recording an application requires the dedicated `apply` command:
```bash
uv run mocnghe apply <job_id> --cv <cv_id> --confirm
```
- **Zero Autonomous Dispatch:** This command does not send emails or submit web forms.
- **Audited Confirmation:** It acts as an audited user affirmation: *"I confirm that I have manually submitted this tailored package to the employer."*
- Protects job seekers against unintended or unchecked bulk applications by autonomous agents.
