"""Document upload and text extraction module for MakeMeRichGPT.

Handles PDF text extraction, image OCR, and file memory.
"""

import os
import io
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# PDF extraction
try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

# Image OCR
try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


UPLOAD_DIR = "data/uploads"
UPLOAD_MEMORY_FILE = "data/upload_memory.json"


def ensure_upload_dir():
    """Ensure the upload directory exists."""
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    if not HAS_PYPDF2:
        return "[PDF extraction unavailable — PyPDF2 not installed]"

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())

        text = "\n\n".join(text_parts)
        if not text.strip():
            return "[PDF contained no extractable text — may be a scanned document]"
        return text
    except Exception as e:
        return f"[Error extracting PDF text: {str(e)}]"


def extract_text_from_image(file_bytes: bytes) -> str:
    """Extract text from an image using OCR."""
    if not HAS_OCR:
        return "[OCR unavailable — pytesseract not installed]"

    try:
        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image)
        if not text.strip():
            return "[No text detected in image]"
        return text.strip()
    except Exception as e:
        return f"[Error performing OCR: {str(e)}]"


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from a text file."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return file_bytes.decode("latin-1")
        except Exception:
            return "[Error decoding text file]"


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
