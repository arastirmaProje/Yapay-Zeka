import os
import sys
from typing import Tuple

import google.generativeai as genai
from dotenv import load_dotenv

# Paket olarak çalışmıyorsa kök dizini sys.path'e ekle
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# .env yolunu açıkça yükle (uvicorn farklı cwd ile çalışsa bile)
load_dotenv(dotenv_path=ROOT_DIR / ".env")

try:
    from app.models import PerformansIstegi
except ImportError:
    from ..models import PerformansIstegi


class PerformanceReportGenerator:
    """
    Gemini API kullanarak performans raporu üretir.
    """
    """"
    def __init__(self, model_name: str = "gemini-1.5-pro") -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(f"GEMINI_API_KEY çevre değişkeni tanımlanmadı. .env konumu: {ROOT_DIR / 'C:\\Users\\Yunus Emre\\OneDrive\\Masaüstü\\personelim-ai\\.env'}")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
    """
    def rapor_olustur(self, istek: PerformansIstegi, skor: float) -> Tuple[str, str]:
        """
        Özet ve detaylı rapor döndürür.
        """
        gorev_ozetleri = []
        for gorev in istek.gorevler[:5]:  # aşırı uzamaması için ilk 5
            gorev_ozetleri.append(
                f"- {gorev.gorev_adi} | Zorluk: {gorev.zorluk_seviyesi} | Durum: {gorev.durum}"
            )

        gorev_metni = "\n".join(gorev_ozetleri) if gorev_ozetleri else "Görev verisi yok."

        prompt = f"""
Şirket içi İK uzmanı gibi davran ve aşağıdaki bilgileri kullanarak Türkçe bir performans raporu yaz.
Format:
Özet:
- 2-3 maddelik kısa değerlendirme
- Skoru ve genel durumu belirt
Detay:
- En fazla 300 kelime
- Güçlü yönler, gelişim alanları, somut öneriler

Çalışan: {istek.ad_soyad} (ID: {istek.calisan_id})
Performans Skoru: {skor:.2f}/100
Hedeflenen haftalık mesai: {istek.hedeflenen_mesai_saati} saat
Gerçekleşen haftalık mesai: {istek.gerceklesen_mesai_saati} saat
Tamamlanan görev sayısı: {istek.tamamlanan_gorev_sayisi}
Tamamlanamayan görev sayısı: {istek.tamamlanamayan_gorev_sayisi}
Kullanılan izin günü: {istek.kullanilan_izin_gunu}
Görevler:
{gorev_metni}
"""

        response = self.model.generate_content(prompt)
        metin = response.text if hasattr(response, "text") else str(response)

        if "Detay:" in metin:
            ozet_kisim, detay_kisim = metin.split("Detay:", 1)
            ozet = ozet_kisim.replace("Özet:", "").strip()
            detay = detay_kisim.strip()
        else:
            ozet = metin.strip()
            detay = metin.strip()

        return ozet, detay
