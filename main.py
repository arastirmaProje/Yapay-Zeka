from fastapi import FastAPI, HTTPException

from app.models import (
    PerformansIstegi,
    PerformansRaporu,
    TopluPerformansSkoru,
    TopluPerformansSkorlari,
    DepartmanIstegi,
    DepartmanRaporu,
    CalisanSkorOzeti,
)
from app.services.calculator import PerformansHesaplayici
from app.services.generator import PerformanceReportGenerator

app = FastAPI(title="Personelim AI", version="0.1.0")

calculator = PerformansHesaplayici()
report_generator = PerformanceReportGenerator()


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Personelim AI API çalışıyor",
        "docs": "/docs",
        "health": "/test",
        "endpoints": {
            "calisan_raporu": "/api/performans",
            "toplu_skor": "/api/topluskor",
            "departman_raporu": "/api/departman/rapor",
        },
    }


@app.get("/test")
def read_root():
    return {"output": "API çalışıyor"}


# ── Bireysel Endpoints ────────────────────────────────────────────────────────

@app.post("/api/performans", response_model=PerformansRaporu, summary="Çalışan Raporu Oluştur")
def performans_hesapla(istek: PerformansIstegi):
    try:
        skor = calculator.hesapla(istek)
        analiz = calculator.analiz_ozeti_getir(istek)
        ozet, detay, grafik = report_generator.rapor_olustur(istek, skor, analiz)
        return PerformansRaporu(
            calisan_id=istek.calisan_id,
            performans_skoru=skor,
            rapor_ozeti=ozet,
            detayli_rapor=detay,
            grafik_verisi=grafik,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/topluskor", response_model=TopluPerformansSkorlari, summary="Toplu Skor Hesapla")
def toplu_skor_hesapla(istekler: list[PerformansIstegi]):
    try:
        skorlar = []
        for istek in istekler:
            skor = calculator.hesapla(istek)
            skorlar.append(
                TopluPerformansSkoru(
                    calisan_id=istek.calisan_id,
                    ad_soyad=istek.ad_soyad,
                    performans_skoru=skor,
                )
            )
        return TopluPerformansSkorlari(
            toplam_calisan=len(skorlar),
            skorlar=skorlar,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Departman Endpoints ───────────────────────────────────────────────────────

@app.post("/api/departman/rapor", response_model=DepartmanRaporu, summary="Departman Raporu Oluştur")
def departman_raporu_olustur(istek: DepartmanIstegi):
    try:
        calisan_skorlari_liste = []
        calisan_analizleri = []
        calisan_skor_ozetleri = []

        for calisan in istek.calisanlar:
            skor = calculator.hesapla(calisan)
            analiz = calculator.analiz_ozeti_getir(calisan)
            calisan_skorlari_liste.append(skor)
            calisan_analizleri.append(analiz)
            calisan_skor_ozetleri.append(
                CalisanSkorOzeti(
                    calisan_id=calisan.calisan_id,
                    ad_soyad=calisan.ad_soyad,
                    performans_skoru=round(skor, 2),
                )
            )

        departman_skoru = calculator.departman_skoru_hesapla(
            calisan_skorlari_liste, calisan_analizleri
        )
        departman_analizi = calculator.departman_analizi_getir(
            calisan_analizleri, calisan_skorlari_liste
        )
        calisan_skorlari_dict = [
            {"ad_soyad": c.ad_soyad, "skor": s}
            for c, s in zip(istek.calisanlar, calisan_skorlari_liste)
        ]

        ozet, detay, grafik = report_generator.departman_raporu_olustur(
            istek, departman_skoru, calisan_skorlari_dict, departman_analizi
        )

        return DepartmanRaporu(
            departman_id=istek.departman_id,
            departman_adi=istek.departman_adi,
            departman_skoru=departman_skoru,
            toplam_calisan=len(istek.calisanlar),
            calisan_skorlari=calisan_skor_ozetleri,
            rapor_ozeti=ozet,
            detayli_rapor=detay,
            grafik_verisi=grafik,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))