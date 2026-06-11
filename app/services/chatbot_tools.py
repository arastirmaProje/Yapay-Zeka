"""
Chatbot Tool Tanımları
─────────────────────
Gemini 2.5 Flash'ın function calling ile çağırabileceği tool'lar.
Her fonksiyonun açık docstring'i ve type hint'leri Gemini'nin
tool'u doğru zamanda çağırmasını sağlar.

NOT: Backend entegrasyonu gerektiren tool'lar (görev oluştur, izin talebi vs.)
şu anda STUB olarak çalışır. Gerçek backend API'leri hazır olduğunda
bu fonksiyonlar HTTP proxy çağrılarına dönüştürülecektir.
"""

from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# PERSONEL TOOL'LARI — Çalışanın kendi verileriyle etkileşim
# ══════════════════════════════════════════════════════════════════════════════


def performans_sorgula(calisan_id: str) -> dict:
    """Çalışanın güncel performans skorunu ve metriklerini getirir.

    Args:
        calisan_id: Çalışanın benzersiz kimlik numarası.

    Returns:
        Performans skoru, genel durum ve temel metrikleri içeren sözlük.
    """
    # STUB: Gerçek implementasyonda PerformansHesaplayici kullanılacak.
    # Şimdilik backend'den veri gelmediği için örnek veri dönüyoruz.
    return {
        "calisan_id": calisan_id,
        "performans_skoru": 0,
        "genel_durum": "Veri bekleniyor",
        "mesaj": (
            "Bu fonksiyon şu anda stub olarak çalışmaktadır. "
            "Gerçek performans verisi için backend entegrasyonu gereklidir. "
            "Çalışanın performans verileri backend API'sinden alınacaktır."
        ),
    }


def gorev_listele(calisan_id: str, durum: Optional[str] = None) -> dict:
    """Çalışanın görevlerini listeler. İsteğe bağlı olarak duruma göre filtreler.

    Args:
        calisan_id: Çalışanın benzersiz kimlik numarası.
        durum: Görev durumu filtresi. Örnek: Tamamlandı, Beklemede, Süresi Geçti.
              Belirtilmezse tüm görevler listelenir.

    Returns:
        Görev listesi ve özet bilgiler.
    """
    # STUB: Backend entegrasyonu ile gerçek görev verileri gelecek
    return {
        "calisan_id": calisan_id,
        "filtre": durum,
        "gorevler": [],
        "toplam_gorev": 0,
        "mesaj": (
            "Bu fonksiyon şu anda stub olarak çalışmaktadır. "
            "Gerçek görev verileri backend API'sinden alınacaktır."
        ),
    }


def izin_talebi_olustur(
    calisan_id: str,
    baslangic: str,
    bitis: str,
    neden: str,
) -> dict:
    """Çalışan adına izin talebi oluşturur.

    Args:
        calisan_id: Çalışanın benzersiz kimlik numarası.
        baslangic: İzin başlangıç tarihi. Örnek: 2026-01-15
        bitis: İzin bitiş tarihi. Örnek: 2026-01-17
        neden: İzin talebi nedeni. Örnek: Yıllık izin

    Returns:
        Oluşturulan izin talebinin durumu ve detayları.
    """
    # STUB: Backend entegrasyonu ile gerçek izin talebi oluşturulacak
    return {
        "calisan_id": calisan_id,
        "baslangic": baslangic,
        "bitis": bitis,
        "neden": neden,
        "durum": "beklemede",
        "mesaj": (
            "İzin talebiniz oluşturuldu ve yönetici onayına gönderildi. "
            "(Bu fonksiyon şu anda stub olarak çalışmaktadır.)"
        ),
    }


def performans_gecmisi(calisan_id: str) -> dict:
    """Çalışanın önceki dönemlerdeki performans skorlarını ve değişim trendini gösterir.

    Args:
        calisan_id: Çalışanın benzersiz kimlik numarası.

    Returns:
        Dönemsel performans skorları ve trend bilgisi.
    """
    # STUB: Backend entegrasyonu ile gerçek geçmiş veriler gelecek
    return {
        "calisan_id": calisan_id,
        "gecmis_skorlar": [],
        "trend": "veri_yok",
        "mesaj": (
            "Bu fonksiyon şu anda stub olarak çalışmaktadır. "
            "Gerçek performans geçmişi backend API'sinden alınacaktır."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# YÖNETİCİ EK TOOL'LARI — Departman yönetimi ve ekip analizi
# ══════════════════════════════════════════════════════════════════════════════


def departman_performans(departman_id: str) -> dict:
    """Departmanın genel performans özetini getirir.
    Ortalama skor, en iyi ve en düşük performans gibi bilgileri içerir.

    Args:
        departman_id: Departmanın benzersiz kimlik numarası.

    Returns:
        Departman performans özeti.
    """
    # STUB: Backend entegrasyonu ile gerçek departman verileri gelecek
    return {
        "departman_id": departman_id,
        "departman_skoru": 0,
        "calisan_sayisi": 0,
        "mesaj": (
            "Bu fonksiyon şu anda stub olarak çalışmaktadır. "
            "Gerçek departman verileri backend API'sinden alınacaktır."
        ),
    }


def calisan_karsilastir(departman_id: str) -> dict:
    """Departmandaki çalışanların performanslarını karşılaştırır.
    En yüksek ve en düşük performanslı çalışanları listeler.

    Args:
        departman_id: Departmanın benzersiz kimlik numarası.

    Returns:
        Çalışan karşılaştırma tablosu.
    """
    # STUB: Backend entegrasyonu ile gerçek karşılaştırma verileri gelecek
    return {
        "departman_id": departman_id,
        "karsilastirma": [],
        "mesaj": (
            "Bu fonksiyon şu anda stub olarak çalışmaktadır. "
            "Gerçek karşılaştırma verileri backend API'sinden alınacaktır."
        ),
    }


def gorev_olustur(
    calisan_id: str,
    gorev_adi: str,
    zorluk: str,
    bitis_tarihi: str,
) -> dict:
    """Belirtilen çalışana yeni bir görev oluşturur ve atar.

    Args:
        calisan_id: Görevin atanacağı çalışanın benzersiz kimlik numarası.
        gorev_adi: Görevin başlığı veya kısa açıklaması.
        zorluk: Görev zorluk seviyesi. Seçenekler: çok kolay, kolay, orta, zor, çok zor
        bitis_tarihi: Görevin tamamlanması gereken son tarih. Örnek: 2026-01-20

    Returns:
        Oluşturulan görevin detayları.
    """
    # STUB: Backend entegrasyonu ile gerçek görev oluşturulacak
    return {
        "calisan_id": calisan_id,
        "gorev_adi": gorev_adi,
        "zorluk": zorluk,
        "bitis_tarihi": bitis_tarihi,
        "durum": "olusturuldu",
        "mesaj": (
            f"'{gorev_adi}' görevi oluşturuldu ve çalışana atandı. "
            "(Bu fonksiyon şu anda stub olarak çalışmaktadır.)"
        ),
    }


def departman_raporu_iste(departman_id: str) -> dict:
    """Departman için yapay zeka destekli detaylı performans raporu oluşturur.

    Args:
        departman_id: Raporun oluşturulacağı departmanın benzersiz kimlik numarası.

    Returns:
        Rapor oluşturma durumu ve detayları.
    """
    # STUB: Backend entegrasyonu ile gerçek rapor verisi alınacak,
    # ardından PerformanceReportGenerator ile rapor üretilecek
    return {
        "departman_id": departman_id,
        "durum": "olusturuluyor",
        "mesaj": (
            "Departman raporu oluşturma talebi alındı. "
            "(Bu fonksiyon şu anda stub olarak çalışmaktadır.)"
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# TOOL LİSTELERİ — ChatbotService tarafından kullanılır
# ══════════════════════════════════════════════════════════════════════════════

PERSONEL_TOOLS = [
    performans_sorgula,
    gorev_listele,
    izin_talebi_olustur,
    performans_gecmisi,
]

YONETICI_TOOLS = [
    # Personel tool'larının tamamı
    performans_sorgula,
    gorev_listele,
    izin_talebi_olustur,
    performans_gecmisi,
    # Yönetici ek tool'ları
    departman_performans,
    calisan_karsilastir,
    gorev_olustur,
    departman_raporu_iste,
]
