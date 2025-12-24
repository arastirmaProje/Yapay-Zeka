from datetime import datetime, date
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ZorlukSeviyesi(str, Enum):
    COK_KOLAY = "çok kolay"
    KOLAY = "kolay"
    ORTA = "orta"
    ZOR = "zor"
    COK_ZOR = "çok zor"


class GorevDurumu(str, Enum):
    TAMAMLANDI = "Tamamlandı"
    TAMAMLANMADI = "Tamamlanmadı"
    DEVAM_EDIYOR = "Devam ediyor"


class GorevDetayiModel(BaseModel):
    """
    Çalışanın tek bir göreviyle ilgili detaylar.
    """

    id: int = Field(..., description="Görevin benzersiz ID'si")
    gorev_adi: str = Field(..., description="Görevin başlığı / adı")
    zorluk_seviyesi: ZorlukSeviyesi = Field(
        ..., description="Görevin zorluk seviyesi"
    )
    durum: GorevDurumu = Field(
        ..., description="Görevin mevcut durumu"
    )
    baslangic_tarihi: datetime = Field(
        ..., description="Göreve başlanılan tarih-saat"
    )
    bitistarihi: datetime = Field(
        ..., description="Görev tamamlandıysa bitiş tarih-saat"
    )
    aciklama: Optional[str] = Field(
        None, description="Göreve dair ek açıklama / notlar"
    )
    geri_donut: Optional[str] = Field(
        None, description="Yönetici veya müşteri geri bildirimi"
    )


class PerformansIstegi(BaseModel):
    """
    Performans hesaplama isteği (API input).
    """

    calisan_id: UUID = Field(..., description="Çalışanın benzersiz ID'si (UUID)")
    ad_soyad: str = Field(..., description="Çalışanın adı soyadı")

    tamamlanan_gorev_sayisi: int = Field(..., ge=0)
    tamamlanamayan_gorev_sayisi: int = Field(..., ge=0)
    hedeflenen_mesai_saati: float = Field(..., ge=0, description="Haftalık hedef mesai")
    gerceklesen_mesai_saati: float = Field(..., ge=0, description="Haftalık gerçekleşen mesai")
    kullanilan_izin_gunu: int = Field(..., ge=0, description="Yıllık izin gün sayısı")


    gorevler: List[GorevDetayiModel] = Field(
        default_factory=list,
        description="Çalışanın ilgili dönemdeki görevleri"
    )


class PerformansRaporu(BaseModel):
    """
    Hesaplanan skor ve LLM tarafından üretilen rapor çıktısı (API output).
    """

    calisan_id: UUID = Field(..., description="Çalışanın benzersiz ID'si (UUID)")
    performans_skoru: float = Field(..., ge=0, le=100, description="0-100 arası skor")
    rapor_ozeti: str = Field(..., description="Kısa özet / maddeler")
    detayli_rapor: str = Field(..., description="Detaylı metin raporu")
    onceki_raporlar: Optional[List[str]] = Field(
        None, description="Varsa geçmiş rapor referansları/özetleri"
    )


class TopluPerformansSkoru(BaseModel):
    """
    Toplu sorgu için sadece performans skoru (rapor yok).
    """

    calisan_id: UUID = Field(..., description="Çalışanın benzersiz ID'si (UUID)")
    ad_soyad: str = Field(..., description="Çalışanın adı soyadı")
    performans_skoru: float = Field(..., ge=0, le=100, description="0-100 arası skor")


class TopluPerformansSkorlari(BaseModel):
    """
    Toplu sorgu sonucu - tüm çalışanların skorları.
    """

    toplam_calisan: int = Field(..., description="Toplam işlenen çalışan sayısı")
    skorlar: List[TopluPerformansSkoru] = Field(..., description="Çalışan skorları listesi")