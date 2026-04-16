"""
Local Visual Document Analyzer (No API Required)
Uses pdfplumber for tables, Tesseract OCR for chart text, and BLIP for image captions.
All processing is done locally with no external API calls.
"""

import os
import logging
from io import BytesIO
import base64
from typing import Optional

logger = logging.getLogger(__name__)

# Try importing pdfplumber (table extraction)
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available. Install with: pip install pdfplumber")

# Try importing PIL + Tesseract (chart text / OCR)
try:
    from PIL import Image
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("PIL or pytesseract not available.")

# Try BLIP (image captioning)
try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
    _blip_processor = None
    _blip_model = None
    BLIP_AVAILABLE = True
except ImportError:
    BLIP_AVAILABLE = False
    _blip_processor = None
    _blip_model = None

# PyMuPDF for image extraction from PDFs
try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False


def _call_gemini_vision_expert(image: "Image.Image") -> str:
    """
    Sends a visual (chart/graph) to Gemini Vision for 'Perfect' interpretation.
    Only called as a fallback for complex visuals.
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage
        from config import get_current_gemini_key

        # Convert PIL image to base64
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=get_current_gemini_key(),
            temperature=0.1
        )

        prompt = (
            "You are a document analysis expert. This image is from an HR policy document. "
            "If it is a chart or graph, identify the type (bar, pie, line, etc.) and describe the EXACT data points, "
            "labels, values, and trends shown. If it is a table, convert it to a markdown table. "
            "Be precise and factual. If you cannot see specific data, describe the visual content."
        )

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{img_base64}",
                },
            ]
        )

        response = llm.invoke([message])
        return response.content.strip()
    except Exception as e:
        logger.error(f"Gemini Vision expert call failed: {e}")
        return ""


def _get_blip_model():
    """Lazily load BLIP model to avoid startup delay."""
    global _blip_processor, _blip_model
    if _blip_processor is None and BLIP_AVAILABLE:
        try:
            logger.info("Loading BLIP model for image captioning...")
            _blip_processor = BlipProcessor.from_pretrained(
                "Salesforce/blip-image-captioning-base", use_fast=True
            )
            _blip_model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            )
            logger.info("✅ BLIP model loaded.")
        except Exception as e:
            logger.error(f"BLIP model load failed: {e}")
            _blip_processor = None
            _blip_model = None
    return _blip_processor, _blip_model


def _caption_image(image: "Image.Image") -> str:
    """Generate a caption for an image using BLIP (runs locally)."""
    processor, model = _get_blip_model()
    if processor and model:
        try:
            inputs = processor(image.convert("RGB"), return_tensors="pt")
            output = model.generate(**inputs, max_new_tokens=60)
            caption = processor.decode(output[0], skip_special_tokens=True)
            return caption
        except Exception as e:
            logger.warning(f"BLIP captioning failed: {e}")
    return ""


def _ocr_image(image: "Image.Image") -> str:
    """Run Tesseract OCR on an image to extract text."""
    if not TESSERACT_AVAILABLE:
        return ""
    try:
        text = pytesseract.image_to_string(image.convert("RGB")).strip()
        return text
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return ""


def extract_tables_from_pdf(file_path: str) -> str:
    """
    Extract all tables from a PDF using pdfplumber.
    Returns a structured text description of each table found.
    """
    if not PDFPLUMBER_AVAILABLE:
        return ""

    all_table_text = []

    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                if not tables:
                    continue

                for table_idx, table in enumerate(tables, start=1):
                    if not table or len(table) < 2:
                        continue

                    lines = [
                        f"\n[Table {table_idx} on Page {page_num}]"
                    ]

                    # First row as header
                    header = table[0]
                    if header:
                        clean_header = [str(cell).strip() if cell else "" for cell in header]
                        lines.append("Columns: " + " | ".join(clean_header))

                    # Data rows
                    for row in table[1:]:
                        if row:
                            clean_row = [str(cell).strip() if cell else "" for cell in row]
                            lines.append(" | ".join(clean_row))

                    all_table_text.append("\n".join(lines))

    except Exception as e:
        logger.error(f"Table extraction failed for {file_path}: {e}")

    if all_table_text:
        result = "\n\n=== TABLES EXTRACTED FROM DOCUMENT ===\n"
        result += "\n\n".join(all_table_text)
        return result

    return ""


def extract_visual_descriptions_from_pdf(file_path: str) -> str:
    """
    Extract text + captions from all images embedded in a PDF.
    Uses:
      - PyMuPDF to extract embedded images
      - Tesseract OCR to read text from chart images
      - BLIP to generate image captions
    """
    if not FITZ_AVAILABLE:
        return ""

    descriptions = []

    try:
        doc = fitz.open(file_path)

        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            image_list = page.get_images(full=True)

            if not image_list:
                continue

            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]

                    image = Image.open(BytesIO(image_bytes)).convert("RGB")

                    # Skip very small images (icons, decorators)
                    if image.width < 80 or image.height < 80:
                        continue

                    parts = [
                        f"\n[Image on Page {page_index + 1}, Image {img_index + 1}]"
                    ]

                    # OCR — reads numbers and labels from charts
                    ocr_text = _ocr_image(image)
                    if ocr_text and len(ocr_text) > 10:
                        parts.append(f"Text/Numbers detected: {ocr_text}")

                    # BLIP caption — detects what the image is
                    caption = _caption_image(image)
                    if caption:
                        parts.append(f"Visual content: {caption}")

                    # --- HYBRID TRIGGER ---
                    # If local tools detect a chart/graph/table, call the Gemini Expert for "Perfect" data extraction.
                    # This saves quota by only calling the API when we actually see a complex visual.
                    visual_keywords = ["chart", "graph", "table", "diagram", "plot", "dashboard", "schedule"]
                    is_complex_visual = any(kw in caption.lower() for kw in visual_keywords) or \
                                      any(kw in ocr_text.lower() for kw in visual_keywords)

                    if is_complex_visual:
                        logger.info(f"  ✨ Complex visual detected. Calling Gemini Expert...")
                        expert_interpretation = _call_gemini_vision_expert(image)
                        if expert_interpretation:
                            parts.append(f"Expert Interpretation: {expert_interpretation}")
                            logger.info(f"  ✅ Gemini Expert interpretation received.")

                    if len(parts) > 1:
                        descriptions.append("\n".join(parts))


                except Exception as e:
                    logger.warning(f"Image {img_index + 1} on page {page_index + 1} failed: {e}")
                    continue

        doc.close()

    except Exception as e:
        logger.error(f"Visual extraction failed for {file_path}: {e}")

    if descriptions:
        result = "\n\n=== VISUAL CONTENT (CHARTS, GRAPHS, IMAGES) ===\n"
        result += "\n\n".join(descriptions)
        return result

    return ""


def analyze_document_visuals(file_path: str) -> str:
    """
    Main entry point: analyze a PDF document for tables and visual content.
    Returns a combined text description that can be appended to the document's text
    before chunking and embedding.

    Supports: PDF (tables + images). Other formats are skipped gracefully.
    """
    if not file_path.lower().endswith(".pdf"):
        return ""  # Only PDF supported for now

    logger.info(f"🔍 [VisualAnalyzer] Analyzing visuals in: {os.path.basename(file_path)}")

    result_parts = []

    # Step 1: Extract tables
    table_text = extract_tables_from_pdf(file_path)
    if table_text:
        result_parts.append(table_text)
        logger.info(f"  ✅ Tables extracted.")

    # Step 2: Extract and describe images/charts
    visual_text = extract_visual_descriptions_from_pdf(file_path)
    if visual_text:
        result_parts.append(visual_text)
        logger.info(f"  ✅ Image/chart descriptions generated.")

    if result_parts:
        return "\n\n".join(result_parts)

    logger.info(f"  ℹ️ No visual elements detected in {os.path.basename(file_path)}")
    return ""
