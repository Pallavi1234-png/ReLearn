"""OCR abstraction. The UI sends a handwriting canvas as a base64 PNG; today no OCR engine is wired in,
so we return available=False and the UI asks the student to type the working.
To add real OCR later, implement `recognise()` (e.g. pix2tex / Tesseract / a Hugging Face TrOCR model) - nothing else changes."""
import base64


def recognise(png_bytes: bytes) -> dict:
    return {"available": False, "text": "",
            "message": "Handwriting is captured but math OCR is not enabled in this build. Please type your working."}


def from_b64(data_url: str) -> dict:
    try:
        raw = base64.b64decode(data_url.split(",", 1)[-1])
    except Exception:
        return {"available": False, "text": "", "message": "Could not read the drawing."}
    return recognise(raw)
