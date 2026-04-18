from fastapi import FastAPI, HTTPException

from app.models import (
    PerformansIstegi,
    PerformansRaporu,
    TopluPerformansSkoru,
    TopluPerformansSkorlari,
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
        "performans": "/api/performans",
        "topluskor": "/api/topluskor",
    }


@app.get("/test")
def read_root():
    return {"output": "API çalışıyor"}


@app.post("/api/performans", response_model=PerformansRaporu, summary="Rapor Oluştur")
def performans_hesapla(istek: PerformansIstegi):
    try:
        skor = calculator.hesapla(istek)
        analiz = calculator.analiz_ozeti_getir(istek)        # ← YENİ
        ozet, detay, grafik = report_generator.rapor_olustur(istek, skor, analiz)  # ← GÜNCELLENDİ
        return PerformansRaporu(
            calisan_id=istek.calisan_id,
            performans_skoru=skor,
            rapor_ozeti=ozet,
            detayli_rapor=detay,
            grafik_verisi=grafik,                            # ← YENİ
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