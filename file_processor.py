"""
File text extraction for SkillMatch AI.

Supported inputs:
- PDF (embedded text, with OCR fallback for pages without extractable text)
- PNG / JPG / JPEG images (Tesseract OCR)
- TXT files

System requirements for OCR:
- Tesseract OCR must be installed and available on PATH.
- PDF OCR additionally requires Poppler, which pdf2image uses.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

logger = logging.getLogger(__name__)

# Avoid unexpectedly large processing jobs. Adjust these for your deployment.
MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_PDF_PAGES = 40
OCR_DPI = 250


def _get_file_bytes(uploaded_file) -> bytes:
    """Read an uploaded file without depending on its current stream position."""
    try:
        if hasattr(uploaded_file, "getvalue"):
            data = uploaded_file.getvalue()
        else:
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
            data = uploaded_file.read()
    except Exception as exc:
        raise ValueError(f"Could not read the uploaded file: {exc}") from exc

    if not data:
        raise ValueError("The uploaded file is empty.")

    if len(data) > MAX_FILE_BYTES:
        raise ValueError(
            f"The file is larger than the {MAX_FILE_BYTES // (1024 * 1024)} MB limit."
        )
    return data


def _detect_file_type(uploaded_file) -> str:
    """Use MIME type where available, then fall back to the filename extension."""
    mime = (getattr(uploaded_file, "type", None) or "").lower().strip()
    if mime in {"application/pdf", "image/jpeg", "image/png", "text/plain"}:
        return mime

    name = getattr(uploaded_file, "name", "") or ""
    suffix = Path(name).suffix.lower()

    extension_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".txt": "text/plain",
    }
    return extension_types.get(suffix, mime)


def _ocr_image(image: Image.Image) -> str:
    """Run Tesseract OCR with a clear diagnostic if the system binary is missing."""
    try:
        # Tesseract generally performs better with RGB or grayscale input.
        prepared = image.convert("RGB")
        return pytesseract.image_to_string(prepared, config="--oem 3 --psm 6").strip()
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR is not installed or is not available on PATH. "
            "Install Tesseract on this computer/server, then restart Streamlit."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Image OCR failed: {type(exc).__name__}: {exc}") from exc


def _extract_image(data: bytes) -> str:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            text = _ocr_image(image)
    except UnidentifiedImageError as exc:
        raise ValueError("The uploaded image could not be opened. Check that it is a valid PNG or JPEG.") from exc

    if not text.strip():
        raise ValueError(
            "No readable text was detected in the image. Try a clearer, higher-resolution image."
        )
    return text


def _ocr_pdf_page(data: bytes, page_number: int) -> str:
    """OCR a single 1-based PDF page using pdf2image and Poppler."""
    try:
        from pdf2image import convert_from_bytes
    except ImportError as exc:
        raise RuntimeError(
            "PDF OCR requires pdf2image. Install it with: pip install pdf2image"
        ) from exc

    try:
        images = convert_from_bytes(
            data,
            dpi=OCR_DPI,
            first_page=page_number,
            last_page=page_number,
            fmt="png",
        )
        if not images:
            return ""
        return _ocr_image(images[0])
    except pytesseract.TesseractNotFoundError:
        raise
    except Exception as exc:
        message = str(exc)
        if "poppler" in message.lower() or "page count" in message.lower():
            raise RuntimeError(
                "Could not convert this PDF for OCR. Install Poppler and make sure "
                "its binaries are available on PATH. On Windows, you may need to "
                "set the poppler_path argument in convert_from_bytes."
            ) from exc
        raise RuntimeError(
            f"OCR failed on PDF page {page_number}: {type(exc).__name__}: {exc}"
        ) from exc


def _extract_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
    except Exception as exc:
        raise ValueError(f"Could not open this PDF: {type(exc).__name__}: {exc}") from exc

    if reader.is_encrypted:
        try:
            decrypt_result = reader.decrypt("")
            if decrypt_result == 0:
                raise ValueError("This PDF is password-protected. Upload an unlocked copy.")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("This PDF is encrypted and could not be opened.") from exc

    page_count = len(reader.pages)
    if page_count == 0:
        raise ValueError("The PDF contains no pages.")
    if page_count > MAX_PDF_PAGES:
        raise ValueError(
            f"This PDF has {page_count} pages. The current limit is {MAX_PDF_PAGES} pages."
        )

    extracted_pages = []
    ocr_pages = []

    for index, page in enumerate(reader.pages, start=1):
        try:
            page_text = (page.extract_text() or "").strip()
        except Exception as exc:
            logger.warning("Text extraction failed on PDF page %s: %s", index, exc)
            page_text = ""

        if page_text:
            extracted_pages.append(f"[Page {index}]\n{page_text}")
        else:
            # OCR only pages with no embedded text, rather than OCRing the whole PDF.
            ocr_pages.append(index)
            extracted_pages.append(None)

    for page_number in ocr_pages:
        logger.info("Running OCR on scanned PDF page %s", page_number)
        ocr_text = _ocr_pdf_page(data, page_number)
        extracted_pages[page_number - 1] = (
            f"[Page {page_number} - OCR]\n{ocr_text}" if ocr_text else ""
        )

    combined = "\n\n".join(part for part in extracted_pages if part)
    if not combined.strip():
        raise ValueError(
            "No readable text was found in this PDF. It may be blank, image-only "
            "with poor scan quality, or protected. Check that Tesseract and Poppler are installed."
        )
    return combined


def _extract_txt(data: bytes) -> str:
    """Decode text with common encodings used by uploaded text files."""
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = data.decode(encoding).strip()
            if text:
                return text
        except UnicodeDecodeError:
            continue

    raise ValueError("The TXT file could not be decoded or contains no readable text.")


def extract_text_from_file(uploaded_file) -> str:
    """
    Extract text from a Streamlit UploadedFile or compatible file object.

    Returns extracted text. Raises ValueError for invalid/unsupported files and
    RuntimeError for missing OCR system dependencies or processing failures.
    """
    if uploaded_file is None:
        return ""

    data = _get_file_bytes(uploaded_file)
    file_type = _detect_file_type(uploaded_file)

    if file_type == "application/pdf":
        return _extract_pdf(data)

    if file_type in {"image/jpeg", "image/png"}:
        return _extract_image(data)

    if file_type == "text/plain":
        return _extract_txt(data)

    filename = getattr(uploaded_file, "name", "uploaded file")
    raise ValueError(
        f"Unsupported file format for '{filename}'. Supported formats are PDF, PNG, JPG, JPEG, and TXT."
    )
