"""
EXAMIX AI - OCR service using Google Cloud Vision API.

Supports JPG, JPEG, PNG, and PDF.

Two ways to authenticate are supported:
  1. GOOGLE_VISION_API_KEY - a plain Google API key (starts "AIza...").
     Calls the Vision REST API directly over HTTPS. Simplest option,
     no service-account setup needed. PDFs are sent to Vision's native
     files:annotate endpoint as base64 - NO poppler, NO pdf2image, NO
     local page rendering required (synchronous PDF OCR supports up to
     5 pages per request, which covers a typical question paper).
  2. GOOGLE_APPLICATION_CREDENTIALS - a *file path* to a service-account
     JSON key. Uses the official google-cloud-vision client library.
     PDFs in this mode ARE rasterized locally via pdf2image/poppler,
     since the client library path here uses per-page image annotation.

If GOOGLE_VISION_API_KEY is set, it takes priority (no poppler needed
at all). Either credential alone is enough.
"""

import os
import io
import base64
import requests


class OCRError(Exception):
    pass


VISION_IMAGES_URL = "https://vision.googleapis.com/v1/images:annotate"
VISION_FILES_URL = "https://vision.googleapis.com/v1/files:annotate"

# Vision's synchronous files:annotate endpoint accepts at most 5 pages
# per request. A typical question paper is 1-2 pages, so this is fine
# for the expo use case without needing async batch processing.
MAX_PDF_PAGES = 5


def _ocr_image_bytes_via_api_key(image_bytes: bytes, api_key: str) -> str:
    payload = {
        "requests": [
            {
                "image": {"content": base64.b64encode(image_bytes).decode("utf-8")},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            }
        ]
    }
    try:
        resp = requests.post(
            VISION_IMAGES_URL, params={"key": api_key}, json=payload, timeout=30
        )
    except requests.exceptions.RequestException as e:
        raise OCRError(f"Could not reach Google Vision API: {e}")

    if resp.status_code != 200:
        raise OCRError(f"Google Vision API returned status {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    result = data.get("responses", [{}])[0]
    if "error" in result:
        raise OCRError(f"Google Vision API error: {result['error'].get('message', 'unknown error')}")

    return result.get("fullTextAnnotation", {}).get("text", "")


def _ocr_pdf_via_api_key(pdf_bytes: bytes, api_key: str) -> str:
    """Send the PDF directly to Vision's files:annotate endpoint as
    base64. No local rendering, no poppler dependency."""
    payload = {
        "requests": [
            {
                "inputConfig": {
                    "mimeType": "application/pdf",
                    "content": base64.b64encode(pdf_bytes).decode("utf-8"),
                },
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                "pages": list(range(1, MAX_PDF_PAGES + 1)),
            }
        ]
    }
    try:
        resp = requests.post(
            VISION_FILES_URL, params={"key": api_key}, json=payload, timeout=45
        )
    except requests.exceptions.RequestException as e:
        raise OCRError(f"Could not reach Google Vision API: {e}")

    if resp.status_code != 200:
        raise OCRError(f"Google Vision API returned status {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    file_response = data.get("responses", [{}])[0]
    if "error" in file_response:
        raise OCRError(f"Google Vision API error: {file_response['error'].get('message', 'unknown error')}")

    page_responses = file_response.get("responses", [])
    texts = [page.get("fullTextAnnotation", {}).get("text", "") for page in page_responses]
    return "\n".join(t for t in texts if t)


def _get_vision_client():
    try:
        from google.cloud import vision
    except ImportError:
        raise OCRError(
            "google-cloud-vision is not installed. Run: pip install google-cloud-vision"
        )

    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not creds_path or not os.path.exists(creds_path):
        raise OCRError(
            "GOOGLE_APPLICATION_CREDENTIALS is not set to a valid file path. "
            "Either point it to your Google Cloud service-account JSON key file, "
            "or set GOOGLE_VISION_API_KEY to a plain API key instead."
        )

    try:
        return vision.ImageAnnotatorClient()
    except Exception as e:
        raise OCRError(f"Could not create Google Vision client: {e}")


def _ocr_image_bytes_via_client(image_bytes: bytes) -> str:
    from google.cloud import vision

    client = _get_vision_client()
    image = vision.Image(content=image_bytes)

    try:
        response = client.document_text_detection(image=image)
    except Exception as e:
        raise OCRError(f"Google Vision API request failed: {e}")

    if response.error.message:
        raise OCRError(f"Google Vision API error: {response.error.message}")

    return response.full_text_annotation.text or ""


def _ocr_image_bytes(image_bytes: bytes) -> str:
    api_key = os.getenv("GOOGLE_VISION_API_KEY", "").strip()
    if api_key:
        return _ocr_image_bytes_via_api_key(image_bytes, api_key)
    return _ocr_image_bytes_via_client(image_bytes)


def _pdf_to_text_via_client(pdf_bytes: bytes) -> str:
    """Service-account mode only: rasterize pages locally (needs
    pdf2image + poppler) then OCR each page image via the client
    library."""
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise OCRError(
            "pdf2image is not installed (or poppler is missing). "
            "Run: pip install pdf2image, and install the 'poppler-utils' system package. "
            "Alternatively, set GOOGLE_VISION_API_KEY instead, which OCRs PDFs "
            "natively with no poppler needed."
        )

    try:
        pages = convert_from_bytes(pdf_bytes, dpi=200)
    except Exception as e:
        raise OCRError(f"Could not render PDF pages: {e}")

    full_text = []
    for page_image in pages:
        buf = io.BytesIO()
        page_image.save(buf, format="PNG")
        page_text = _ocr_image_bytes_via_client(buf.getvalue())
        full_text.append(page_text)

    return "\n".join(full_text)


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from an uploaded question paper (PDF/JPG/JPEG/PNG)."""
    lower_name = filename.lower()
    api_key = os.getenv("GOOGLE_VISION_API_KEY", "").strip()

    if lower_name.endswith(".pdf"):
        if api_key:
            text = _ocr_pdf_via_api_key(file_bytes, api_key)
        else:
            text = _pdf_to_text_via_client(file_bytes)
    elif lower_name.endswith((".jpg", ".jpeg", ".png")):
        text = _ocr_image_bytes(file_bytes)
    else:
        raise OCRError("Unsupported file type. Please upload a PDF, JPG, JPEG, or PNG.")

    if not text or not text.strip():
        raise OCRError("No readable text was found in the uploaded file.")

    return text.strip()
