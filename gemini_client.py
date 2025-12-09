import os
from google.generativeai import configure, GenerativeModel

def get_gemini_model():
    """
    Tries Gemini API keys from GEMINI_API_KEY env variable (comma-separated).
    Returns the first model that works.
    """
    api_keys_str = os.getenv("GEMINI_API_KEY", "")
    api_keys = [k.strip() for k in api_keys_str.split(",") if k.strip()]

    if not api_keys:
        raise RuntimeError("No Gemini API keys provided in GEMINI_API_KEY.")

    for key in api_keys:
        try:
            configure(api_key=key)
            model = GenerativeModel("gemini-pro")
            model.generate_content("ping")  # Lightweight validation
            print(f" Using Gemini key: {key[:6]}...")
            return model
        except Exception as e:
            if "usage limit" in str(e).lower() or "quota" in str(e).lower():
                print(f" Key {key[:6]}... hit usage limit.")
                continue
            else:
                raise e  # Unexpected error

    raise RuntimeError(" All Gemini API keys failed due to usage limits or errors.")
