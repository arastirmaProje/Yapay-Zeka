"""
Chatbot Tool Tanımları
─────────────────────
Gemini 2.5 Flash'ın function calling ile çağırabileceği tool'lar.
Her fonksiyonun açık docstring'i ve type hint'leri Gemini'nin
tool'u doğru zamanda çağırmasını sağlar.

Tool fonksiyonları Gemini tarafından çağrılır. business_id ve token
parametreleri Gemini'ye gösterilmez — ChatbotService tarafından
otomatik inject edilir.
"""

from typing import Optional

from app.services import backend_client


# ══════════════════════════════════════════════════════════════════════════════
# PERSONEL TOOL'LARI — Çalışanın kendi verileriyle etkileşim
# ══════════════════════════════════════════════════════════════════════════════


async def performans_sorgula(calisan_id: str) -> dict:
    """Çalışanın sistemde kayıtlı olan EN SON (en güncel) performans skorunu getirir.
    DİKKAT: Bu araç sıfırdan yeni hesaplama YAPMAZ.
    Sadece mevcut kayıtlı skoru öğrenmek ("en sonki skorum nedir", "performansımı getir") için kullanılır.

    Args:
        calisan_id: Çalışanın benzersiz kimlik numarası.

    Returns:
        Kayıtlı en son performans raporu ve skoru.
    """
    business_id = performans_sorgula._injected.get("business_id", "")
    token = performans_sorgula._injected.get("token", "")

    result = await backend_client.performans_gecmisi_getir_api(
        business_id=business_id,
        calisan_id=calisan_id,
        token=token,
    )
    
    # API hata dönerse
    if isinstance(result, dict) and result.get("hata"):
        return result
        
    # Gelen veri liste ise en sonuncuyu alalım
    kayitlar = result.get("data") or result.get("Data") or result.get("items") or [] if isinstance(result, dict) else (result if isinstance(result, list) else [])
    if not kayitlar or len(kayitlar) == 0:
        return {"mesaj": "Sistemde henüz hesaplanmış bir performans raporunuz bulunamadı. Lütfen yeni bir performans skoru hesaplanmasını isteyin."}
        
    en_son_kayit = kayitlar[-1]
    
    return {"en_son_performans_raporu": en_son_kayit}

performans_sorgula._injected = {}


async def yeni_performans_hesapla(calisan_id: str) -> dict:
    """Çalışanın performans skorunu SIFIRDAN YENİDEN HESAPLAR ve detaylı yeni rapor oluşturur.
    Kullanıcı açıkça 'yeni performans skoru yap', 'hesapla', 'yeniden değerlendir' dediğinde kullanılır.

    Args:
        calisan_id: Çalışanın benzersiz kimlik numarası.

    Returns:
        Sıfırdan hesaplanan yeni performans skoru ve analiz raporu.
    """
    business_id = yeni_performans_hesapla._injected.get("business_id", "")
    token = yeni_performans_hesapla._injected.get("token", "")

    result = await backend_client.performans_getir(
        business_id=business_id,
        calisan_id=calisan_id,
        token=token,
    )
    return result

yeni_performans_hesapla._injected = {}


async def gorev_listele(calisan_id: str, durum: Optional[str] = None) -> dict:
    """Çalışanın görevlerini listeler. İsteğe bağlı olarak duruma göre filtreler.

    Args:
        calisan_id: Çalışanın benzersiz kimlik numarası.
        durum: Görev durumu filtresi. Örnek: Tamamlandı, Beklemede, Süresi Geçti.
              Belirtilmezse tüm görevler listelenir.

    Returns:
        Görev listesi ve özet bilgiler.
    """
    business_id = gorev_listele._injected.get("business_id", "")
    token = gorev_listele._injected.get("token", "")

    result = await backend_client.gorevleri_getir(
        business_id=business_id,
        token=token,
        calisan_id=calisan_id,
    )

    # Duruma göre filtreleme (backend tüm görevleri döndürüyorsa)
    if durum and isinstance(result, dict) and "data" in result:
        data = result.get("data")
        if isinstance(data, list):
            filtered = [
                g for g in data
                if durum.lower() in str(g.get("status", "")).lower()
            ]
            result["data"] = filtered
            result["filtre_uygulandi"] = durum

    return result

gorev_listele._injected = {}


async def izin_talebi_olustur(
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
    business_id = izin_talebi_olustur._injected.get("business_id", "")
    token = izin_talebi_olustur._injected.get("token", "")

    result = await backend_client.izin_talebi_olustur_api(
        business_id=business_id,
        baslangic=baslangic,
        bitis=bitis,
        neden=neden,
        token=token,
    )
    return result

izin_talebi_olustur._injected = {}


async def performans_gecmisi(calisan_id: str) -> dict:
    """Çalışanın önceki dönemlerdeki TÜM geçmiş performans skorlarını ve değişim trendini gösterir.
    Sıfırdan hesaplama yapmaz.

    Args:
        calisan_id: Çalışanın benzersiz kimlik numarası.

    Returns:
        Dönemsel performans skorları ve trend bilgisi listesi.
    """
    business_id = performans_gecmisi._injected.get("business_id", "")
    token = performans_gecmisi._injected.get("token", "")

    result = await backend_client.performans_gecmisi_getir_api(
        business_id=business_id,
        calisan_id=calisan_id,
        token=token,
    )
    return result

performans_gecmisi._injected = {}


# ══════════════════════════════════════════════════════════════════════════════
# YÖNETİCİ EK TOOL'LARI — Departman yönetimi ve ekip analizi
# ══════════════════════════════════════════════════════════════════════════════


async def departman_performans(departman_id: str) -> dict:
    """Departmanın genel performans özetini getirir.
    Ortalama skor, en iyi ve en düşük performans gibi bilgileri içerir.

    Args:
        departman_id: Departmanın benzersiz kimlik numarası.

    Returns:
        Departman performans özeti.
    """
    business_id = departman_performans._injected.get("business_id", "")
    token = departman_performans._injected.get("token", "")

    result = await backend_client.departman_performans_getir(
        business_id=business_id,
        departman_id=departman_id,
        token=token,
    )
    return result

departman_performans._injected = {}


async def calisan_karsilastir(departman_id: str) -> dict:
    """Departmandaki çalışanların performanslarını karşılaştırır.
    En yüksek ve en düşük performanslı çalışanları listeler.

    Args:
        departman_id: Departmanın benzersiz kimlik numarası.

    Returns:
        Çalışan karşılaştırma tablosu.
    """
    business_id = calisan_karsilastir._injected.get("business_id", "")
    token = calisan_karsilastir._injected.get("token", "")

    result = await backend_client.toplu_performans_getir(
        business_id=business_id,
        token=token,
    )
    return result

calisan_karsilastir._injected = {}


async def gorev_olustur(
    calisan_id: str,
    gorev_adi: str,
    bitis_tarihi: str,
) -> dict:
    """Belirtilen çalışana yeni bir görev oluşturur ve atar.

    Args:
        calisan_id: Görevin atanacağı çalışanın benzersiz kimlik numarası.
        gorev_adi: Görevin başlığı veya kısa açıklaması.
        bitis_tarihi: Görevin tamamlanması gereken son tarih. Örnek: 2026-01-20

    Returns:
        Oluşturulan görevin detayları.
    """
    business_id = gorev_olustur._injected.get("business_id", "")
    token = gorev_olustur._injected.get("token", "")

    result = await backend_client.gorev_olustur_api(
        business_id=business_id,
        calisan_id=calisan_id,
        gorev_adi=gorev_adi,
        bitis_tarihi=bitis_tarihi,
        token=token,
    )
    return result

gorev_olustur._injected = {}


async def departman_raporu_iste(departman_id: str) -> dict:
    """Departman için yapay zeka destekli detaylı performans raporu oluşturur.

    Args:
        departman_id: Raporun oluşturulacağı departmanın benzersiz kimlik numarası.

    Returns:
        Rapor oluşturma durumu ve detayları.
    """
    business_id = departman_raporu_iste._injected.get("business_id", "")
    token = departman_raporu_iste._injected.get("token", "")

    result = await backend_client.departman_raporu_getir(
        business_id=business_id,
        departman_id=departman_id,
        token=token,
    )
    return result

departman_raporu_iste._injected = {}


async def tum_departman_skorlarini_getir() -> dict:
    """Tüm departmanların performans skorlarını toplu olarak getirir ve karşılaştırma sağlar. Departman bazlı toplu performans bilgisi istendiğinde bu aracı kullanın.

    Returns:
        Tüm departmanların güncel performans skorları ve analizleri.
    """
    business_id = tum_departman_skorlarini_getir._injected.get("business_id", "")
    token = tum_departman_skorlarini_getir._injected.get("token", "")
    departments = tum_departman_skorlarini_getir._injected.get("departments", [])

    if not departments:
        return {"hata": "Departman listesi bulunamadı veya yöneticinin erişim yetkisi olan departman yok."}

    import asyncio
    
    async def fetch_dep(dep):
        res = await backend_client.departman_performans_getir(business_id, dep["id"], token)
        return {"departman_adi": dep["name"], "sonuc": res}
        
    tasks = [fetch_dep(dep) for dep in departments]
    results = await asyncio.gather(*tasks)
    
    return {"tum_departman_skorlari": results}

tum_departman_skorlarini_getir._injected = {}


async def tum_calisanlari_listele() -> dict:
    """Şirketteki tüm çalışanların listesini (isim, departman, pozisyon bilgileriyle) getirir.
    'Tüm çalışanları listeler misin', 'Çalışan listesini getir' gibi taleplerde bu aracı kullanın.
    
    Returns:
        Şirketteki çalışanların listesi.
    """
    business_id = tum_calisanlari_listele._injected.get("business_id", "")
    token = tum_calisanlari_listele._injected.get("token", "")

    result = await backend_client.calisan_listesi_getir(business_id=business_id, token=token)
    
    if isinstance(result, dict) and result.get("hata"):
        return result
        
    calisanlar_api = result.get("data") or result.get("Data") or result.get("items") or [] if isinstance(result, dict) else (result if isinstance(result, list) else [])
    
    ozet_liste = []
    for c in calisanlar_api:
        ad_soyad = str(c.get("fullName") or c.get("FullName") or "")
        departman = str(c.get("departmentName") or c.get("DepartmentName") or "Bilinmiyor")
        pozisyon = str(c.get("positionName") or c.get("PositionName") or "Bilinmiyor")
        if ad_soyad:
            ozet_liste.append(f"{ad_soyad} - Departman: {departman} - Pozisyon: {pozisyon}")
            
    if not ozet_liste:
        return {"mesaj": "Şirkette kayıtlı çalışan bulunamadı veya liste çekilemedi."}
        
    return {"calisanlar": ozet_liste}

tum_calisanlari_listele._injected = {}


# ══════════════════════════════════════════════════════════════════════════════
# TOOL LİSTELERİ — ChatbotService tarafından kullanılır
# ══════════════════════════════════════════════════════════════════════════════

PERSONEL_TOOLS = [
    performans_sorgula,
    yeni_performans_hesapla,
    gorev_listele,
    izin_talebi_olustur,
    performans_gecmisi,
]

YONETICI_TOOLS = [
    # Personel tool'larının tamamı
    performans_sorgula,
    yeni_performans_hesapla,
    gorev_listele,
    izin_talebi_olustur,
    performans_gecmisi,
    # Yönetici ek tool'ları
    departman_performans,
    calisan_karsilastir,
    gorev_olustur,
    departman_raporu_iste,
    tum_departman_skorlarini_getir,
    tum_calisanlari_listele,
]

# Tüm tool'ların _injected attribute'unu ayarlamak için yardımcı
ALL_TOOLS = YONETICI_TOOLS
