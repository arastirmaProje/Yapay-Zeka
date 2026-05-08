import os
import json
import sys
from typing import Tuple, Dict, Any, List

import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
load_dotenv(dotenv_path=ROOT_DIR / ".env")

try:
    from app.models import PerformansIstegi, DepartmanIstegi
except ImportError:
    from ..models import PerformansIstegi, DepartmanIstegi


class PerformanceReportGenerator:

    def __init__(self, model_name: str = "gemini-2.5-flash") -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY çevre değişkeni tanımlanmadı.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    # ── Yardımcı metodlar ─────────────────────────────────────────────────

    def _gorev_metni_olustur(self, istek) -> str:
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
            satir = f"- [{gorev.durum.value}] {gorev.gorev_adi} | Zorluk: {gorev.zorluk_seviyesi.value}"
            if sure_saat is not None and sure_saat > 0:
                satir += f" | Süre: {sure_saat} saat"
            if gorev.geri_donut and gorev.geri_donut.strip():
                satir += f" | Geri Bildirim: {gorev.geri_donut}"
            satirlar.append(satir)
        return "\n".join(satirlar)

    def _json_parse(self, metin: str) -> dict:
        temiz = metin.strip()
        if "```" in temiz:
            parcalar = temiz.split("```")
            for parca in parcalar:
                parca = parca.strip()
                if parca.startswith("json"):
                    parca = parca[4:].strip()
                if parca.startswith("{"):
                    temiz = parca
                    break
        baslangic = temiz.find("{")
        bitis = temiz.rfind("}")
        if baslangic != -1 and bitis != -1:
            temiz = temiz[baslangic:bitis + 1]
        return json.loads(temiz)

    def _genel_durum_belirle(self, skor: float) -> str:
        if skor >= 85:
            return "Mükemmel"
        elif skor >= 70:
            return "İyi"
        elif skor >= 50:
            return "Geliştirilmesi Gerekiyor"
        else:
            return "Kritik"

    def _rapor_metni_olustur(self, veri: dict, genel_durum: str) -> Tuple[str, str]:
        maddeler = veri.get("ozet_maddeler", [])
        ozet = "\n".join(f"• {m}" for m in maddeler)
        ozet += f"\n\nGenel Durum: {genel_durum}"
        detay_parcalar = []
        if veri.get("guclu_yonler"):
            detay_parcalar.append("Güçlü Yönler:\n" + "\n".join(f"• {g}" for g in veri["guclu_yonler"]))
        if veri.get("gelisim_alanlari"):
            detay_parcalar.append("Gelişim Alanları:\n" + "\n".join(f"• {g}" for g in veri["gelisim_alanlari"]))
        if veri.get("somut_oneriler"):
            detay_parcalar.append("Öneriler:\n" + "\n".join(f"• {o}" for o in veri["somut_oneriler"]))
        if veri.get("detayli_analiz"):
            detay_parcalar.append(veri["detayli_analiz"])
        return ozet, "\n\n".join(detay_parcalar)

    def _prompt_kurallari(self) -> str:
        return """ÇIKTI KURALLARI:
- Yalnızca geçerli bir JSON nesnesi döndür
- JSON dışında hiçbir metin, açıklama veya markdown ekleme
- Şablon ifadeler kullanma, placeholder yazma
- Tüm metinler Türkçe olsun
- Her madde birbirinden FARKLI bilgi içermeli, tekrar etme
- detayli_analiz diğer alanların daha derin bir yorumu olsun"""

    def _json_format(self, genel_durum: str) -> str:
        return f"""DÖNDÜRÜLECEK JSON FORMATI:
{{
  "ozet_maddeler": ["madde 1 (skor ve genel durum)", "madde 2 (güçlü metrik)", "madde 3 (gelişim alanı)"],
  "genel_durum": "{genel_durum}",
  "guclu_yonler": ["güçlü yön 1", "güçlü yön 2", "güçlü yön 3"],
  "gelisim_alanlari": ["gelişim alanı 1", "gelişim alanı 2"],
  "somut_oneriler": ["öneri 1", "öneri 2", "öneri 3"],
  "detayli_analiz": "200-250 kelime arası akıcı Türkçe paragraf."
}}"""

    # ── Bireysel rapor ────────────────────────────────────────────────────

    def rapor_olustur(
        self,
        istek: PerformansIstegi,
        skor: float,
        analiz: Dict[str, Any],
    ) -> Tuple[str, str, Dict[str, Any]]:
        genel_durum = self._genel_durum_belirle(skor)
        gorev_metni = self._gorev_metni_olustur(istek)

        prompt = f"""
Aşağıdaki çalışan performans verilerini analiz ederek İK raporu oluştur.

{self._prompt_kurallari()}

{self._json_format(genel_durum)}

ÇALIŞAN BİLGİLERİ:
- Ad Soyad: {istek.ad_soyad}
- Performans Skoru: {skor:.2f} / 100
- Genel Durum: {genel_durum}

METRİKLER:
- Görev Tamamlanma Oranı: %{analiz['tamamlanma_orani']}
- Verimlilik Skoru: {analiz['verimlilik_skoru']} / 100
- Deadline Uyum Skoru: {analiz['deadline_uyum_skoru'] if analiz['deadline_uyum_skoru'] is not None else 'Veri Yok'}
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

        veri["genel_durum"] = genel_durum
        ozet, detay = self._rapor_metni_olustur(veri, genel_durum)

        grafik_verisi = {
            "mesai_karsilastirma": {
                "hedeflenen": istek.hedeflenen_mesai_saati,
                "gerceklesen": istek.gerceklesen_mesai_saati,
            },
            "performans_karsilastirma": {
                "guncel": round(skor, 2),
                "onceki": istek.onceki_performans_skoru,
            },
            "metrikler": {
                "tamamlanma_orani": analiz["tamamlanma_orani"],
                "verimlilik_skoru": analiz["verimlilik_skoru"],
                "deadline_uyum_skoru": analiz["deadline_uyum_skoru"],
                "zorluk_basari_dengesi": analiz["zorluk_basari_dengesi"],
                "mesai_kullanim_orani": analiz["mesai_kullanim_orani"],
                "ortalama_zorluk": analiz["ortalama_zorluk"],
            },
        }

        return ozet, detay, grafik_verisi

    # ── Departman raporu ──────────────────────────────────────────────────

    def departman_raporu_olustur(
        self,
        istek: DepartmanIstegi,
        departman_skoru: float,
        calisan_skorlari: List[Dict[str, Any]],
        departman_analizi: Dict[str, Any],
    ) -> Tuple[str, str, Dict[str, Any]]:
        genel_durum = self._genel_durum_belirle(departman_skoru)

        calisan_metni = "\n".join(
            f"- {c['ad_soyad']}: {c['skor']:.2f}/100"
            for c in sorted(calisan_skorlari, key=lambda x: x["skor"], reverse=True)
        )
        deadline_str = (
            f"%{departman_analizi['ortalama_deadline_uyumu']}"
            if departman_analizi["ortalama_deadline_uyumu"] is not None
            else "Veri Yok"
        )

        prompt = f"""
Aşağıdaki departman performans verilerini analiz ederek yöneticiye yönelik İK raporu oluştur.

{self._prompt_kurallari()}

{self._json_format(genel_durum)}

DEPARTMAN BİLGİLERİ:
- Departman: {istek.departman_adi}
- Toplam Çalışan: {len(istek.calisanlar)}
- Departman Performans Skoru: {departman_skoru:.2f} / 100
- Genel Durum: {genel_durum}

DEPARTMAN METRİKLERİ (Ortalama):
- Performans Skoru Ortalaması: {departman_analizi['ortalama_performans_skoru']}
- En Yüksek Skor: {departman_analizi['en_yuksek_skor']}
- En Düşük Skor: {departman_analizi['en_dusuk_skor']}
- Görev Tamamlanma Oranı: %{departman_analizi['ortalama_tamamlanma_orani']}
- Verimlilik: {departman_analizi['ortalama_verimlilik']} / 100
- Deadline Uyumu: {deadline_str}
- Zorluk-Başarı Dengesi: {departman_analizi['ortalama_zorluk_basari']} / 100
- Mesai Kullanım Oranı: %{departman_analizi['ortalama_mesai_kullanimi']}

ÇALIŞAN SKORLARI (Yüksekten Düşüğe):
{calisan_metni}
"""
        response = self.model.generate_content(prompt)
        metin = response.text if hasattr(response, "text") else str(response)

        try:
            veri = self._json_parse(metin)
        except (json.JSONDecodeError, ValueError):
            veri = {
                "ozet_maddeler": [
                    f"Departman skoru: {departman_skoru:.2f}/100 — {genel_durum}",
                    f"Ortalama tamamlanma: %{departman_analizi['ortalama_tamamlanma_orani']}",
                    f"En yüksek: {departman_analizi['en_yuksek_skor']}, En düşük: {departman_analizi['en_dusuk_skor']}",
                ],
                "genel_durum": genel_durum,
                "guclu_yonler": [],
                "gelisim_alanlari": [],
                "somut_oneriler": [],
                "detayli_analiz": metin,
            }

        veri["genel_durum"] = genel_durum
        ozet, detay = self._rapor_metni_olustur(veri, genel_durum)

        # Grafik verisi — mobilciler ve backend için
        grafik_verisi = {
            # Çalışan bazlı skor karşılaştırması (bar chart)
            "calisan_performans_karsilastirma": [
                {"ad_soyad": c["ad_soyad"], "skor": c["skor"]}
                for c in sorted(calisan_skorlari, key=lambda x: x["skor"], reverse=True)
            ],
            # Departman geneli metrik ortalamaları
            "departman_metrikleri": {
                "ortalama_tamamlanma_orani": departman_analizi["ortalama_tamamlanma_orani"],
                "ortalama_verimlilik": departman_analizi["ortalama_verimlilik"],
                "ortalama_deadline_uyumu": departman_analizi["ortalama_deadline_uyumu"],
                "ortalama_zorluk_basari": departman_analizi["ortalama_zorluk_basari"],
                "ortalama_mesai_kullanimi": departman_analizi["ortalama_mesai_kullanimi"],
            },
            # Skor özeti (min/max/ort)
            "skor_ozeti": {
                "departman_skoru": round(departman_skoru, 2),
                "en_yuksek": departman_analizi["en_yuksek_skor"],
                "en_dusuk": departman_analizi["en_dusuk_skor"],
                "ortalama": departman_analizi["ortalama_performans_skoru"],
            },
        }

        return ozet, detay, grafik_verisi