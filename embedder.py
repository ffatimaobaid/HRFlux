import os
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from bs4 import BeautifulSoup
from docx import Document
from pptx import Presentation
from ebooklib import epub
from unstructured.partition.auto import partition

# Load embedding model globally with error handling
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
except ImportError as e:
    print(f"Warning: sentence-transformers not installed: {e}")
    model = None
except Exception as e:
    print(f"Warning: Could not load embedding model: {e}")
    model = None

def extract_text(file_path):
    """
    Detects the file type and extracts text accordingly.
    Uses `unstructured` for most formats, with fallbacks for EPUB and image OCR.
    """
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext in [".pdf", ".docx", ".pptx", ".html", ".htm", ".txt"]:
            text = extract_with_unstructured(file_path)
        elif ext == ".epub":
            text = extract_text_from_epub(file_path)
        elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
            text = extract_text_from_image(file_path)
        else:
            return "Unsupported file type."

        normalized = normalize_text(text)
        if len(normalized.strip()) < 50:
            print(f"[Warning] Extracted text is very short: {normalized[:100]}")
        return normalized

    except Exception as e:
        print(f"[Error] Failed to extract text from {file_path}: {e}")
        return f"Error extracting text: {e}"

def extract_with_unstructured(file_path):
    """
    Uses the `unstructured` library to extract text from supported files.
    """
    # Newer versions of `unstructured` expect `filename`, not `file_path` or `path`.
    # This fixes: "Exactly one of file, filename and url must be specified".
    elements = partition(filename=file_path)
    return "\n".join([el.text for el in elements if hasattr(el, 'text') and el.text])

def extract_text_from_image(image_path):
    """
    OCR extraction from image using Tesseract.
    """
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)

    if len(text.strip()) < 10:
        print(f"[Warning] OCR output too short for file: {image_path}, might be blank.")

    return text

def extract_text_from_epub(epub_path):
    """
    Extracts readable text from EPUB files using ebooklib + BeautifulSoup.
    """
    book = epub.read_epub(epub_path)
    text = []
    for item in book.get_items():
        if item.get_type() == epub.EpubHtml:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text.append(soup.get_text())
    return "\n".join(text)

def normalize_text(text):
    """
    Removes extra whitespace, trims lines, and normalizes encoding issues.
    """
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
