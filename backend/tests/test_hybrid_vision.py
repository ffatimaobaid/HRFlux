import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from local_visual_analyzer import analyze_document_visuals

def test_visual_analysis(pdf_path):
    print(f"🚀 Testing Hybrid Visual Analysis for: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return

    result = analyze_document_visuals(pdf_path)
    
    if result:
        print("\n--- [ANALYSIS RESULT] ---")
        print(result)
        print("-------------------------")
        print("✅ Success: Visual elements were found and described.")
    else:
        print("\nℹ️ No visual elements detected or analysis skipped.")

if __name__ == "__main__":
    # Test on one of the existing PDFs
    test_pdf = os.path.join(os.path.dirname(__file__), "policy_docs", "CVProjectReport.pdf")
    test_visual_analysis(test_pdf)
