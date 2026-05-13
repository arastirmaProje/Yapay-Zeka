from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ZorlukSeviyesi(str, Enum):
    COK_KOLAY = "çok kolay"
    KOLAY = "kolay"
    ORTA = "orta"
    ZOR = "zor"
    COK_ZOR = "çok zor"


class GorevDurumu(str, Enum):
    TAMAMLANDI = "Tamamlandı"
    KAPATILDI = "Kapatıldı"
    SURESI_GECTI = "Süresi Geçti"
    BEKLEMEDE = "Beklemede"


class GorevDetayiModel(BaseModel):
    id: UUID = Field(..., description="Görevin benzersiz ID'si")
    gorev_adi: str = Field(..., description="Görevin başlığı / adı")
    zorluk_seviyesi: ZorlukSeviyesi = Field(..., description="Görevin zorluk seviyesi")
    durum: GorevDurumu = Field(..., description="Görevin mevcut durumu")
    baslangic_tarihi: datetime = Field(..., description="Göreve başlanılan tarih-saat")
    bitistarihi: datetime = Field(..., description="Görev bitiş tarih-saat")
    aciklama: Optional[str] = Field(None, description="Göreve dair ek açıklama")
    geri_donut: Optional[str] = Field(None, description="Yönetici geri bildirimi")


# ── Bireysel Performans Modelleri ─────────────────────────────────────────────

class PerformansIstegi(BaseModel):
    calisan_id: UUID = Field(..., description="Çalışanın benzersiz ID'si")
    ad_soyad: str = Field(..., description="Çalışanın adı soyadı")
    tamamlanan_gorev_sayisi: int = Field(..., ge=0)
    tamamlanamayan_gorev_sayisi: int = Field(..., ge=0)
    hedeflenen_mesai_saati: float = Field(..., ge=0, description="Aylık hedef mesai (saat)")
    gerceklesen_mesai_saati: float = Field(..., ge=0, description="Aylık gerçekleşen mesai (saat)")
    kullanilan_izin_gunu: int = Field(..., ge=0)
    onceki_performans_skoru: Optional[float] = Field(None, ge=0, le=100)
    gorevler: List[GorevDetayiModel] = Field(default_factory=list)


class PerformansRaporu(BaseModel):
    calisan_id: UUID
    performans_skoru: float = Field(..., ge=0, le=100)
    rapor_ozeti: str
    detayli_rapor: str
    grafik_verisi: Optional[Dict[str, Any]] = None
    onceki_raporlar: Optional[List[str]] = None


class TopluPerformansSkoru(BaseModel):
    calisan_id: UUID
    ad_soyad: str
    performans_skoru: float = Field(..., ge=0, le=100)


class TopluPerformansSkorlari(BaseModel):
    toplam_calisan: int
    skorlar: List[TopluPerformansSkoru]


# ── Departman Modelleri ───────────────────────────────────────────────────────

class DepartmanCalisaniIstegi(BaseModel):
    calisan_id: UUID
    ad_soyad: str
    tamamlanan_gorev_sayisi: int = Field(..., ge=0)
    tamamlanamayan_gorev_sayisi: int = Field(..., ge=0)
    hedeflenen_mesai_saati: float = Field(..., ge=0)
    gerceklesen_mesai_saati: float = Field(..., ge=0)
    kullanilan_izin_gunu: int = Field(..., ge=0)
    onceki_performans_skoru: Optional[float] = Field(None, ge=0, le=100)
    gorevler: List[GorevDetayiModel] = Field(default_factory=list)


class DepartmanIstegi(BaseModel):

    departman_id: UUID = Field(..., description="Departmanın benzersiz ID'si")
    departman_adi: str = Field(..., description="Departman adı")
    calisanlar: List[DepartmanCalisaniIstegi] = Field(..., min_length=1)


class CalisanSkorOzeti(BaseModel):
    calisan_id: UUID
    ad_soyad: str
    performans_skoru: float = Field(..., ge=0, le=100)


class DepartmanRaporu(BaseModel):
    departman_id: UUID
    departman_adi: str
    departman_skoru: float = Field(..., ge=0, le=100)
    toplam_calisan: int
    calisan_skorlari: List[CalisanSkorOzeti]
    rapor_ozeti: str
    detayli_rapor: str
    grafik_verisi: Optional[Dict[str, Any]] = None


# ── Çoklu Departman Karşılaştırma Modelleri ──────────────────────────────────

class CokluDepartmanGrafik(BaseModel):
    """Birden fazla departmanın grafik karşılaştırma verilerini döner."""
    toplam_departman: int = Field(..., description="Karşılaştırmaya dahil edilen departman sayısı")
    grafik_verisi: Dict[str, Any] = Field(..., description="Tüm karşılaştırma grafik verileri")