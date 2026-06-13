import os
import re
import json
import sys
from typing import Tuple, Dict, Any, List

import google.generativeai as genai
from google.generativeai import types
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

        # ── MALİYET KONTROLÜ ──────────────────────────────────────────────
        # 1. response_mime_type="application/json" → Görsel üretimi ENGELLER,
        #    sadece JSON metin döner. Pro/Imagen modeline yönlendirmeyi önler.
        # 2. max_output_tokens → Yanıt boyutunu sınırlar
        # 3. Model: gemini-2.5-flash → En uygun fiyat/kalite dengesi
        self.generation_config = types.GenerationConfig(
            response_mime_type="application/json",
            max_output_tokens=4096,
            temperature=0.7,
        )

        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config,
        )

    # ── Metin Temizleme ───────────────────────────────────────────────────

    def _temizle(self, metin: str) -> str:
        """
        Gemini çıktısındaki markdown ve HTML kalıntılarını temizler.
        Mobil uygulamaya düz metin (plain text) olarak gönderilecek
        şekilde arındırır.
        """
        if not metin or not isinstance(metin, str):
            return metin or ""

        # HTML etiketlerini kaldır (<b>, <br>, <p>, <strong> vs.)
        metin = re.sub(r"<[^>]+>", "", metin)

        # Markdown başlık işaretleri (### başlık → başlık)
        metin = re.sub(r"^#{1,6}\s*", "", metin, flags=re.MULTILINE)

        # Markdown kalın (**metin** veya __metin__)
        metin = re.sub(r"\*\*(.+?)\*\*", r"\1", metin)
        metin = re.sub(r"__(.+?)__", r"\1", metin)

        # Markdown italik (*metin* veya _metin_) — tek karakter
        metin = re.sub(r"(?<!\w)\*([^*\n]+?)\*(?!\w)", r"\1", metin)
        metin = re.sub(r"(?<!\w)_([^_\n]+?)_(?!\w)", r"\1", metin)

        # Markdown üstü çizili (~~metin~~)
        metin = re.sub(r"~~(.+?)~~", r"\1", metin)

        # Markdown kod blokları (```kod``` ve `kod`)
        metin = re.sub(r"```[\s\S]*?```", "", metin)
        metin = re.sub(r"`([^`]+)`", r"\1", metin)

        # Markdown linkler [metin](url) → metin
        metin = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", metin)

        # Markdown yatay çizgi (--- veya ***)
        metin = re.sub(r"^[-*_]{3,}\s*$", "", metin, flags=re.MULTILINE)

        # Markdown liste işaretleri (- veya * ile başlayan satırlar)
        # Bunları bullet noktasına dönüştür
        metin = re.sub(r"^\s*[-*]\s+", "• ", metin, flags=re.MULTILINE)

        # Fazla boş satırları tek satıra indir
        metin = re.sub(r"\n{3,}", "\n\n", metin)

        return metin.strip()

    def _temizle_dict(self, veri: dict) -> dict:
        """Dict içindeki tüm string değerleri ve liste elemanlarını temizler."""
        temiz = {}
        for anahtar, deger in veri.items():
            if isinstance(deger, str):
                temiz[anahtar] = self._temizle(deger)
            elif isinstance(deger, list):
                temiz[anahtar] = [
                    self._temizle(eleman) if isinstance(eleman, str) else eleman
                    for eleman in deger
                ]
            else:
                temiz[anahtar] = deger
        return temiz

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

    def _partial_json_extract(self, metin: str) -> str:
        """
        Yarım/bozuk JSON'dan okunabilir metin çıkarır.
        Parse edilemeyen Gemini çıktısını kullanıcıya ham JSON olarak
        göstermek yerine anlamlı düz metne dönüştürür.
        """
        if not metin:
            return ""
        # JSON string değerlerini çıkar ("..." içindeki metinler)
        parcalar = re.findall(r'"([^"]{15,})"', metin)
        if parcalar:
            # JSON anahtarlarını filtrele, sadece anlamlı metinleri al
            json_anahtarlar = {
                "ozet_maddeler", "genel_durum", "guclu_yonler",
                "gelisim_alanlari", "somut_oneriler", "detayli_analiz",
            }
            anlamli = [
                p for p in parcalar
                if p.strip() not in json_anahtarlar and not p.strip().startswith("{")
            ]
            if anlamli:
                return self._temizle("\n".join(f"• {m}" for m in anlamli))
        # Hiçbir şey çıkaramazsa JSON kalıntılarını temizle
        temiz = re.sub(r'[{}\[\]",:]+', ' ', metin)
        temiz = re.sub(r'\b(ozet_maddeler|guclu_yonler|gelisim_alanlari|somut_oneriler|detayli_analiz|genel_durum)\b', '', temiz)
        temiz = re.sub(r'\s{2,}', ' ', temiz).strip()
        return self._temizle(temiz) if temiz else "Detaylı rapor oluşturulamadı."

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
        ozet = self._temizle(ozet)
        detay = self._temizle("\n\n".join(detay_parcalar))
        return ozet, detay

    def _prompt_kurallari(self) -> str:
        return """KESİN ÇIKTI KURALLARI (İHLAL ETME):
1. Yanıtın yalnızca geçerli bir JSON nesnesi olacak. JSON dışında tek bir karakter bile yazma.
2. Markdown biçimlendirme kesinlikle YASAK: yıldız (*), alt çizgi (_), diyez (#), üstü çizili (~~), backtick (`) ve köşeli parantez bağlantısı ([text](url)) kullanma.
3. HTML etiketi kesinlikle YASAK: <b>, <i>, <br>, <p>, <strong>, <em> gibi hiçbir HTML etiketi kullanma.
4. Metinlerde sadece düz Türkçe metin yaz. Biçimlendirme veya özel işaret kullanma.
5. Şablon ifade veya placeholder kullanma. Her cümle gerçek veriye dayalı, özgün ve anlamlı olsun.
6. Tüm metinler profesyonel İK diliyle Türkçe yazılsın.
7. Her madde birbirinden FARKLI ve özgün bilgi içermeli, asla tekrar etme.
8. Sayısal verileri cümle içinde doğal şekilde kullan (oranlarda % işareti ile).
9. detayli_analiz alanı diğer alanların tekrarı değil, verilerin bütünsel bir yorumu ve derinlemesine değerlendirmesi olsun."""

    def _json_format_bireysel(self, genel_durum: str) -> str:
        return f"""DÖNDÜRÜLECEK JSON FORMATI (bu yapıya birebir uy):
{{
  "ozet_maddeler": [
    "Performans skorunu ve genel durumu özetleyen tek cümle",
    "En güçlü metriği vurgulayan tek cümle",
    "Gelişim gerektiren alanı belirten tek cümle"
  ],
  "genel_durum": "{genel_durum}",
  "guclu_yonler": [
    "Verilerden çıkan birinci güçlü yön (somut metrik referansıyla)",
    "Verilerden çıkan ikinci güçlü yön (somut metrik referansıyla)",
    "Verilerden çıkan üçüncü güçlü yön (somut metrik referansıyla)"
  ],
  "gelisim_alanlari": [
    "Birinci gelişim alanı (hangi metriğin neden düşük olduğunu açıkla)",
    "İkinci gelişim alanı (hangi metriğin neden düşük olduğunu açıkla)"
  ],
  "somut_oneriler": [
    "Uygulanabilir birinci öneri (zaman çerçevesi ve beklenen etki belirt)",
    "Uygulanabilir ikinci öneri (zaman çerçevesi ve beklenen etki belirt)",
    "Uygulanabilir üçüncü öneri (zaman çerçevesi ve beklenen etki belirt)"
  ],
  "detayli_analiz": "200-250 kelime arası akıcı Türkçe paragraf. Çalışanın genel performans tablosunu değerlendir. Güçlü ve zayıf yönleri bağlamsal olarak yorumla. Metriklerin birbirleriyle ilişkisini analiz et. Kısa ve uzun vadeli gelişim önerileri sun. Profesyonel İK dili kullan, düz metin yaz, biçimlendirme işareti kullanma."
}}"""

    def _json_format_departman(self, genel_durum: str) -> str:
        return f"""DÖNDÜRÜLECEK JSON FORMATI (bu yapıya birebir uy):
{{
  "ozet_maddeler": [
    "Departman skorunu ve genel durumu özetleyen tek cümle",
    "Departmanın en güçlü metriğini vurgulayan tek cümle",
    "Departmanın gelişim gerektiren alanını belirten tek cümle"
  ],
  "genel_durum": "{genel_durum}",
  "guclu_yonler": [
    "Departmanın verilerden çıkan birinci güçlü yönü (somut metrik referansıyla)",
    "Departmanın verilerden çıkan ikinci güçlü yönü (somut metrik referansıyla)",
    "Departmanın verilerden çıkan üçüncü güçlü yönü (somut metrik referansıyla)"
  ],
  "gelisim_alanlari": [
    "Departmanın birinci gelişim alanı (hangi metriğin neden düşük olduğunu açıkla)",
    "Departmanın ikinci gelişim alanı (hangi metriğin neden düşük olduğunu açıkla)"
  ],
  "somut_oneriler": [
    "Yöneticiye yönelik uygulanabilir birinci öneri (ekip geneli)",
    "Yöneticiye yönelik uygulanabilir ikinci öneri (bireysel gelişim)",
    "Yöneticiye yönelik uygulanabilir üçüncü öneri (süreç iyileştirme)"
  ],
  "detayli_analiz": "250-300 kelime arası akıcı Türkçe paragraf. Departmanın genel performans tablosunu yönetici perspektifinden değerlendir. Çalışanlar arası performans dağılımını, ekip dinamiklerini ve metrik ortalamalarını bağlamsal olarak yorumla. Yöneticiye stratejik aksiyon önerileri sun. Profesyonel İK dili kullan, düz metin yaz, biçimlendirme işareti kullanma."
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

        deadline_str = (
            f"%{analiz['deadline_uyum_skoru']}"
            if analiz["deadline_uyum_skoru"] is not None
            else "Veri Yok"
        )

        prompt = f"""Sen kurumsal bir İnsan Kaynakları performans analiz uzmanısın.
Aşağıda bir çalışana ait aylık performans verileri ve görev detayları sunulmaktadır.
Bu verileri analiz ederek profesyonel bir bireysel performans değerlendirme raporu oluştur.

{self._prompt_kurallari()}

{self._json_format_bireysel(genel_durum)}

─── ÇALIŞAN PROFİLİ ───
Ad Soyad: {istek.ad_soyad}
Performans Skoru: {skor:.2f} / 100
Genel Durum: {genel_durum}

─── PERFORMANS METRİKLERİ ───
Görev Tamamlanma Oranı: %{analiz['tamamlanma_orani']}
Verimlilik Skoru (saat başı üretkenlik): {analiz['verimlilik_skoru']} / 100
Deadline Uyum Skoru: {deadline_str}
Zorluk-Başarı Dengesi: {analiz['zorluk_basari_dengesi']} / 100
Mesai Kullanım Oranı: %{analiz['mesai_kullanim_orani']}
Ortalama Görev Zorluğu: {analiz['ortalama_zorluk']} / 5

─── GÖREV İSTATİSTİKLERİ ───
Tamamlanan Görev Sayısı: {istek.tamamlanan_gorev_sayisi}
Tamamlanamayan Görev Sayısı: {istek.tamamlanamayan_gorev_sayisi}
Kullanılan İzin Günü: {istek.kullanilan_izin_gunu}
Hedeflenen Aylık Mesai: {istek.hedeflenen_mesai_saati} saat
Gerçekleşen Aylık Mesai: {istek.gerceklesen_mesai_saati} saat

─── GÖREV DETAYLARI ───
{gorev_metni}

ÖNEMLİ HATIRLATMA: Yanıtında kesinlikle markdown (*, **, #, `, ~~) ve HTML (<b>, <br> vb.) kullanma. Yalnızca düz Türkçe metin içeren geçerli JSON döndür."""

        response = self.model.generate_content(
            prompt,
            generation_config=self.generation_config,
        )
        metin = response.text if hasattr(response, "text") else str(response)

        try:
            veri = self._json_parse(metin)
            veri = self._temizle_dict(veri)
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
                "detayli_analiz": self._partial_json_extract(metin),
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
        calisan_analizleri: List[Dict[str, Any]] = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        genel_durum = self._genel_durum_belirle(departman_skoru)

        sirali_calisanlar = sorted(calisan_skorlari, key=lambda x: x["skor"], reverse=True)
        calisan_metni = "\n".join(
            f"- {c['ad_soyad']}: {c['skor']:.2f}/100"
            for c in sirali_calisanlar
        )
        deadline_str = (
            f"%{departman_analizi['ortalama_deadline_uyumu']}"
            if departman_analizi["ortalama_deadline_uyumu"] is not None
            else "Veri Yok"
        )

        # Skor dağılımı bilgisi
        skor_farki = departman_analizi["en_yuksek_skor"] - departman_analizi["en_dusuk_skor"]

        prompt = f"""Sen kurumsal bir İnsan Kaynakları departman performans analiz uzmanısın.
Aşağıda bir departmana ait aylık performans verileri ve çalışan bazlı skor dağılımı sunulmaktadır.
Bu verileri analiz ederek departman yöneticisine yönelik profesyonel bir performans değerlendirme raporu oluştur.
Rapor, yöneticinin stratejik kararlar alabilmesi için somut ve uygulanabilir bilgiler içermelidir.

{self._prompt_kurallari()}

{self._json_format_departman(genel_durum)}

─── DEPARTMAN PROFİLİ ───
Departman Adı: {istek.departman_adi}
Toplam Çalışan Sayısı: {len(istek.calisanlar)}
Departman Performans Skoru: {departman_skoru:.2f} / 100
Genel Durum: {genel_durum}

─── DEPARTMAN METRİK ORTALAMALARI ───
Performans Skoru Ortalaması: {departman_analizi['ortalama_performans_skoru']} / 100
En Yüksek Bireysel Skor: {departman_analizi['en_yuksek_skor']} / 100
En Düşük Bireysel Skor: {departman_analizi['en_dusuk_skor']} / 100
Skor Farkı (En Yüksek - En Düşük): {skor_farki:.2f} puan
Görev Tamamlanma Oranı Ortalaması: %{departman_analizi['ortalama_tamamlanma_orani']}
Verimlilik Ortalaması: {departman_analizi['ortalama_verimlilik']} / 100
Deadline Uyum Ortalaması: {deadline_str}
Zorluk-Başarı Dengesi Ortalaması: {departman_analizi['ortalama_zorluk_basari']} / 100
Mesai Kullanım Oranı Ortalaması: %{departman_analizi['ortalama_mesai_kullanimi']}

─── ÇALIŞAN SKOR DAĞILIMI (Yüksekten Düşüğe) ───
{calisan_metni}

ÖNEMLİ HATIRLATMA: Yanıtında kesinlikle markdown (*, **, #, `, ~~) ve HTML (<b>, <br> vb.) kullanma. Yalnızca düz Türkçe metin içeren geçerli JSON döndür."""

        response = self.model.generate_content(
            prompt,
            generation_config=self.generation_config,
        )
        metin = response.text if hasattr(response, "text") else str(response)

        try:
            veri = self._json_parse(metin)
            veri = self._temizle_dict(veri)
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
                "detayli_analiz": self._partial_json_extract(metin),
            }

        veri["genel_durum"] = genel_durum
        ozet, detay = self._rapor_metni_olustur(veri, genel_durum)

        # Grafik verisi — mobilciler ve backend için
        grafik_verisi = {
            # Çalışan bazlı skor karşılaştırması (bar chart)
            "calisan_performans_karsilastirma": [
                {"ad_soyad": c["ad_soyad"], "skor": c["skor"]}
                for c in sirali_calisanlar
            ],
            # Çalışan bazlı mesai karşılaştırması (grouped bar chart)
            "calisan_mesai_karsilastirma": [
                {
                    "ad_soyad": c.ad_soyad,
                    "hedeflenen": c.hedeflenen_mesai_saati,
                    "gerceklesen": c.gerceklesen_mesai_saati,
                    "mesai_kullanim_orani": round(
                        (c.gerceklesen_mesai_saati / c.hedeflenen_mesai_saati * 100)
                        if c.hedeflenen_mesai_saati > 0 else 0.0, 1
                    ),
                }
                for c in istek.calisanlar
            ],
            # Çalışan bazlı detaylı metrikler (radar chart / multi-metric)
            "calisan_detayli_metrikler": self._calisan_detayli_metrik_olustur(
                istek, calisan_skorlari, calisan_analizleri
            ),
            # Departman geneli mesai özeti (pie / donut chart)
            "departman_mesai_ozeti": {
                "toplam_hedeflenen": round(sum(c.hedeflenen_mesai_saati for c in istek.calisanlar), 1),
                "toplam_gerceklesen": round(sum(c.gerceklesen_mesai_saati for c in istek.calisanlar), 1),
                "mesai_kullanim_orani": round(
                    (sum(c.gerceklesen_mesai_saati for c in istek.calisanlar) /
                     max(sum(c.hedeflenen_mesai_saati for c in istek.calisanlar), 1)) * 100, 1
                ),
            },
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
            # Görev dağılımı (departman geneli)
            "gorev_dagilimi": {
                "toplam_tamamlanan": sum(c.tamamlanan_gorev_sayisi for c in istek.calisanlar),
                "toplam_tamamlanamayan": sum(c.tamamlanamayan_gorev_sayisi for c in istek.calisanlar),
                "toplam_gorev": sum(
                    c.tamamlanan_gorev_sayisi + c.tamamlanamayan_gorev_sayisi
                    for c in istek.calisanlar
                ),
            },
            # --- Yeni Eklenen Çalışan Karşılaştırma Grafikleri (Swift Charts uyumlu) ---
            "calisan_tamamlanma_orani_karsilastirma": [
                {
                    "ad_soyad": istek.calisanlar[i].ad_soyad,
                    "oran": calisan_analizleri[i].get("tamamlanma_orani", 0) if calisan_analizleri and i < len(calisan_analizleri) else 0,
                }
                for i in range(len(istek.calisanlar))
            ],
            "calisan_verimlilik_karsilastirma": [
                {
                    "ad_soyad": istek.calisanlar[i].ad_soyad,
                    "verimlilik": calisan_analizleri[i].get("verimlilik_skoru", 0) if calisan_analizleri and i < len(calisan_analizleri) else 0,
                }
                for i in range(len(istek.calisanlar))
            ],
            "calisan_zorluk_basari_karsilastirma": [
                {
                    "ad_soyad": istek.calisanlar[i].ad_soyad,
                    "zorluk_basari": calisan_analizleri[i].get("zorluk_basari_dengesi", 0) if calisan_analizleri and i < len(calisan_analizleri) else 0,
                }
                for i in range(len(istek.calisanlar))
            ],
            "calisan_deadline_uyumu_karsilastirma": [
                {
                    "ad_soyad": istek.calisanlar[i].ad_soyad,
                    "deadline_uyumu": calisan_analizleri[i].get("deadline_uyum_skoru", 0) if calisan_analizleri and i < len(calisan_analizleri) and calisan_analizleri[i].get("deadline_uyum_skoru") is not None else 0,
                }
                for i in range(len(istek.calisanlar))
            ],
            "calisan_gorev_dagilimi_karsilastirma": [
                {
                    "ad_soyad": c.ad_soyad,
                    "tamamlanan": c.tamamlanan_gorev_sayisi,
                    "tamamlanamayan": c.tamamlanamayan_gorev_sayisi,
                    "toplam": c.tamamlanan_gorev_sayisi + c.tamamlanamayan_gorev_sayisi,
                }
                for c in istek.calisanlar
            ],
        }

        return ozet, detay, grafik_verisi

    def _calisan_detayli_metrik_olustur(
        self,
        istek: DepartmanIstegi,
        calisan_skorlari: List[Dict[str, Any]],
        calisan_analizleri: List[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Her çalışan için detaylı metrikleri birleştirir (radar/multi-metric chart için)."""
        sonuc = []
        for i, calisan in enumerate(istek.calisanlar):
            skor_bilgisi = next(
                (c for c in calisan_skorlari if c["ad_soyad"] == calisan.ad_soyad),
                {"skor": 0.0},
            )
            metrik = {
                "ad_soyad": calisan.ad_soyad,
                "performans_skoru": round(skor_bilgisi["skor"], 2),
                "tamamlanan_gorev": calisan.tamamlanan_gorev_sayisi,
                "tamamlanamayan_gorev": calisan.tamamlanamayan_gorev_sayisi,
            }
            # Eğer çalışan analizleri geçildiyse detaylı metrikleri ekle
            if calisan_analizleri and i < len(calisan_analizleri):
                analiz = calisan_analizleri[i]
                metrik.update({
                    "tamamlanma_orani": analiz.get("tamamlanma_orani", 0),
                    "verimlilik_skoru": analiz.get("verimlilik_skoru", 0),
                    "deadline_uyum_skoru": analiz.get("deadline_uyum_skoru"),
                    "zorluk_basari_dengesi": analiz.get("zorluk_basari_dengesi", 0),
                    "mesai_kullanim_orani": analiz.get("mesai_kullanim_orani", 0),
                })
            sonuc.append(metrik)
        return sonuc