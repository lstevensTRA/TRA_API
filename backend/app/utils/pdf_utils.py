import io
import re
import pypdf
import warnings
import logging

# Suppress pypdf FloatObject warnings at module level
warnings.filterwarnings(
    "ignore",
    message=r"FloatObject .+ invalid; use 0.0 instead",
    module="pypdf.generic._base"
)

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF bytes using pypdf, then pdfplumber, then OCR as fallback."""
    text = ""
    used_method = None

    def is_text_readable(text):
        if not text or len(text) < 100:
            return False
        # Too many (cid:xx) patterns = garbage
        if len(re.findall(r'\(cid:\d+\)', text)) > 10:
            return False
        # Too many non-ASCII or non-printable chars
        ascii_ratio = sum(32 <= ord(c) < 127 for c in text) / len(text)
        if ascii_ratio < 0.7:
            return False
        # At least 20% letters, at least 10 spaces per 1000 chars
        letter_ratio = sum(c.isalpha() for c in text) / len(text)
        space_ratio = text.count(' ') / max(1, len(text))
        return letter_ratio > 0.2 and space_ratio > 0.01

    # Try pypdf first
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            page_texts = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                page_texts.append(page_text)
            text = "\n".join(page_texts)
        if is_text_readable(text):
            used_method = "pypdf"
            logger.info(f"✅ Successfully extracted text using pypdf ({len(text)} chars)")
            return text
        else:
            logger.warning("⚠️ pypdf extraction unreadable, trying fallback")
    except Exception as e:
        logger.warning(f"⚠️ pypdf failed: {e}")

    # Try pdfplumber next
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            page_texts = []
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                page_texts.append(page_text)
            text = "\n".join(page_texts)
        if is_text_readable(text):
            used_method = "pdfplumber"
            logger.info(f"✅ Successfully extracted text using pdfplumber ({len(text)} chars)")
            return text
        else:
            logger.warning("⚠️ pdfplumber extraction unreadable, trying OCR")
    except Exception as e:
        logger.warning(f"⚠️ pdfplumber failed: {e}")

    # OCR fallback (optional - only if pdf2image and pytesseract are available)
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        images = convert_from_bytes(pdf_bytes)
        ocr_text = "\n".join(pytesseract.image_to_string(img) for img in images)
        if is_text_readable(ocr_text):
            used_method = "OCR"
            logger.info(f"✅ Successfully extracted text using OCR ({len(ocr_text)} chars)")
            return ocr_text
        else:
            logger.warning("⚠️ OCR extraction also unreadable")
    except ImportError as e:
        logger.warning(f"⚠️ OCR dependencies not available ({e}), skipping OCR fallback")
    except Exception as e:
        logger.warning(f"⚠️ OCR fallback failed: {e}")

    logger.error("❌ Could not extract readable text from PDF with any method")
    return "" 