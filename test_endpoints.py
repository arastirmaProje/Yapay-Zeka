"""
Tüm endpoint'leri test eden script.
"""
import json
import urllib.request
from datetime import datetime, timedelta
from uuid import uuid4

BASE = "http://127.0.0.1:8001"

def post(path, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

# ── Test Verileri ────────────────────────────────────────────────────────────

now = datetime.now().isoformat()
past = (datetime.now() - timedelta(hours=48)).isoformat()

gorevler = [
    {
        "id": str(uuid4()),
        "gorev_adi": "Veri tabanı optimizasyonu",
        "zorluk_seviyesi": "zor",
        "durum": "Tamamlandı",
        "baslangic_tarihi": past,
        "bitistarihi": now,
        "aciklama": "PostgreSQL sorgu optimizasyonu",
        "geri_donut": "Çok iyi iş çıkardı",
    },
    {
        "id": str(uuid4()),
        "gorev_adi": "Dokümantasyon güncelleme",
        "zorluk_seviyesi": "kolay",
        "durum": "Tamamlandı",
        "baslangic_tarihi": past,
        "bitistarihi": now,
        "aciklama": None,
        "geri_donut": None,
    },
    {
        "id": str(uuid4()),
        "gorev_adi": "Microservice entegrasyonu",
        "zorluk_seviyesi": "çok zor",
        "durum": "Beklemede",
        "baslangic_tarihi": past,
        "bitistarihi": now,
        "aciklama": "RabbitMQ ile entegrasyon",
        "geri_donut": None,
    },
]

calisan1 = {
    "calisan_id": str(uuid4()),
    "ad_soyad": "Yunus Emre Şimşek",
    "tamamlanan_gorev_sayisi": 8,
    "tamamlanamayan_gorev_sayisi": 2,
    "hedeflenen_mesai_saati": 160,
    "gerceklesen_mesai_saati": 172,
    "kullanilan_izin_gunu": 3,
    "onceki_performans_skoru": 74.5,
    "gorevler": gorevler,
}

calisan2 = {
    "calisan_id": str(uuid4()),
    "ad_soyad": "Zeynep Çelik",
    "tamamlanan_gorev_sayisi": 6,
    "tamamlanamayan_gorev_sayisi": 4,
    "hedeflenen_mesai_saati": 160,
    "gerceklesen_mesai_saati": 145,
    "kullanilan_izin_gunu": 5,
    "onceki_performans_skoru": 68.0,
    "gorevler": gorevler[:2],
}

calisan3 = {
    "calisan_id": str(uuid4()),
    "ad_soyad": "Ahmet Yılmaz",
    "tamamlanan_gorev_sayisi": 10,
    "tamamlanamayan_gorev_sayisi": 1,
    "hedeflenen_mesai_saati": 160,
    "gerceklesen_mesai_saati": 165,
    "kullanilan_izin_gunu": 1,
    "onceki_performans_skoru": 82.0,
    "gorevler": gorevler,
}


# ── TEST 1: Bireysel Performans ──────────────────────────────────────────────

print("=" * 60)
print("TEST 1: POST /api/performans")
print("=" * 60)
status, data = post("/api/performans", calisan1)
print(f"Status: {status}")
if status == 200:
    print(f"Performans Skoru: {data['performans_skoru']}")
    print(f"Rapor Özeti (ilk 150 karakter): {data['rapor_ozeti'][:150]}...")
    print(f"Grafik Verisi anahtarları: {list(data['grafik_verisi'].keys())}")
    print("✅ BAŞARILI")
else:
    print(f"❌ HATA: {data}")

# ── TEST 2: Toplu Skor ──────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("TEST 2: POST /api/topluskor")
print("=" * 60)
status, data = post("/api/topluskor", [calisan1, calisan2, calisan3])
print(f"Status: {status}")
if status == 200:
    print(f"Toplam Çalışan: {data['toplam_calisan']}")
    for s in data["skorlar"]:
        print(f"  - {s['ad_soyad']}: {s['performans_skoru']}")
    print("✅ BAŞARILI")
else:
    print(f"❌ HATA: {data}")

# ── TEST 3: Departman Raporu ─────────────────────────────────────────────────

print("\n" + "=" * 60)
print("TEST 3: POST /api/departman/rapor")
print("=" * 60)
dept_istek = {
    "departman_id": str(uuid4()),
    "departman_adi": "Yazılım Geliştirme",
    "calisanlar": [calisan1, calisan2, calisan3],
}
status, data = post("/api/departman/rapor", dept_istek)
print(f"Status: {status}")
if status == 200:
    print(f"Departman Skoru: {data['departman_skoru']}")
    print(f"Toplam Çalışan: {data['toplam_calisan']}")
    print(f"Grafik Verisi anahtarları: {list(data['grafik_verisi'].keys())}")
    # Yeni eklenen alanları kontrol et
    gv = data["grafik_verisi"]
    if "calisan_mesai_karsilastirma" in gv:
        print(f"  ✅ calisan_mesai_karsilastirma: {len(gv['calisan_mesai_karsilastirma'])} çalışan")
    if "calisan_detayli_metrikler" in gv:
        print(f"  ✅ calisan_detayli_metrikler: {len(gv['calisan_detayli_metrikler'])} çalışan")
    if "departman_mesai_ozeti" in gv:
        print(f"  ✅ departman_mesai_ozeti: {gv['departman_mesai_ozeti']}")
    if "gorev_dagilimi" in gv:
        print(f"  ✅ gorev_dagilimi: {gv['gorev_dagilimi']}")
    print("✅ BAŞARILI")
else:
    print(f"❌ HATA: {data}")

# ── TEST 4: Çoklu Departman Grafikleri ────────────────────────────────────────

print("\n" + "=" * 60)
print("TEST 4: POST /api/departman/grafikler")
print("=" * 60)
dept1 = {
    "departman_id": str(uuid4()),
    "departman_adi": "Yazılım Geliştirme",
    "calisanlar": [calisan1, calisan3],
}
dept2 = {
    "departman_id": str(uuid4()),
    "departman_adi": "Pazarlama",
    "calisanlar": [calisan2],
}
status, data = post("/api/departman/grafikler", [dept1, dept2])
print(f"Status: {status}")
if status == 200:
    print(f"Toplam Departman: {data['toplam_departman']}")
    gv = data["grafik_verisi"]
    print(f"Grafik Verisi anahtarları: {list(gv.keys())}")
    print(f"\nDepartman Puan Karşılaştırma:")
    for d in gv["departman_puan_karsilastirma"]:
        print(f"  - {d['departman_adi']}: {d['skor']}")
    print(f"\nMesai Karşılaştırma:")
    for d in gv["mesai_karsilastirma"]:
        print(f"  - {d['departman_adi']}: Hedef={d['hedeflenen_toplam']}h, Gerçek={d['gerceklesen_toplam']}h, Oran=%{d['mesai_kullanim_orani']}")
    print(f"\nGenel Özet: {json.dumps(gv['genel_ozet'], ensure_ascii=False, indent=2)}")
    print("✅ BAŞARILI")
else:
    print(f"❌ HATA: {data}")

print("\n" + "=" * 60)
print("TÜM TESTLER TAMAMLANDI")
print("=" * 60)
