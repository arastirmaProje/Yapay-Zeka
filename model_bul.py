import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY") 

if not api_key:
    print("Hata: API Key bulunamadı.")
else:
    genai.configure(api_key=api_key)
    print("--- SENİN KULLANABİLECEĞİN MODELLER ---")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                clean_name = m.name.replace("models/", "")
                print(f"Model Kodu: {clean_name}")
    except Exception as e:
        print(f"Hata: {e}")