"""Document upload and text extraction module for CouncilGPT.

Handles PDF text extraction, image OCR, and file memory.

OCR Strategy:
- Primary: pytesseract (requires system `tesseract-ocr` package)
- Fallback: PIL-based image metadata extraction (always available)
- Text files: direct UTF-8/Latin-1 decoding

All extraction errors are logged with full tracebacks for debugging.
"""

import os
import io
import json
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

# PDF extraction
try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    print("[DOCUMENTS] WARNING: PyPDF2 not installed — PDF extraction disabled")

# Image OCR
try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True

    # Test if tesseract binary is actually available
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        HAS_OCR = False
        print("[DOCUMENTS] WARNING: pytesseract installed but tesseract binary not found — OCR disabled, using PIL fallback")
except ImportError:
    HAS_OCR = False
    print("[DOCUMENTS] WARNING: pytesseract not installed — OCR disabled, using PIL fallback")

# PIL for fallback image analysis
try:
    from PIL import Image as PILImage
    from PIL.ExifTags import TAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[DOCUMENTS] WARNING: Pillow not installed — image analysis disabled")


UPLOAD_DIR = "data/uploads"
UPLOAD_MEMORY_FILE = "data/upload_memory.json"


def ensure_upload_dir():
    """Ensure the upload directory exists."""
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    if not HAS_PYPDF2:
        return "[PDF extraction unavailable — PyPDF2 not installed. Run: pip install PyPDF2]"

    try:
        print(f"[DOCUMENTS] Extracting text from PDF ({len(file_bytes)} bytes)...")
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text.strip())
                    print(f"[DOCUMENTS]   Page {page_num + 1}: extracted {len(page_text)} chars")
                else:
                    print(f"[DOCUMENTS]   Page {page_num + 1}: no extractable text (may be scanned)")
            except Exception as page_err:
                print(f"[DOCUMENTS]   Page {page_num + 1}: extraction error — {page_err}")
                continue

        text = "\n\n".join(text_parts)
        if not text.strip():
            return "[PDF contained no extractable text — may be a scanned/image-only PDF. Consider converting to a text-based PDF or uploading as an image for OCR.]"

        print(f"[DOCUMENTS] PDF extraction complete: {len(text)} total chars from {len(reader.pages)} pages")
        return text

    except Exception as e:
        print(f"[DOCUMENTS] PDF extraction FAILED: {e}")
        traceback.print_exc()
        return f"[Error extracting PDF text: {str(e)}]"


def extract_text_from_image(file_bytes: bytes) -> str:
    """
    Extract text from an image.

    Strategy:
    1. Try pytesseract OCR (if tesseract binary is installed)
    2. Fall back to PIL-based image description (always works)
    """
    if not HAS_PIL:
        return "[Image analysis unavailable — Pillow not installed]"

    try:
        image = PILImage.open(io.BytesIO(file_bytes))
        print(f"[DOCUMENTS] Image opened: {image.format} {image.size[0]}x{image.size[1]} {image.mode}")
    except Exception as e:
        print(f"[DOCUMENTS] Failed to open image: {e}")
        traceback.print_exc()
        return f"[Error opening image: {str(e)}]"

    # Attempt 1: Tesseract OCR
    if HAS_OCR:
        try:
            print("[DOCUMENTS] Attempting OCR with tesseract...")

            # Preprocess for better OCR: convert to RGB, resize if too small
            if image.mode in ("RGBA", "P", "LA"):
                image = image.convert("RGB")
            elif image.mode == "L":
                pass  # Grayscale is fine for OCR

            text = pytesseract.image_to_string(image)

            if text and text.strip():
                print(f"[DOCUMENTS] OCR extracted {len(text.strip())} chars")
                return text.strip()
            else:
                print("[DOCUMENTS] OCR returned empty text — image may not contain text")
        except Exception as e:
            print(f"[DOCUMENTS] OCR failed: {e}")
            traceback.print_exc()

    # Attempt 2: PIL-based image metadata extraction (fallback)
    try:
        print("[DOCUMENTS] Using PIL fallback for image analysis...")
        info_parts = []
        info_parts.append(f"Image format: {image.format or 'unknown'}")
        info_parts.append(f"Dimensions: {image.size[0]}x{image.size[1]} pixels")
        info_parts.append(f"Color mode: {image.mode}")

        # Try to extract EXIF data
        try:
            exif_data = image._getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    if tag_name in ("ImageDescription", "Make", "Model", "DateTime",
                                    "Software", "Artist", "Copyright", "UserComment"):
                        info_parts.append(f"{tag_name}: {value}")
        except Exception:
            pass

        # Try to get text chunks (PNG)
        if hasattr(image, "text") and image.text:
            for key, val in image.text.items():
                info_parts.append(f"Metadata[{key}]: {val[:500]}")

        # Analyze image content by color distribution
        try:
            colors = image.convert("RGB").getcolors(maxcolors=50000)
            if colors:
                info_parts.append(f"Unique colors: {len(colors)}")
                if len(colors) < 20:
                    info_parts.append("Note: Very few unique colors — this appears to be a simple graphic, chart, or diagram")
                elif len(colors) > 10000:
                    info_parts.append("Note: High color complexity — this appears to be a photograph or detailed chart")
        except Exception:
            pass

        result = "[Image uploaded — OCR not available. Image metadata:]\n" + "\n".join(info_parts)
        result += "\n\n[NOTE: To enable full text extraction from images, install tesseract-ocr: sudo apt install tesseract-ocr]"

        print(f"[DOCUMENTS] PIL fallback produced {len(result)} chars of metadata")
        return result

    except Exception as e:
        print(f"[DOCUMENTS] PIL fallback also failed: {e}")
        traceback.print_exc()
        return f"[Error analyzing image: {str(e)}. Install tesseract-ocr for OCR support.]"


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from a text file."""
    try:
        text = file_bytes.decode("utf-8")
        print(f"[DOCUMENTS] Text file decoded (UTF-8): {len(text)} chars")
        return text
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("latin-1")
            print(f"[DOCUMENTS] Text file decoded (Latin-1 fallback): {len(text)} chars")
            return text
        except Exception as e:
            print(f"[DOCUMENTS] Text file decode FAILED: {e}")
            return "[Error decoding text file — unsupported encoding]"


def process_upload(
    filename: str,
    file_bytes: bytes,
    conversation_id: str,
) -> Dict[str, Any]:
    """
    Process an uploaded file: save it, extract text, and store in memory.

    Args:
        filename: Original filename
        file_bytes: Raw file bytes
        conversation_id: The conversation this upload belongs to

    Returns:
        Dict with 'filename', 'extracted_text', 'file_type', 'saved_path'
    """
    ensure_upload_dir()

    print(f"\n[DOCUMENTS] ═══════════════════════════════════════════")
    print(f"[DOCUMENTS] Processing upload: {filename}")
    print(f"[DOCUMENTS] Size: {len(file_bytes)} bytes ({len(file_bytes) / 1024:.1f} KB)")
    print(f"[DOCUMENTS] Conversation: {conversation_id}")

    # Determine file type
    ext = os.path.splitext(filename)[1].lower()
    file_type = "unknown"
    extracted_text = ""

    if ext == ".pdf":
        file_type = "pdf"
        extracted_text = extract_text_from_pdf(file_bytes)
    elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"):
        file_type = "image"
        extracted_text = extract_text_from_image(file_bytes)
    elif ext in (".txt", ".md", ".csv", ".log", ".json", ".xml", ".html"):
        file_type = "text"
        extracted_text = extract_text_from_txt(file_bytes)
    else:
        file_type = "binary"
        extracted_text = f"[Unsupported file type: {ext}]"

    print(f"[DOCUMENTS] File type: {file_type}")
    print(f"[DOCUMENTS] Extracted text length: {len(extracted_text)} chars")
    print(f"[DOCUMENTS] First 200 chars: {extracted_text[:200]}...")
    print(f"[DOCUMENTS] ═══════════════════════════════════════════\n")

    # Save the file
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = f"{timestamp}_{filename}"
    save_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    # Truncate text if too long
    if len(extracted_text) > 10000:
        extracted_text = extracted_text[:10000] + "\n\n[Text truncated — document was too long]"

    # Save to memory index
    memory_entry = {
        "filename": filename,
        "file_type": file_type,
        "saved_path": save_path,
        "conversation_id": conversation_id,
        "extracted_text": extracted_text,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": len(file_bytes),
    }
    _save_to_memory(memory_entry)

    return {
        "filename": filename,
        "file_type": file_type,
        "extracted_text": extracted_text,
        "saved_path": save_path,
        "size_bytes": len(file_bytes),
    }


def _save_to_memory(entry: Dict[str, Any]):
    """Append an upload entry to the memory index."""
    Path(os.path.dirname(UPLOAD_MEMORY_FILE)).mkdir(parents=True, exist_ok=True)

    memories = []
    if os.path.exists(UPLOAD_MEMORY_FILE):
        try:
            with open(UPLOAD_MEMORY_FILE, "r") as f:
                memories = json.load(f)
        except (json.JSONDecodeError, IOError):
            memories = []

    memories.append(entry)

    with open(UPLOAD_MEMORY_FILE, "w") as f:
        json.dump(memories, f, indent=2)


def get_upload_history(conversation_id: Optional[str] = None) -> list:
    """Get upload history, optionally filtered by conversation."""
    if not os.path.exists(UPLOAD_MEMORY_FILE):
        return []

    try:
        with open(UPLOAD_MEMORY_FILE, "r") as f:
            memories = json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

    if conversation_id:
        return [m for m in memories if m.get("conversation_id") == conversation_id]
    return memories


def search_upload_memory(query: str) -> list:
    """Search through uploaded document texts for relevant content."""
    if not os.path.exists(UPLOAD_MEMORY_FILE):
        return []

    try:
        with open(UPLOAD_MEMORY_FILE, "r") as f:
            memories = json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

    query_lower = query.lower()
    results = []
    for m in memories:
        text = m.get("extracted_text", "").lower()
        if query_lower in text:
            results.append({
                "filename": m["filename"],
                "conversation_id": m.get("conversation_id"),
                "uploaded_at": m.get("uploaded_at"),
                "snippet": _extract_snippet(m["extracted_text"], query, 200),
            })

    return results


def _extract_snippet(text: str, query: str, max_len: int = 200) -> str:
    """Extract a snippet around the query match."""
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[:max_len]
    start = max(0, idx - max_len // 2)
    end = min(len(text), idx + len(query) + max_len // 2)
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet
