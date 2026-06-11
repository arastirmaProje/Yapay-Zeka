"""
Chatbot endpoint'lerini test eden script.
"""
import json
import urllib.request
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
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return 0, {"hata": str(e)}


# ── TEST 1: Personel Chatbot — Basit sohbet ────────────────────────────────

print("=" * 60)
print("TEST 1: POST /api/chat/personel — Basit sohbet")
print("=" * 60)

calisan_id = str(uuid4())
status, data = post("/api/chat/personel", {
    "kullanici_id": calisan_id,
    "mesaj": "Merhaba, performansım nasıl?",
    "gecmis": [],
})
print(f"Status: {status}")
if status == 200:
    print(f"Yanıt: {data['yanit'][:200]}...")
    print(f"İşlem yapıldı: {data.get('islem_yapildi')}")
    print(f"Veri: {data.get('veri')}")
    print("✅ BAŞARILI")
else:
    print(f"❌ HATA: {data}")


# ── TEST 2: Personel Chatbot — Konuşma geçmişi ile ────────────────────────

print("\n" + "=" * 60)
print("TEST 2: POST /api/chat/personel — Geçmişli sohbet")
print("=" * 60)

status, data = post("/api/chat/personel", {
    "kullanici_id": calisan_id,
    "mesaj": "İzin almak istiyorum",
    "gecmis": [
        {"rol": "user", "icerik": "Merhaba"},
        {"rol": "model", "icerik": "Merhaba! Size nasıl yardımcı olabilirim?"},
    ],
})
print(f"Status: {status}")
if status == 200:
    print(f"Yanıt: {data['yanit'][:200]}...")
    print(f"İşlem yapıldı: {data.get('islem_yapildi')}")
    print("✅ BAŞARILI")
else:
    print(f"❌ HATA: {data}")


# ── TEST 3: Yönetici Chatbot ──────────────────────────────────────────────

print("\n" + "=" * 60)
print("TEST 3: POST /api/chat/yonetici — Departman sorgusu")
print("=" * 60)

yonetici_id = str(uuid4())
departman_id = str(uuid4())
status, data = post("/api/chat/yonetici", {
    "kullanici_id": yonetici_id,
    "departman_id": departman_id,
    "mesaj": "Departmanın performansı nasıl?",
    "gecmis": [],
})
print(f"Status: {status}")
if status == 200:
    print(f"Yanıt: {data['yanit'][:200]}...")
    print(f"İşlem yapıldı: {data.get('islem_yapildi')}")
    print(f"Veri: {data.get('veri')}")
    print("✅ BAŞARILI")
else:
    print(f"❌ HATA: {data}")


# ── TEST 4: Yönetici Chatbot — Görev oluşturma ───────────────────────────

print("\n" + "=" * 60)
print("TEST 4: POST /api/chat/yonetici — Görev oluşturma")
print("=" * 60)

status, data = post("/api/chat/yonetici", {
    "kullanici_id": yonetici_id,
    "departman_id": departman_id,
    "mesaj": "Ahmet'e yeni bir görev ata: Veritabanı optimizasyonu, zorluk zor, bitiş 2026-07-01",
    "gecmis": [],
})
print(f"Status: {status}")
if status == 200:
    print(f"Yanıt: {data['yanit'][:200]}...")
    print(f"İşlem yapıldı: {data.get('islem_yapildi')}")
    print(f"Veri: {data.get('veri')}")
    print("✅ BAŞARILI")
else:
    print(f"❌ HATA: {data}")


# ── TEST 5: Validasyon — Boş mesaj ────────────────────────────────────────

print("\n" + "=" * 60)
print("TEST 5: Validasyon — Eksik alan")
print("=" * 60)

status, data = post("/api/chat/personel", {
    "kullanici_id": calisan_id,
    # mesaj eksik
})
print(f"Status: {status}")
if status == 422:
    print("✅ DOĞRU: 422 Validation Error döndü")
else:
    print(f"⚠️ Beklenen 422, gelen: {status} — {data}")


# ── TEST 6: Personel Grafik Endpoint (mevcut) ────────────────────────────

print("\n" + "=" * 60)
print("TEST 6: POST /api/performans/grafikler (mevcut)")
print("=" * 60)

from datetime import datetime, timedelta

now = datetime.now().isoformat()
past = (datetime.now() - timedelta(hours=48)).isoformat()

gorevler = [
    {
        "id": str(uuid4()),
        "gorev_adi": "Test görevi",
        "zorluk_seviyesi": "orta",
        "durum": "Tamamlandı",
        "baslangic_tarihi": past,
        "bitistarihi": now,
        "aciklama": None,
        "geri_donut": None,
    }
]

status, data = post("/api/performans/grafikler", {
    "calisan_id": str(uuid4()),
    "ad_soyad": "Test Kişi",
    "tamamlanan_gorev_sayisi": 5,
    "tamamlanamayan_gorev_sayisi": 1,
    "hedeflenen_mesai_saati": 160,
    "gerceklesen_mesai_saati": 155,
    "kullanilan_izin_gunu": 2,
    "onceki_performans_skoru": 75.0,
    "gorevler": gorevler,
})
print(f"Status: {status}")
if status == 200:
    print(f"Performans Skoru: {data['performans_skoru']}")
    print(f"Grafik anahtarları: {list(data['grafik_verisi'].keys())}")
    print("✅ BAŞARILI")
else:
    print(f"❌ HATA: {data}")


print("\n" + "=" * 60)
print("TÜM CHATBOT TESTLERİ TAMAMLANDI")
print("=" * 60)
