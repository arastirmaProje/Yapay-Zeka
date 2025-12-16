# model_bul.py
import google.generativeai as genai
import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Eğer .env okuyamazsa, test için API key'i tırnak içine buraya yapıştırabilirsin:
api_key = os.getenv("GEMINI_API_KEY") 

if not api_key:
    print("Hata: API Key bulunamadı.")
else:
    genai.configure(api_key=api_key)
    print("--- SENİN KULLANABİLECEĞİN MODELLER ---")
    try:
        for m in genai.list_models():
            # Sadece metin/chat üretebilen modelleri filtrele
            if 'generateContent' in m.supported_generation_methods:
                # Başındaki "models/" kısmını atarak temiz ismi yazdırıyoruz
                clean_name = m.name.replace("models/", "")
                print(f"Model Kodu: {clean_name}")
    except Exception as e:
        print(f"Hata: {e}")