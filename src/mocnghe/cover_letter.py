"""Evidence-grounded cover letter generator, review gate, and multi-format renderer."""
import io
from datetime import UTC, datetime
from html import escape
from importlib.resources import files
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .cv import digest
from .cv_render import publish_bundle


class CoverLetter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    cv_id: str
    cv_hash: str
    job_id: str
    job_hash: str
    language: Literal["en", "vi"]
    recipient: str = Field(min_length=1, max_length=200)
    company: str = Field(min_length=1, max_length=200)
    role_title: str = Field(min_length=1, max_length=200)
    date_str: str
    salutation: str
    opening: str = Field(min_length=1, max_length=4000)
    body_paragraphs: list[str] = Field(min_length=1, max_length=10)
    closing: str = Field(min_length=1, max_length=4000)
    signoff: str
    sender_name: str
    sender_contact: str
    evidence_ids: list[str] = Field(default_factory=list)


def render_cover_letter_pdf(cl: CoverLetter, max_pages: int = 1) -> bytes:
    """Render cover letter into professional single-page PDF with ReportLab."""
    font = "MocNgheNotoSans"
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font, str(files("mocnghe.assets").joinpath(
            "fonts/NotoSans-Regular.ttf"))))
    body = ParagraphStyle("cl_body", fontName=font, fontSize=10.5, leading=16, spaceAfter=10)
    header = ParagraphStyle("cl_header", parent=body, fontSize=11, leading=15, spaceAfter=4)
    sender = ParagraphStyle("cl_sender", parent=body, fontSize=16, leading=22, spaceAfter=4)
    salutation = ParagraphStyle("cl_salut", parent=body, fontSize=11, leading=16, spaceBefore=8, spaceAfter=8)

    def p(text: str, style=body):
        return Paragraph(escape(text).replace("\n", "<br/>"), style)

    story: list[Any] = [
        p(cl.sender_name, sender),
    ]
    if cl.sender_contact:
        story.append(p(cl.sender_contact, header))
    story.append(Spacer(1, 10))
    story.append(p(cl.date_str, header))
    story.append(Spacer(1, 6))
    story.append(p(f"<b>{cl.recipient}</b><br/>{cl.company}", header))
    story.append(Spacer(1, 10))
    story.append(p(cl.salutation, salutation))
    story.append(p(cl.opening))
    for para in cl.body_paragraphs:
        story.append(p(para))
    story.append(p(cl.closing))
    story.append(Spacer(1, 10))
    story.append(p(cl.signoff))
    story.append(Spacer(1, 16))
    story.append(p(cl.sender_name, header))

    buf = io.BytesIO()

    def check_page(canvas, document):
        if document.page > max_pages:
            raise ValueError(f"Cover letter exceeds {max_pages} page budget")

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
        title=f"Cover Letter - {cl.sender_name} - {cl.role_title}",
    )
    doc.build(story, onFirstPage=check_page, onLaterPages=check_page)
    return buf.getvalue()


class CoverLetterService:
    content_hash = staticmethod(digest)

    def __init__(self, cv_service):
        self.cvs = cv_service
        self.repo = cv_service.repo
        with self.repo.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS cover_letters "
                "(id TEXT PRIMARY KEY, payload TEXT NOT NULL, hash TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS cover_letter_approvals "
                "(id TEXT PRIMARY KEY REFERENCES cover_letters(id), hash TEXT NOT NULL)"
            )

    def create(
        self,
        cv_id: str,
        job_id: str,
        *,
        recipient: str | None = None,
        custom_opening: str | None = None,
        custom_closing: str | None = None,
    ) -> CoverLetter:
        cv = self.cvs.get(cv_id)
        if not self.cvs.approved(cv_id):
            raise PermissionError("approved CV required before creating cover letter")
        job = self.repo.get_job(job_id)
        if job is None:
            raise ValueError("job not found")

        company = getattr(job, "employer", None) or ("Công ty" if cv.language == "vi" else "Company")
        role_title = getattr(job, "title", None) or ("Vị trí ứng tuyển" if cv.language == "vi" else "Target Role")
        recipient = recipient or ("Hội đồng tuyển dụng" if cv.language == "vi" else "Hiring Team")

        sender_name = cv.identity.get("name", cv.identity.get("full_name", "Ứng viên"))
        contacts = [v for k, v in cv.identity.items() if k not in {"name", "full_name"}]
        sender_contact = " | ".join(contacts)

        now_str = datetime.now(UTC).strftime("%d/%m/%Y" if cv.language == "vi" else "%B %d, %Y")

        if cv.language == "vi":
            salutation = f"Kính gửi {recipient} tại {company},"
            opening = custom_opening or (
                f"Tôi viết thư này để bày tỏ nguyện vọng ứng tuyển vào vị trí {role_title} tại {company}. "
                "Với những kinh nghiệm và kỹ năng đã tích lũy, tôi tin rằng mình có thể đóng góp hiệu quả vào mục tiêu chung của quý công ty."
            )
            # Body paragraphs grounded in approved claims
            body_paras = [c.text for c in cv.claims if c.section in {"experience", "skills", "other"}]
            if not body_paras:
                body_paras = [c.text for c in cv.claims]
            closing = custom_closing or (
                "Rất mong có cơ hội trao đổi trực tiếp với quý công ty trong buổi phỏng vấn để làm rõ hơn về sự phù hợp của tôi đối với vị trí này. "
                "Cảm ơn quý công ty đã dành thời gian xem xét hồ sơ."
            )
            signoff = "Trân trọng,"
        else:
            salutation = f"Dear {recipient} at {company},"
            opening = custom_opening or (
                f"I am writing to express my strong interest in the {role_title} position at {company}. "
                "Based on my verified qualifications and practical background, I am confident in my ability to contribute meaningfully to your team."
            )
            body_paras = [c.text for c in cv.claims if c.section in {"experience", "skills", "other"}]
            if not body_paras:
                body_paras = [c.text for c in cv.claims]
            closing = custom_closing or (
                "I would welcome the opportunity to discuss how my background and skills align with your needs. "
                "Thank you for your time and consideration."
            )
            signoff = "Sincerely,"

        target_job_id = getattr(job, "job_id", job_id)
        letter = CoverLetter(
            id=uuid4().hex,
            cv_id=cv.id,
            cv_hash=digest(cv),
            job_id=target_job_id,
            job_hash=digest(job),
            language=cv.language,
            recipient=recipient,
            company=company,
            role_title=role_title,
            date_str=now_str,
            salutation=salutation,
            opening=opening,
            body_paragraphs=body_paras,
            closing=closing,
            signoff=signoff,
            sender_name=sender_name,
            sender_contact=sender_contact,
            evidence_ids=[c.evidence_id for c in cv.claims],
        )

        with self.repo.connect() as db:
            db.execute(
                "INSERT INTO cover_letters VALUES (?, ?, ?)",
                (letter.id, letter.model_dump_json(), digest(letter)),
            )
        return letter

    def get(self, cl_id: str) -> CoverLetter:
        with self.repo.connect() as db:
            row = db.execute("SELECT payload, hash FROM cover_letters WHERE id=?", (cl_id,)).fetchone()
        if row is None:
            raise ValueError("cover letter not found")
        letter = CoverLetter.model_validate_json(row["payload"])
        if digest(letter) != row["hash"]:
            raise ValueError("cover letter storage hash mismatch")
        return letter

    def approved(self, cl_id: str) -> bool:
        letter = self.get(cl_id)
        with self.repo.connect() as db:
            row = db.execute("SELECT hash FROM cover_letter_approvals WHERE id=?", (cl_id,)).fetchone()
        return row is not None and row["hash"] == digest(letter)

    def approve(self, cl_id: str, content_hash: str) -> None:
        letter = self.get(cl_id)
        if content_hash != digest(letter):
            raise ValueError("content hash mismatch; review exact content before approving")
        with self.repo.connect() as db:
            db.execute("INSERT OR REPLACE INTO cover_letter_approvals VALUES (?, ?)", (cl_id, content_hash))

    def export(self, cl_id: str, target_dir: Path, *, max_pages: int = 1) -> None:
        letter = self.get(cl_id)
        if not self.approved(cl_id):
            raise PermissionError("cover letter must be approved before export")

        md_content = (
            f"# Cover Letter - {letter.sender_name}\n\n"
            f"**To:** {letter.recipient}, {letter.company}\n"
            f"**Date:** {letter.date_str}\n\n"
            f"{letter.salutation}\n\n"
            f"{letter.opening}\n\n"
            + "\n\n".join(letter.body_paragraphs)
            + f"\n\n{letter.closing}\n\n"
            f"{letter.signoff}\n\n"
            f"{letter.sender_name}\n"
        )

        pdf_bytes = render_cover_letter_pdf(letter, max_pages=max_pages)

        publish_bundle(
            Path(target_dir),
            {
                "cover_letter.md": md_content.encode("utf-8"),
                "cover_letter.txt": md_content.encode("utf-8"),
                "cover_letter.pdf": pdf_bytes,
                "cover_letter.json": letter.model_dump_json(indent=2).encode("utf-8"),
            },
        )
