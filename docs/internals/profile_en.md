# Profile & Evidence Subsystem

The `profile` subsystem manages candidate ground-truth information. Its foundational principle is **strict factual grounding**: every claim, skill, or achievement must be anchored in verified evidence (`CandidateEvidence`), prohibiting ungrounded synthesis or hallucinated qualifications.

---

## 1. Core Data Models (`models/profile.py`)

### 1.1. Atomic Evidence (`CandidateEvidence`)
The minimal factual unit representing candidate capabilities:
```python
class CandidateEvidence(BaseModel):
    evidence_id: str          # Unique ID (e.g., "ev_exp_steam_camera")
    status: EvidenceStatus    # candidate_confirmed | document_verified | public_verified
    summary: str              # Overview of achievement or qualification
    source: str               # Document or system source (e.g., "cv.pdf", "github_pr")
    source_quote: str | None  # Verbatim quotation (required for CV tailoring)
    provenance: str | None    # Category tag: experience, education, identity...
    uncertainty: Literal["low", "medium", "high", "unknown"]
```

### 1.2. Fact Requirements (`FactRequirement`)
Binds key assertions directly to supporting evidence citations:
```python
class FactRequirement(BaseModel):
    fact_id: str              # Assertion identifier (e.g., "fact_cs_student")
    label: str                # Assertion description (e.g., "Enrolled CS Student")
    evidence_ids: list[str]   # Must cite at least one valid evidence_id
```
> **Validation Rule:** The `CandidateProfile` schema performs model-level validation: any fact citing a missing or unlisted `evidence_id` triggers a rejection with `missing evidence ids`.

---

## 2. Profile Lifecycle

```
        [ Draft Onboarding ] (profile_drafts table)
                     |
                     |  - OnboardingSession.answer()
                     |  - OnboardingSession.correct()
                     v
        [ Schema Validation ] (mocnghe profile validation)
                     |
                     |  - Verifies completeness & citations
                     |  - Ensures Pydantic contract compliance
                     v
        [ Confirmation ] (mocnghe profile confirm / confirm-file)
                     |
                     |  - Stamps confirmed_at in UTC
                     |  - Computes profile_content_hash = SHA-256(payload)
                     v
        [ Immutable Record ] (stored in profiles table)
```

### Immutability Guarantees
Once confirmed under a given version tag (e.g. `version: "1.0"`):
- The complete JSON document is persisted to the `profiles` table.
- Confirmed profile versions are strictly immutable. Any subsequent updates require incrementing the version string (e.g. `"1.1"` or `"2.0"`).
- Guarantees historical reproducibility for previously tailored CVs and application audits.
