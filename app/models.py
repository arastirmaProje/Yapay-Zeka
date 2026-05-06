from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Dict, Any
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
    KAPATILDI = "Kapatıldı"
    TAMAMLANMADI = "Tamamlanmadı"
    SURESI_GECTI = "Süresi Geçti"
    BEKLEMEDE = "Beklemede"
    DEVAM_EDIYOR = "Devam ediyor"

class BeklemeTuru(str, Enum):
    """Sadece Beklemede durumundaki görevler için Gemini tarafından belirlenir."""
    KISI_KAYNAKLI = "Kişi Kaynaklı"      #kişinin kendinden kaynaklı hatalar negatif 
    SISTEM_KAYNAKLI = "Sistem Kaynaklı"  #başka task tamamlanmadan yeni task başlanamaması nötr
    DIS_FAKTOR = "Dış Faktör"       #onay bekleme , müşteri kaynaklı gecikme nötr
    
    
class GorevDetayiModel(BaseModel):
    """
    Çalışanın tek bir göreviyle ilgili detaylar.
    """
    id: UUID = Field(..., description="Görevin benzersiz ID'si (UUID)")
    gorev_adi: str = Field(..., description="Görevin başlığı / adı")
    zorluk_seviyesi: ZorlukSeviyesi = Field(..., description="Görevin zorluk seviyesi")
    durum: GorevDurumu = Field(..., description="Görevin mevcut durumu")
    baslangic_tarihi: datetime = Field(..., description="Göreve başlanılan tarih-saat")
    bitistarihi: datetime = Field(..., description="Görev tamamlandıysa bitiş tarih-saat")
    aciklama: Optional[str] = Field(None, description="Göreve dair ek açıklama / notlar")
    geri_donut: Optional[str] = Field(None, description="Yönetici veya müşteri geri bildirimi")


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

    onceki_performans_skoru: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Bir önceki dönem performans skoru (karşılaştırma grafiği için)"
    )

    gorevler: List[GorevDetayiModel] = Field(
        default_factory=list,
        description="Çalışanın ilgili dönemdeki görevleri"
    )


class PerformansRaporu(BaseModel):
    """
    Hesaplanan skor ve LLM tarafından üretilen rapor çıktısı.
    """
    calisan_id: UUID = Field(..., description="Çalışanın benzersiz ID'si (UUID)")
    performans_skoru: float = Field(..., ge=0, le=100, description="0-100 arası skor")
    rapor_ozeti: str = Field(..., description="Kısa özet / maddeler")
    detayli_rapor: str = Field(..., description="Detaylı metin raporu")
    grafik_verisi: Optional[Dict[str, Any]] = Field(
        None,
        description="Mobil grafik verileri (mesai, performans karşılaştırma, metrikler)"
    )
    onceki_raporlar: Optional[List[str]] = Field(
        None, description="Varsa geçmiş rapor referansları/özetleri"
    )


class TopluPerformansSkoru(BaseModel):
    """
    Toplu sorgu için sadece performans skoru.
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
    
class DepartmanCalisaniIstegi(BaseModel):
    '''Departman sorgusundaki her bir çalışan için gereken bilgiler'''
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

class Departmanİstegi(BaseModel):
    '''Departman sorgusu için gereken bilgiler'''
    departman_id: UUID = Field(..., description="Departmanın benzersiz ID'si (UUID)")
    departman_adi: str = Field(..., description="Departmanın adı")
    calisanlar: List[DepartmanCalisaniIstegi] = Field(
        default_factory=list,
        description="Departmandaki çalışanların listesi"
    )
    
class CalisanPerformansSkoru(BaseModel):
    '''Çalışan performans skorunu ve analizlerini içeren model'''
    calisan_id: UUID = Field(..., description="Çalışanın benzersiz ID'si (UUID)")
    ad_soyad: str = Field(..., description="Çalışanın adı soyadı")
    performans_skoru: float = Field(..., ge=0, le=100, description="0-100 arası skor")
    analiz_ozeti: Dict[str, Any] = Field(
        default_factory=dict,
        description="Ek metrikler ve analiz sonuçları (verimlilik, deadline uyumu, zorluk dengesi vb.)"
    )

class DepartmanPerformansRaporu(BaseModel):
    '''Departman performans raporu modeli'''
    departman_id: UUID = Field(..., description="Departmanın benzersiz ID'si (UUID)")
    departman_adi: str = Field(..., description="Departmanın adı")
    departman_skoru: float = Field(..., ge=0, le=100, description="0-100 arası departman skoru")
    toplam_calisan: int = Field(..., description="Departmandaki toplam çalışan sayısı")
    calisan_skorlari: List[CalisanPerformansSkoru] = Field(
        default_factory=list,
        description="Departmandaki her bir çalışanın performans skorları ve analiz özetleri"
    )
    rapor_ozeti: str = Field(..., description="Departman performans raporu özeti")
    detayli_rapor: str = Field(..., description="Departman performans raporu detaylı metni")
    grafik_verisi: Optional[Dict[str, Any]] = Field(
        None,
        description="Departman performansını görselleştirmek için grafik verileri (örneğin, çalışan skor dağılımı, metrik karşılaştırmaları)"
    )

class GorevAnalizİstegi(BaseModel):
    '''Görev detaylarını analiz ederek performans skoruna ekler'''
    gorev_id: UUID = Field(..., description="Görevin benzersiz ID'si (UUID)")
    gorev_adi: str = Field(..., description="Görevin başlığı / adı")
    zorluk_seviyesi: ZorlukSeviyesi = Field(..., description="Görevin zorluk seviyesi")
    durum: GorevDurumu = Field(..., description="Görevin mevcut durumu")
    aciklama: Optional[str] = Field(None, description="Göreve dair ek açıklama / notlar")
    geri_donut: Optional[str] = Field(None, description="Yönetici veya müşteri geri bildirimi")
    baslangic_tarihi: datetime = Field(..., description="Göreve başlanılan tarih-saat")
    bitis_tarihi: Optional[datetime] = Field(None, description="Görev tamamlandıysa bitiş tarih-saat")

class GorevAnalizSonucu(BaseModel):
    '''Görev analizinden elde edilen skor etkisi ve geri bildirim'''
    gorev_id: UUID = Field(..., description="Görevin benzersiz ID'si (UUID)")
    durum: GorevDurumu
    bekleme_turu: Optional[BeklemeTuru] = Field(
        None,
        description="Sadece Beklemede durumunda dolar: kisi_kaynakli / sistem_kaynakli / dis_faktor"
    )
    performans_bonus_cezasi: float = Field(..., description="Bu görevin performans skoruna etkisi (nötr veya negatif ceza)")
    yapay_zeka_geri_bildirimi: str = Field(..., description="Yapay zeka tarafından üretilen görevle ilgili geri bildirim")