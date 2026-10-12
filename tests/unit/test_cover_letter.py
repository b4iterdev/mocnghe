import pytest
from pypdf import PdfReader

from mocnghe.cover_letter import CoverLetterService
from mocnghe.cv import CVService
from mocnghe.ingestion.manual import import_jd_text_with_status


def test_cover_letter_workflow(repo, tmp_path):
    job, _ = import_jd_text_with_status(
        repo,
        "Tiêu đề: Senior Python Developer\nCông ty: VinTech\nYêu cầu: Python",
        source_identity="synthetic",
    )

    cv_service = CVService(repo)
    cv = cv_service.create("v1", ["ev1"], language="vi", identity_keys=["name", "email"])
    cl_service = CoverLetterService(cv_service)

    assert job.job_id is not None
    # Cannot create without approved CV
    with pytest.raises(PermissionError, match="approved CV"):
        cl_service.create(cv.id, job.job_id)

    cv_service.approve(cv.id, cv_service.content_hash(cv))

    # Create cover letter
    cl = cl_service.create(cv.id, job.job_id, recipient="Trưởng phòng Kỹ thuật")
    assert cl.company == "VinTech"
    assert cl.role_title == "Senior Python Developer"
    assert "Trưởng phòng Kỹ thuật" in cl.recipient
    assert "Tình nguyện hỗ trợ khách hàng." in cl.body_paragraphs[0]
    assert not cl_service.approved(cl.id)

    # Cannot export without approval
    target = tmp_path / "cl_out"
    with pytest.raises(PermissionError, match="must be approved"):
        cl_service.export(cl.id, target)

    # Wrong hash fails
    with pytest.raises(ValueError, match="hash mismatch"):
        cl_service.approve(cl.id, "0" * 64)

    # Valid approval and export
    cl_service.approve(cl.id, cl_service.content_hash(cl))
    assert cl_service.approved(cl.id)

    cl_service.export(cl.id, target)
    assert (target / "cover_letter.md").exists()
    assert (target / "cover_letter.txt").exists()
    assert (target / "cover_letter.pdf").exists()
    assert (target / "cover_letter.json").exists()

    reader = PdfReader(target / "cover_letter.pdf")
    assert len(reader.pages) == 1
    pdf_text = reader.pages[0].extract_text()
    assert "VinTech" in pdf_text
    assert "Senior Python Developer" in pdf_text


def test_cover_letter_english_and_custom_text(repo, tmp_path):
    job, _ = import_jd_text_with_status(
        repo,
        "Tiêu đề: DevOps Engineer\nCông ty: GlobalTech\nYêu cầu: Linux",
        source_identity="synthetic",
    )

    cv_service = CVService(repo)
    cv = cv_service.create("v1", ["ev1"], language="en")
    cv_service.approve(cv.id, cv_service.content_hash(cv))

    assert job.job_id is not None
    cl_service = CoverLetterService(cv_service)
    cl = cl_service.create(
        cv.id,
        job.job_id,
        recipient="Engineering Manager",
        custom_opening="Custom opening line for DevOps.",
        custom_closing="Custom closing line.",
    )
    assert cl.language == "en"
    assert "Custom opening line" in cl.opening
    assert "Custom closing line" in cl.closing
    assert cl.salutation == "Dear Engineering Manager at GlobalTech,"


def test_tampered_cover_letter_rejected(repo):
    job, _ = import_jd_text_with_status(
        repo,
        "Tiêu đề: Test Role\nCông ty: Co\nYêu cầu: Python",
        source_identity="synthetic",
    )
    cv_service = CVService(repo)
    cv = cv_service.create("v1", ["ev1"], language="vi")
    cv_service.approve(cv.id, cv_service.content_hash(cv))

    assert job.job_id is not None
    cl_service = CoverLetterService(cv_service)
    cl = cl_service.create(cv.id, job.job_id)

    with repo.connect() as db:
        db.execute("UPDATE cover_letters SET hash = ? WHERE id = ?", ("0" * 64, cl.id))

    with pytest.raises(ValueError, match="hash mismatch"):
        cl_service.get(cl.id)
