import re
from typing import Literal

from pydantic import BaseModel, Field

from .evaluation_runtime import _requirements_from_job
from .models.job import Job
from .models.profile import CandidateProfile


class RequirementMatch(BaseModel):
    requirement_id: str
    requirement_text: str
    status: Literal["matched", "potential", "gap"]
    matching_skills: list[str] = Field(default_factory=list)
    matching_evidence_ids: list[str] = Field(default_factory=list)
    notes: str | None = None


class SkillGapReport(BaseModel):
    job_id: str
    profile_version: str
    total_requirements: int
    match_score_pct: float
    matched: list[RequirementMatch] = Field(default_factory=list)
    potential: list[RequirementMatch] = Field(default_factory=list)
    gaps: list[RequirementMatch] = Field(default_factory=list)


def _normalize(text: str) -> str:
    return re.sub(r"[^\w\s\+#/]", " ", text.lower()).strip()


def _contains_keyword(text: str, keyword: str) -> bool:
    norm_text = f" {_normalize(text)} "
    norm_kw = _normalize(keyword)
    if not norm_kw:
        return False
    pattern = rf"(?:\b|\s){re.escape(norm_kw)}(?:\b|\s)"
    return bool(re.search(pattern, norm_text))


def analyze_skill_gap(profile: CandidateProfile, job: Job) -> SkillGapReport:
    packet_reqs = _requirements_from_job(job)
    total_count = len(packet_reqs)

    matched: list[RequirementMatch] = []
    potential: list[RequirementMatch] = []
    gaps: list[RequirementMatch] = []

    all_candidate_skills = profile.skills + profile.languages
    evidence_list = profile.evidence

    for req in packet_reqs:
        req_text = req.text
        req_skills: list[str] = []
        req_ev_ids: list[str] = []

        # 1. Direct Skill Matching
        for skill in all_candidate_skills:
            if (_contains_keyword(req_text, skill) or _contains_keyword(skill, req_text)) and skill not in req_skills:
                req_skills.append(skill)

        # 2. Evidence Grounding Matching
        for ev in evidence_list:
            ev_corpus = f"{ev.summary} {ev.source_quote or ''}"
            # Check if requirement matches evidence tokens or vice-versa
            matched_via_skills = any(_contains_keyword(ev_corpus, s) for s in req_skills) if req_skills else False
            if matched_via_skills and ev.evidence_id not in req_ev_ids:
                req_ev_ids.append(ev.evidence_id)
            elif not matched_via_skills:
                # Direct check if words from requirement match evidence
                words = [w for w in _normalize(req_text).split() if len(w) >= 3 and w not in {"and", "the", "for", "with", "years", "experience"}]
                matching_words = [w for w in words if _contains_keyword(ev_corpus, w)]
                if (len(matching_words) >= 2 or (len(words) == 1 and len(matching_words) == 1)) and ev.evidence_id not in req_ev_ids:
                    req_ev_ids.append(ev.evidence_id)

        if req_skills or req_ev_ids:
            if req_skills:
                matched.append(
                    RequirementMatch(
                        requirement_id=req.requirement_id,
                        requirement_text=req_text,
                        status="matched",
                        matching_skills=req_skills,
                        matching_evidence_ids=req_ev_ids,
                        notes=f"Supported by skills: {', '.join(req_skills)}",
                    )
                )
            else:
                potential.append(
                    RequirementMatch(
                        requirement_id=req.requirement_id,
                        requirement_text=req_text,
                        status="potential",
                        matching_skills=[],
                        matching_evidence_ids=req_ev_ids,
                        notes="Partial evidence grounding without explicit skills badge.",
                    )
                )
        else:
            gaps.append(
                RequirementMatch(
                    requirement_id=req.requirement_id,
                    requirement_text=req_text,
                    status="gap",
                    matching_skills=[],
                    matching_evidence_ids=[],
                    notes="No verified candidate skill or evidence cited.",
                )
            )

    score = round((len(matched) / total_count * 100), 1) if total_count > 0 else 0.0

    return SkillGapReport(
        job_id=str(job.job_id or "unknown"),
        profile_version=profile.version,
        total_requirements=total_count,
        match_score_pct=score,
        matched=matched,
        potential=potential,
        gaps=gaps,
    )
