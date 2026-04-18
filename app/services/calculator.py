from pathlib import Path
from typing import Dict, Any, Tuple
import joblib
import pandas as pd
from app.models import PerformansIstegi

class PerformansHesaplayici:

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


    def _zorluk_ortalama(self, istek: PerformansIstegi) -> float:
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

    # ek metrikler ────────────────────────────────────────────────

    def verimlilik_skoru_hesapla(self, istek: PerformansIstegi) -> float:
        """
        Birim saatte tamamlanan görev sayısı → 0-100 arası normalize edilmiş skor.
        Referans: saatte 0.5 görev = 100 puan
        """
        if istek.gerceklesen_mesai_saati <= 0:
            return 0.0
        gph = istek.tamamlanan_gorev_sayisi / istek.gerceklesen_mesai_saati
        return min(100.0, (gph / 0.5) * 100)

    def deadline_uyum_skoru_hesapla(self, istek: PerformansIstegi) -> float:
        """
        Tamamlanan görevlerin başlangıç→bitiş süresine bakarak
        zamanında teslim edilip edilmediğini ölçer.
        Şimdilik: tamamlanan / toplam * 100 (ilerleyen aşamada planlanan_sure eklenebilir)
        """
        tamamlanan = [g for g in istek.gorevler if g.durum.value == "Tamamlandı"]
        toplam = len(istek.gorevler)
        if toplam == 0:
            return 50.0  # veri yoksa nötr
        return (len(tamamlanan) / toplam) * 100

    def zorluk_basari_dengesi_hesapla(self, istek: PerformansIstegi) -> float:
        """
        Zor görevlerdeki başarı oranını ölçer.
        Zor/çok zor görevleri tamamlamak daha fazla ağırlık taşır.
        """
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
        return (kazanilan_agirlik / toplam_agirlik) * 100

    def analiz_ozeti_getir(self, istek: PerformansIstegi) -> Dict[str, Any]:
        """
        Tüm ek metrikleri dict olarak döndürür — generator.py'a iletilir.
        """
        tamamlanan = istek.tamamlanan_gorev_sayisi
        tamamlanamayan = istek.tamamlanamayan_gorev_sayisi
        toplam = max(tamamlanan + tamamlanamayan, 1)

        return {
            "tamamlanma_orani": round((tamamlanan / toplam) * 100, 1),
            "verimlilik_skoru": round(self.verimlilik_skoru_hesapla(istek), 1),
            "deadline_uyum_skoru": round(self.deadline_uyum_skoru_hesapla(istek), 1),
            "zorluk_basari_dengesi": round(self.zorluk_basari_dengesi_hesapla(istek), 1),
            "mesai_kullanim_orani": round(
                (istek.gerceklesen_mesai_saati / istek.hedeflenen_mesai_saati * 100)
                if istek.hedeflenen_mesai_saati > 0 else 0, 1
            ),
            "ortalama_zorluk": round(self._zorluk_ortalama(istek), 2),
        }

    def _hazirla_feature_vektor(self, istek: PerformansIstegi) -> Dict[str, Any]:
        hedeflenen_haftalik = float(istek.hedeflenen_mesai_saati)
        hedeflenen_gunluk = hedeflenen_haftalik / 5
        gerceklesen_haftalik = float(istek.gerceklesen_mesai_saati)
        gerceklesen_gunluk = gerceklesen_haftalik / 5
        tamamlanan = int(istek.tamamlanan_gorev_sayisi)
        tamamlanamayan = int(istek.tamamlanamayan_gorev_sayisi)
        zorluk_encoded = self._zorluk_ortalama(istek)
        toplam_gorev = max(tamamlanan + tamamlanamayan, 1)
        tamamlanma_orani = tamamlanan / toplam_gorev
        mesai_sapmasi_mutlak = abs(hedeflenen_haftalik - gerceklesen_haftalik)
        izin_esik_ustu = max(0, int(istek.kullanilan_izin_gunu) - 5)

        return {
            "hedeflenen_gunluk_mesai_saati": hedeflenen_gunluk,
            "hedeflenen_haftalik_mesai_saati": hedeflenen_haftalik,
            "gerceklesen_gunluk_mesai_saati": gerceklesen_gunluk,
            "gerceklesen_haftalik_mesai_saati": gerceklesen_haftalik,
            "tamamlanan_gorev_sayisi": tamamlanan,
            "tamamlanamayan_gorev_sayisi": tamamlanamayan,
            "zorluk_seviyesi_encoded": zorluk_encoded,
            "tamamlanma_orani": tamamlanma_orani,
            "mesai_sapmasi_mutlak": mesai_sapmasi_mutlak,
            "izin_esik_ustu": izin_esik_ustu,
        }

    def hesapla(self, istek: PerformansIstegi) -> float:
        feature_vektor = self._hazirla_feature_vektor(istek)
        df = pd.DataFrame([feature_vektor])
        df = df.reindex(columns=self.feature_names, fill_value=0)
        model_skor = float(self.model.predict(df)[0])
        mesai_bonus_ceza = self._mesai_bonus_ceza_hesapla(
            istek.hedeflenen_mesai_saati,
            istek.gerceklesen_mesai_saati
        )
        return max(0.0, min(100.0, model_skor + mesai_bonus_ceza))