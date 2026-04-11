from transformers import BlipProcessor, BlipForConditionalGeneration
from pdf2image import convert_from_path
from PIL import Image

# Load BLIP model and processor once
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

def generate_caption(image: Image.Image):
    """
    Generate a natural language caption for the given image.
    """
    inputs = processor(images=image, return_tensors="pt")
    out = model.generate(**inputs)
    caption = processor.decode(out[0], skip_special_tokens=True)
    return caption

def extract_image_captions(pdf_path):
    """
    Converts PDF pages to images and generates captions using BLIP.
    Returns a list of caption strings (one per image page).
    """
    captions = []
    try:
        images = convert_from_path(pdf_path)
        for i, image in enumerate(images):
            caption = generate_caption(image)
            captions.append(f"[Image Page {i+1}] {caption}")
    except Exception as e:
        print(f"Failed to generate image captions: {e}")
    return captions
