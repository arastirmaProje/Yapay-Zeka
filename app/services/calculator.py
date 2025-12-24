from pathlib import Path
from typing import Dict, Any
import sys
import joblib
import pandas as pd
from app.models import PerformansIstegi

class PerformansHesaplayici:
    """
    Eğitilmiş model ile çalışan performans skorunu hesaplar.
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

    def _zorluk_ortalama(self, istek: PerformansIstegi) -> float:
        if not istek.gorevler:
            return 3.0

        encoded = [
            self.zorluk_haritasi.get(gorev.zorluk_seviyesi.lower(), 3)
            for gorev in istek.gorevler
        ]
        return sum(encoded) / len(encoded)

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

        features = {
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
        return features

    def hesapla(self, istek: PerformansIstegi) -> float:
        """
        Performans skorunu 0-100 arasında döndürür.
        """
        feature_vektor = self._hazirla_feature_vektor(istek)

        df = pd.DataFrame([feature_vektor])
        df = df.reindex(columns=self.feature_names, fill_value=0)

        skor = float(self.model.predict(df)[0])
        return max(0.0, min(100.0, skor))
