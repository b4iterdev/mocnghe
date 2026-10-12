"""Visual regression testing and verification for rendered PDF documents."""
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None  # type: ignore


def pdf_to_images(pdf_bytes: bytes, dpi: int = 150) -> list[Image.Image]:
    """Render each page of a PDF bytes stream into a PIL RGB Image."""
    if pymupdf is None:
        raise RuntimeError("pymupdf is required for PDF visual verification")
    if not pdf_bytes:
        raise ValueError("pdf_bytes cannot be empty")
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    images: list[Image.Image] = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        images.append(img)
    return images


def compare_images(
    actual: Image.Image,
    expected: Image.Image,
    tolerance: float = 0.01,
) -> tuple[bool, float, Image.Image | None]:
    """
    Compare two PIL images.
    Returns: (passed: bool, diff_ratio: float, diff_image: Optional[Image])
    diff_ratio is ratio of mismatched pixels (0.0 means identical).
    """
    if actual.size != expected.size:
        # Resize difference is an immediate mismatch
        return False, 1.0, None

    # Compute difference
    diff = ImageChops.difference(actual, expected)
    # Convert diff to grayscale to count non-zero pixels
    diff_gray = diff.convert("L")
    histogram = diff_gray.histogram()
    # Non-zero pixels are at indices 1..255
    non_zero = sum(histogram[1:])
    total_pixels = actual.size[0] * actual.size[1]
    diff_ratio = non_zero / total_pixels if total_pixels > 0 else 0.0

    passed = diff_ratio <= tolerance
    return passed, diff_ratio, diff if not passed else None


def verify_pdf_visual(
    pdf_bytes: bytes,
    snapshot_path: Path,
    *,
    page_index: int = 0,
    dpi: int = 150,
    tolerance: float = 0.01,
    update: bool = False,
) -> dict[str, Any]:
    """
    Verify a PDF page visually against a baseline snapshot PNG.
    If update is True or baseline does not exist, writes current render as baseline.
    """
    snapshot_path = Path(snapshot_path)
    images = pdf_to_images(pdf_bytes, dpi=dpi)
    if not images:
        raise ValueError("PDF has no pages")
    if page_index < 0 or page_index >= len(images):
        raise ValueError(f"page_index {page_index} out of range (total pages: {len(images)})")

    current_image = images[page_index]

    if update or not snapshot_path.exists():
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        current_image.save(snapshot_path, "PNG")
        return {
            "status": "baseline_updated",
            "passed": True,
            "diff_ratio": 0.0,
            "snapshot_path": str(snapshot_path),
            "page_count": len(images),
        }

    expected_image = Image.open(snapshot_path).convert("RGB")
    passed, diff_ratio, _ = compare_images(current_image, expected_image, tolerance=tolerance)

    return {
        "status": "matched" if passed else "mismatched",
        "passed": passed,
        "diff_ratio": diff_ratio,
        "tolerance": tolerance,
        "snapshot_path": str(snapshot_path),
        "page_count": len(images),
    }
