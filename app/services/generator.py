# generator.py - güncellenmiş hali

import os
import json
import sys
from typing import Tuple, Dict, Any

import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
load_dotenv(dotenv_path=ROOT_DIR / ".env")

try:
    from app.models import PerformansIstegi
except ImportError:
    from ..models import PerformansIstegi


class PerformanceReportGenerator:

    def __init__(self, model_name: str = "gemini-2.5-flash") -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY çevre değişkeni tanımlanmadı.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def _gorev_metni_olustur(self, istek: PerformansIstegi) -> str:
        if not istek.gorevler:
            return "Görev verisi yok."

        satirlar = []
        for gorev in istek.gorevler[:8]:
            sure_saat = None
            try:
                delta = gorev.bitistarihi - gorev.baslangic_tarihi
                sure_saat = round(delta.total_seconds() / 3600, 1)
            except Exception:
                pass

            satir = (
                f"- [{gorev.durum.value}] {gorev.gorev_adi} "
                f"| Zorluk: {gorev.zorluk_seviyesi.value}"
            )
            if sure_saat is not None:
                satir += f" | Süre: {sure_saat} saat"
            if gorev.geri_donut:
                satir += f" | Geri bildirim: {gorev.geri_donut}"
            satirlar.append(satir)

        return "\n".join(satirlar)

    def rapor_olustur(
        self,
        istek: PerformansIstegi,
        skor: float,
        analiz: Dict[str, Any],
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Returns: (ozet, detay, grafik_verisi)
        """
        gorev_metni = self._gorev_metni_olustur(istek)

        prompt = f"""
Sen deneyimli bir İK analistisisin. Aşağıdaki çalışan verilerini analiz ederek
YALNIZCA geçerli bir JSON nesnesi döndür. Başka hiçbir metin, açıklama veya markdown ekleme.

JSON formatı tam olarak şu şekilde olmalı:
{{
  "ozet_maddeler": ["madde 1", "madde 2", "madde 3"],
  "genel_durum": "Mükemmel | İyi | Geliştirilmesi Gerekiyor | Kritik",
  "guclu_yonler": ["güçlü yön 1", "güçlü yön 2"],
  "gelisim_alanlari": ["alan 1", "alan 2"],
  "somut_oneriler": ["öneri 1", "öneri 2", "öneri 3"],
  "detayli_analiz": "200-300 kelime arası detaylı metin"
}}

--- ÇALIŞAN BİLGİLERİ ---
Ad Soyad: {istek.ad_soyad}
Performans Skoru: {skor:.2f}/100

--- METRİKLER ---
Mesai Kullanım Oranı: %{analiz['mesai_kullanim_orani']}
Görev Tamamlanma Oranı: %{analiz['tamamlanma_orani']}
Verimlilik Skoru: {analiz['verimlilik_skoru']}/100
Deadline Uyum Skoru: {analiz['deadline_uyum_skoru']}/100
Zorluk-Başarı Dengesi: {analiz['zorluk_basari_dengesi']}/100
Ortalama Görev Zorluğu: {analiz['ortalama_zorluk']}/5
Kullanılan İzin Günü: {istek.kullanilan_izin_gunu}

--- GÖREV DETAYLARI ---
{gorev_metni}
"""

        response = self.model.generate_content(prompt)
        metin = response.text if hasattr(response, "text") else str(response)

       
        try:
            temiz = metin.strip()
            if temiz.startswith("```"):
                temiz = temiz.split("```")[1]
                if temiz.startswith("json"):
                    temiz = temiz[4:]
            veri = json.loads(temiz.strip())
        except json.JSONDecodeError:
            veri = {
                "ozet_maddeler": [metin[:200]],
                "genel_durum": "Bilinmiyor",
                "guclu_yonler": [],
                "gelisim_alanlari": [],
                "somut_oneriler": [],
                "detayli_analiz": metin,
            }

        ozet = "\n".join(f"• {m}" for m in veri.get("ozet_maddeler", []))
        ozet += f"\n\nGenel Durum: {veri.get('genel_durum', '-')}"

        detay_parcalar = []
        if veri.get("guclu_yonler"):
            detay_parcalar.append("Güçlü Yönler:\n" + "\n".join(f"• {g}" for g in veri["guclu_yonler"]))
        if veri.get("gelisim_alanlari"):
            detay_parcalar.append("Gelişim Alanları:\n" + "\n".join(f"• {g}" for g in veri["gelisim_alanlari"]))
        if veri.get("somut_oneriler"):
            detay_parcalar.append("Öneriler:\n" + "\n".join(f"• {o}" for o in veri["somut_oneriler"]))
        if veri.get("detayli_analiz"):
            detay_parcalar.append(veri["detayli_analiz"])
        detay = "\n\n".join(detay_parcalar)

        # Mobil için grafik verisi
        grafik_verisi = {
            "radar": {
                "kategoriler": [
                    "Tamamlanma", "Verimlilik", "Deadline", "Zorluk/Başarı", "Mesai"
                ],
                "degerler": [
                    analiz["tamamlanma_orani"],
                    analiz["verimlilik_skoru"],
                    analiz["deadline_uyum_skoru"],
                    analiz["zorluk_basari_dengesi"],
                    min(100.0, analiz["mesai_kullanim_orani"]),
                ],
            },
            "gorev_dagilimi": {
                "tamamlandi": istek.tamamlanan_gorev_sayisi,
                "tamamlanamadi": istek.tamamlanamayan_gorev_sayisi,
                "devam_ediyor": sum(
                    1 for g in istek.gorevler if g.durum.value == "Devam ediyor"
                ),
            },
            "mesai_karsilastirma": {
                "hedeflenen": istek.hedeflenen_mesai_saati,
                "gerceklesen": istek.gerceklesen_mesai_saati,
            },
        }

        return ozet, detay, grafik_verisi