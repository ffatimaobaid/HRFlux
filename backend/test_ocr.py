import fitz
import pytesseract
from PIL import Image
import os

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
file_path = os.path.join("policy_docs", "PPIT Assignment 2.pdf")

def test_single_ocr():
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    print(f"--- Testing OCR on {file_path} ---")
    doc = fitz.open(file_path)
    combined_text = ""
    for i in range(len(doc)):
        print(f"Processing page {i+1}...")
        page = doc[i]
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0)) # 144 DPI (Faster/Enough)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img)
        print(f"Extracted {len(text)} chars from page {i+1}")
        combined_text += text + "\n"
    doc.close()
    
    with open("ocr_result.txt", "w", encoding="utf-8") as f:
        f.write(combined_text)
    print(f"--- DONE. Final chars: {len(combined_text)} ---")

if __name__ == "__main__":
    test_single_ocr()
