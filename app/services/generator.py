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

    def __init__(self, model_name: str = "gemini-2.5-flash-lite") -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY çevre değişkeni tanımlanmadı.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def _gorev_metni_olustur(self, istek: PerformansIstegi) -> str:
        if not istek.gorevler:
            return "Görev verisi bulunmamaktadır."

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
            if sure_saat is not None and sure_saat > 0:
                satir += f" | Tamamlanma Süresi: {sure_saat} saat"
            if gorev.geri_donut and gorev.geri_donut.strip():
                satir += f" | Yönetici Geri Bildirimi: {gorev.geri_donut}"
            satirlar.append(satir)

        return "\n".join(satirlar)

    def _json_parse(self, metin: str) -> dict:
        """Gemini çıktısını güvenli şekilde JSON'a çevirir."""
        temiz = metin.strip()

        # ``` bloğu varsa içini al
        if "```" in temiz:
            parcalar = temiz.split("```")
            for parca in parcalar:
                parca = parca.strip()
                if parca.startswith("json"):
                    parca = parca[4:].strip()
                if parca.startswith("{"):
                    temiz = parca
                    break

        # İlk { ile son } arasını al
        baslangic = temiz.find("{")
        bitis = temiz.rfind("}")
        if baslangic != -1 and bitis != -1:
            temiz = temiz[baslangic:bitis + 1]

        return json.loads(temiz)

    def _guclu_durum_belirle(self, skor: float) -> str:
        if skor >= 85:
            return "Mükemmel"
        elif skor >= 70:
            return "İyi"
        elif skor >= 50:
            return "Geliştirilmesi Gerekiyor"
        else:
            return "Kritik"

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
        genel_durum = self._guclu_durum_belirle(skor)

        prompt = f"""
Aşağıdaki çalışan performans verilerini analiz ederek bir İK raporu oluştur.

ÇIKTI KURALLARI:
- Yalnızca geçerli bir JSON nesnesi döndür
- JSON dışında hiçbir metin, açıklama, başlık veya markdown ekleme
- Şablon ifadeler kullanma ([Dönem Belirtiniz] gibi placeholder yazma)
- Tüm metinler Türkçe olsun
- Rakamları yorumlarken aşağıdaki bağlamı dikkate al

BAĞLAM:
- Performans skoru 0-100 arasında, {skor:.1f} puan aldı → Genel Durum: {genel_durum}
- Verimlilik skoru: birim saatte tamamlanan görev oranı (düşük olması fazla mesai harcandığına işaret eder)
- Deadline uyum skoru: görevlerin zamanında tamamlanma yüzdesi
- Zorluk-başarı dengesi: zor görevlerdeki başarı ağırlıklı oran

DÖNDÜRÜLECEK JSON FORMATI:
{{
  "ozet_maddeler": [
    "özet madde 1 (skoru ve genel durumu belirt)",
    "özet madde 2 (en güçlü metriği vurgula)",
    "özet madde 3 (varsa en kritik gelişim alanını belirt)"
  ],
  "genel_durum": "{genel_durum}",
  "guclu_yonler": [
    "güçlü yön 1",
    "güçlü yön 2",
    "güçlü yön 3"
  ],
  "gelisim_alanlari": [
    "gelişim alanı 1",
    "gelişim alanı 2"
  ],
  "somut_oneriler": [
    "somut ve uygulanabilir öneri 1",
    "somut ve uygulanabilir öneri 2",
    "somut ve uygulanabilir öneri 3"
  ],
  "detayli_analiz": "200-250 kelime arası, akıcı Türkçe paragraf. Güçlü yönler, gelişim alanları ve önerileri içersin. Placeholder veya şablon ifade kullanma."
}}

ÇALIŞAN BİLGİLERİ:
- Ad Soyad: {istek.ad_soyad}
- Performans Skoru: {skor:.2f} / 100
- Genel Durum: {genel_durum}

METRİKLER:
- Görev Tamamlanma Oranı: %{analiz['tamamlanma_orani']}
- Verimlilik Skoru: {analiz['verimlilik_skoru']} / 100
- Deadline Uyum Skoru: {analiz['deadline_uyum_skoru']} / 100
- Zorluk-Başarı Dengesi: {analiz['zorluk_basari_dengesi']} / 100
- Mesai Kullanım Oranı: %{analiz['mesai_kullanim_orani']}
- Ortalama Görev Zorluğu: {analiz['ortalama_zorluk']} / 5
- Tamamlanan Görev: {istek.tamamlanan_gorev_sayisi}
- Tamamlanamayan Görev: {istek.tamamlanamayan_gorev_sayisi}
- Kullanılan İzin Günü: {istek.kullanilan_izin_gunu}

GÖREV DETAYLARI:
{gorev_metni}
"""

        response = self.model.generate_content(prompt)
        metin = response.text if hasattr(response, "text") else str(response)

        try:
            veri = self._json_parse(metin)
        except (json.JSONDecodeError, ValueError):
            veri = {
                "ozet_maddeler": [
                    f"Performans skoru: {skor:.2f}/100 — {genel_durum}",
                    f"Görev tamamlanma oranı: %{analiz['tamamlanma_orani']}",
                    f"Mesai kullanım oranı: %{analiz['mesai_kullanim_orani']}",
                ],
                "genel_durum": genel_durum,
                "guclu_yonler": [],
                "gelisim_alanlari": [],
                "somut_oneriler": [],
                "detayli_analiz": metin,
            }

        # genel_durum her zaman tutarlı olsun
        veri["genel_durum"] = genel_durum

        # Özet metni oluştur
        maddeler = veri.get("ozet_maddeler", [])
        ozet = "\n".join(f"• {m}" for m in maddeler)
        ozet += f"\n\nGenel Durum: {genel_durum}"

        # Detay metni oluştur
        detay_parcalar = []

        if veri.get("guclu_yonler"):
            detay_parcalar.append(
                "Güçlü Yönler:\n" + "\n".join(f"• {g}" for g in veri["guclu_yonler"])
            )
        if veri.get("gelisim_alanlari"):
            detay_parcalar.append(
                "Gelişim Alanları:\n" + "\n".join(f"• {g}" for g in veri["gelisim_alanlari"])
            )
        if veri.get("somut_oneriler"):
            detay_parcalar.append(
                "Öneriler:\n" + "\n".join(f"• {o}" for o in veri["somut_oneriler"])
            )
        if veri.get("detayli_analiz"):
            detay_parcalar.append(veri["detayli_analiz"])

        detay = "\n\n".join(detay_parcalar)

        # Grafik verisi
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