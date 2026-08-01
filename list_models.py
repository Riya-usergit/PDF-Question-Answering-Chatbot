import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load settings from .env file
load_dotenv(".env")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("No GEMINI_API_KEY found in .env!")
    exit(1)

genai.configure(api_key=api_key)

print("Listing all available models for your API key...")
try:
    models = genai.list_models()
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name} (displayName: {m.display_name})")
except Exception as e:
    print(f"Error listing models: {e}")
