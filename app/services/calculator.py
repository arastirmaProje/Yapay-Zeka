from pathlib import Path
from typing import Dict, Any, Optional, List
from statistics import mean
import joblib
import pandas as pd


class PerformansHesaplayici:
    """
    Eğitilmiş model ile çalışan ve departman performans skorlarını hesaplar.
    """

    def __init__(self, model_path: str = "performans_model.pkl") -> None:
        base_dir = Path(__file__).resolve().parents[2]
        self.model_path = (base_dir / model_path) if not Path(model_path).is_absolute() else Path(model_path)
        self.feature_names_path = base_dir / "feature_names.pkl"
        self.zorluk_haritasi_path = base_dir / "zorluk_haritasi.pkl"

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model dosyası bulunamadı: {self.model_path}")
        self.model = joblib.load(self.model_path)

        if not self.feature_names_path.exists():
            raise FileNotFoundError(f"Feature listesi bulunamadı: {self.feature_names_path}")
        self.feature_names = joblib.load(self.feature_names_path)

        if not self.zorluk_haritasi_path.exists():
            raise FileNotFoundError(f"Zorluk haritası bulunamadı: {self.zorluk_haritasi_path}")
        self.zorluk_haritasi = joblib.load(self.zorluk_haritasi_path)

    # ── Yardımcı metodlar ─────────────────────────────────────────────────

    def _zorluk_ortalama(self, istek) -> float:
        if not istek.gorevler:
            return 3.0
        encoded = [
            self.zorluk_haritasi.get(gorev.zorluk_seviyesi.lower(), 3)
            for gorev in istek.gorevler
        ]
        return sum(encoded) / len(encoded)

    def _mesai_bonus_ceza_hesapla(self, hedeflenen: float, gerceklesen: float) -> float:
        if hedeflenen <= 0:
            return 0.0
        yuzde_oran = (gerceklesen / hedeflenen) * 100
        if 125.0 <= yuzde_oran <= 150.0:
            return min(5.0, 2.0 + ((yuzde_oran - 125.0) / 25.0) * 3.0)
        elif yuzde_oran > 150.0:
            return max(-10.0, -((min(yuzde_oran, 200.0) - 150.0) / 50.0) * 10.0)
        return 0.0

    def _gorev_sayilari_dogrula(self, istek) -> tuple:
        """
        gorevler listesindeki durum bilgilerini kontrol ederek
        tamamlanan/tamamlanamayan sayılarını doğrular.
        Backend'den 0 gelse bile gorevler listesinde tamamlanmış görev
        varsa gerçek sayıları kullanır.
        """
        tamamlanan = istek.tamamlanan_gorev_sayisi
        tamamlanamayan = istek.tamamlanamayan_gorev_sayisi

        if not istek.gorevler:
            return tamamlanan, tamamlanamayan

        gorevden_tamamlanan = sum(
            1 for g in istek.gorevler if g.durum.value == "Tamamlandı"
        )
        gorevden_tamamlanamayan = sum(
            1 for g in istek.gorevler
            if g.durum.value in ("Süresi Geçti", "Kapatıldı")
        )

        # Sayılar tutarsızsa gorevler listesindeki gerçek verileri kullan
        if tamamlanan == 0 and gorevden_tamamlanan > 0:
            tamamlanan = gorevden_tamamlanan
        if tamamlanamayan == 0 and gorevden_tamamlanamayan > 0:
            tamamlanamayan = gorevden_tamamlanamayan

        return tamamlanan, tamamlanamayan

    # ── Bireysel metrikler ────────────────────────────────────────────────

    def verimlilik_skoru_hesapla(self, istek) -> float:
        tamamlanan, _ = self._gorev_sayilari_dogrula(istek)
        if istek.gerceklesen_mesai_saati <= 0:
            return 0.0
        gph = tamamlanan / istek.gerceklesen_mesai_saati
        return min(100.0, (gph / 0.5) * 100)

    def deadline_uyum_skoru_hesapla(self, istek) -> Optional[float]:
        """Görev verisi yoksa None döner."""
        toplam = len(istek.gorevler)
        if toplam == 0:
            return None
        tamamlanan = [g for g in istek.gorevler if g.durum.value == "Tamamlandı"]
        return round((len(tamamlanan) / toplam) * 100, 1)

    def zorluk_basari_dengesi_hesapla(self, istek) -> float:
        if not istek.gorevler:
            return 50.0
        zorluk_agirlik = {"çok kolay": 1, "kolay": 2, "orta": 3, "zor": 4, "çok zor": 5}
        toplam_agirlik = 0.0
        kazanilan_agirlik = 0.0
        for gorev in istek.gorevler:
            agirlik = zorluk_agirlik.get(gorev.zorluk_seviyesi.lower(), 3)
            toplam_agirlik += agirlik
            if gorev.durum.value == "Tamamlandı":
                kazanilan_agirlik += agirlik
        if toplam_agirlik == 0:
            return 50.0
        return round((kazanilan_agirlik / toplam_agirlik) * 100, 1)

    def analiz_ozeti_getir(self, istek) -> Dict[str, Any]:
        tamamlanan, tamamlanamayan = self._gorev_sayilari_dogrula(istek)
        toplam = max(tamamlanan + tamamlanamayan, 1)
        return {
            "tamamlanma_orani": round((tamamlanan / toplam) * 100, 1),
            "verimlilik_skoru": round(self.verimlilik_skoru_hesapla(istek), 1),
            "deadline_uyum_skoru": self.deadline_uyum_skoru_hesapla(istek),
            "zorluk_basari_dengesi": self.zorluk_basari_dengesi_hesapla(istek),
            "mesai_kullanim_orani": round(
                (istek.gerceklesen_mesai_saati / istek.hedeflenen_mesai_saati * 100)
                if istek.hedeflenen_mesai_saati > 0 else 0.0, 1
            ),
            "ortalama_zorluk": round(self._zorluk_ortalama(istek), 2),
        }

    def _hazirla_feature_vektor(self, istek) -> Dict[str, Any]:
        hedeflenen = float(istek.hedeflenen_mesai_saati)
        gerceklesen = float(istek.gerceklesen_mesai_saati)
        tamamlanan_raw, tamamlanamayan_raw = self._gorev_sayilari_dogrula(istek)
        tamamlanan = int(tamamlanan_raw)
        tamamlanamayan = int(tamamlanamayan_raw)
        toplam_gorev = max(tamamlanan + tamamlanamayan, 1)
        return {
            "hedeflenen_gunluk_mesai_saati": hedeflenen / 5,
            "hedeflenen_haftalik_mesai_saati": hedeflenen,
            "gerceklesen_gunluk_mesai_saati": gerceklesen / 5,
            "gerceklesen_haftalik_mesai_saati": gerceklesen,
            "tamamlanan_gorev_sayisi": tamamlanan,
            "tamamlanamayan_gorev_sayisi": tamamlanamayan,
            "zorluk_seviyesi_encoded": self._zorluk_ortalama(istek),
            "tamamlanma_orani": tamamlanan / toplam_gorev,
            "mesai_sapmasi_mutlak": abs(hedeflenen - gerceklesen),
            "izin_esik_ustu": max(0, int(istek.kullanilan_izin_gunu) - 5),
        }

    def hesapla(self, istek) -> float:
        df = pd.DataFrame([self._hazirla_feature_vektor(istek)])
        df = df.reindex(columns=self.feature_names, fill_value=0)
        model_skor = float(self.model.predict(df)[0])
        bonus_ceza = self._mesai_bonus_ceza_hesapla(
            istek.hedeflenen_mesai_saati,
            istek.gerceklesen_mesai_saati
        )
        return max(0.0, min(100.0, model_skor + bonus_ceza))

    # ── Departman metodları ───────────────────────────────────────────────

    def departman_skoru_hesapla(
        self,
        calisan_skorlari: List[float],
        calisan_analizleri: List[Dict[str, Any]],
    ) -> float:
        """
        Ağırlıklı departman skoru:
          Performans skoru  %40
          Tamamlanma oranı  %25
          Zorluk/Başarı     %20
          Mesai kullanımı   %15
        """
        skor = (
            mean(calisan_skorlari) * 0.40 +
            mean([a["tamamlanma_orani"] for a in calisan_analizleri]) * 0.25 +
            mean([a["zorluk_basari_dengesi"] for a in calisan_analizleri]) * 0.20 +
            mean([min(100.0, a["mesai_kullanim_orani"]) for a in calisan_analizleri]) * 0.15
        )
        return round(min(100.0, max(0.0, skor)), 2)

    def departman_analizi_getir(
        self,
        calisan_analizleri: List[Dict[str, Any]],
        calisan_skorlari: List[float],
    ) -> Dict[str, Any]:
        deadline_skorlari = [
            a["deadline_uyum_skoru"]
            for a in calisan_analizleri
            if a["deadline_uyum_skoru"] is not None
        ]
        return {
            "ortalama_performans_skoru": round(mean(calisan_skorlari), 2),
            "en_yuksek_skor": round(max(calisan_skorlari), 2),
            "en_dusuk_skor": round(min(calisan_skorlari), 2),
            "ortalama_tamamlanma_orani": round(mean([a["tamamlanma_orani"] for a in calisan_analizleri]), 1),
            "ortalama_verimlilik": round(mean([a["verimlilik_skoru"] for a in calisan_analizleri]), 1),
            "ortalama_deadline_uyumu": round(mean(deadline_skorlari), 1) if deadline_skorlari else None,
            "ortalama_zorluk_basari": round(mean([a["zorluk_basari_dengesi"] for a in calisan_analizleri]), 1),
            "ortalama_mesai_kullanimi": round(mean([a["mesai_kullanim_orani"] for a in calisan_analizleri]), 1),
        }