from pathlib import Path

from .models.profile import CandidateProfile


def generate_brief(profile: CandidateProfile) -> str:
    lines = [
        f"# First-Pass Triage Brief: {profile.profile_id} ({profile.version})",
        "",
        "Use this brief for fast, deterministic first-pass screening of scraped or incoming job descriptions.",
        "",
        "## 1. Target Role Families (Ranked)",
    ]

    if profile.ranked_targets:
        for t in profile.ranked_targets:
            lines.append(f"- **Rank {t.rank}**: {t.title} (`{t.occupation_family}`)")
    else:
        lines.append("- *(No target roles specified)*")
    lines.append("")

    lines.append("## 2. Hard Compensation Floors")
    prefs = profile.preferences
    if prefs.internship_compensation_floor and prefs.internship_compensation_floor.amount is not None:
        amt = f"{prefs.internship_compensation_floor.amount:,}"
        curr = prefs.internship_compensation_floor.currency or ""
        per = prefs.internship_compensation_floor.period or ""
        gn = prefs.internship_compensation_floor.gross_net
        lines.append(f"- **Internship Floor**: {amt} {curr} / {per} ({gn})")
    else:
        lines.append("- **Internship Floor**: Negotiable / Not specified")

    if prefs.full_time_compensation_floor and prefs.full_time_compensation_floor.amount is not None:
        amt = f"{prefs.full_time_compensation_floor.amount:,}"
        curr = prefs.full_time_compensation_floor.currency or ""
        per = prefs.full_time_compensation_floor.period or ""
        gn = prefs.full_time_compensation_floor.gross_net
        lines.append(f"- **Full-Time Floor**: {amt} {curr} / {per} ({gn})")
    else:
        lines.append("- **Full-Time Floor**: Negotiable / Not specified")
    lines.append("")

    lines.append("## 3. Location & Workplace Policy")
    locs = ", ".join(prefs.preferred_locations) if prefs.preferred_locations else "Flexible / Any"
    lines.append(f"- **Preferred Locations**: {locs}")
    lines.append(f"- **Remote From Vietnam**: {'Allowed' if prefs.remote_from_vietnam else 'On-site preferred'}")
    if prefs.weekly_availability_hours is not None:
        lines.append(f"- **Weekly Hours**: Max {prefs.weekly_availability_hours}h/week")
    lines.append("")

    lines.append("## 4. Industry Exclusions & Hard Red Flags")
    if prefs.industry_exclusions:
        lines.append("- **Excluded Industries**:")
        for exc in prefs.industry_exclusions:
            lines.append(f"  • {exc}")
    else:
        lines.append("- *(No industry exclusions defined)*")
    lines.append("")

    lines.append("## 5. Quick Decision Heuristics")
    lines.append("- **PASS (Evaluate)**: Role matches ranked target, salary meets/exceeds floor, location matches, zero red flags.")
    lines.append("- **HOLD (Unknowns)**: Salary undisclosed/negotiable or location requires confirmation.")
    lines.append("- **REJECT**: Excluded industry, hard location mismatch, or salary explicitly below floor.")
    lines.append("")

    return "\n".join(lines)


def generate_framing(profile: CandidateProfile) -> str:
    lines = [
        f"# Role Framing & Proof Mapping: {profile.profile_id} ({profile.version})",
        "",
        "This document guides AI agents and tailoring workflows on positioning the candidate truthfully without hallucination or overclaiming.",
        "",
        "## 1. Candidate Positioning & Core Narrative",
    ]
    name = profile.identity.get("name", "The candidate")
    lines.append(f"- **Identity**: {name}")
    if profile.skills:
        lines.append(f"- **Primary Stacks**: {', '.join(profile.skills)}")
    lines.append("")

    lines.append("## 2. Evidence & Proof Point Mapping")
    for t in profile.ranked_targets:
        lines.append(f"### Target Role: {t.title} ({t.occupation_family})")
        matching_evidence = [
            ev for ev in profile.evidence
            if ev.evidence_id in t.evidence_ids or (t.title.lower() in ev.summary.lower())
        ]
        if not matching_evidence:
            matching_evidence = profile.evidence[:3]  # Fallback to top evidence
        for ev in matching_evidence:
            quote_text = f' > "{ev.source_quote}"' if ev.source_quote else ""
            lines.append(f"- **`{ev.evidence_id}`** [{ev.status.value if hasattr(ev.status, 'value') else ev.status}]: {ev.summary}")
            if quote_text:
                lines.append(f"  {quote_text}")
        lines.append("")

    lines.append("## 3. Factual Caveats & Guardrails")
    lines.append("- **Zero-Hallucination Invariant**: Never invent metrics, team size, revenue, or customer counts not grounded in verified quotes.")
    lines.append("- **Volunteer is Volunteer**: Volunteer experience must be clearly framed as volunteer or open-source contribution, never inflated into senior enterprise employment.")
    lines.append("- **Scope Precision**: Retain metric qualifiers like 'approximately', 'team of', 'as low as' exactly where evidence requires them.")
    lines.append("- **Missing Skills**: Flag genuine missing requirements as skill gaps; never claim a technology merely to boost ATS keyword score.")
    lines.append("")

    lines.append("## 4. Logistics & Availability Boundaries")
    prefs = profile.preferences
    lines.append(f"- **Current Availability**: {prefs.availability_current or 'Immediate'}")
    lines.append(f"- **Future Availability**: {prefs.availability_future or 'Full-time upon graduation'}")
    lines.append(f"- **Travel Policy**: {prefs.travel or 'No regular travel'}")
    lines.append("")

    return "\n".join(lines)


def export_framing_bundle(profile: CandidateProfile, target_dir: Path) -> dict[str, Path]:
    modes_dir = target_dir / "modes"
    modes_dir.mkdir(parents=True, exist_ok=True)

    brief_path = modes_dir / "_brief.md"
    profile_path = modes_dir / "_profile.md"

    brief_text = generate_brief(profile)
    framing_text = generate_framing(profile)

    brief_path.write_text(brief_text, encoding="utf-8")
    profile_path.write_text(framing_text, encoding="utf-8")

    # Also symlink or mirror to workspace root for convenience
    root_brief = target_dir / "_brief.md"
    root_profile = target_dir / "_profile.md"
    root_brief.write_text(brief_text, encoding="utf-8")
    root_profile.write_text(framing_text, encoding="utf-8")

    return {
        "brief": brief_path,
        "profile": profile_path,
    }
