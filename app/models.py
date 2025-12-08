from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class GorevDetayiModel(BaseModel):
    id: int
    gorev_adi: str
    zorluk_seviyesi: str
    durum: str #örn: tamamlandi, devam ediyor
    baslangic_tarihi: datetime
    bitistarihi: datetime
    aciklama: Optional[str] = None
    geri_donut: Optional[str] = None

class PerformansIstegi(BaseModel): 
    calisan_id: int
    ad_soyad: str
    tamamlanan_gorev_sayisi: int
    tamamlanamayan_gorev_sayisi: int
    hedeflenen_mesai_saati: float
    gerceklesen_mesai_saati: float
    kullanilan_izin_gunu: int #yıllık
    gorevler: List[GorevDetayiModel]

class PerformansRaporu(BaseModel):
    calisan_id: int
    performans_skoru: float
    rapor_ozeti: str
    detayli_rapor: str
    onceki_raporlar: Optional[List[str]] = None