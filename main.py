from statistics import mean

from fastapi import FastAPI, HTTPException

from app.models import (
    PerformansIstegi,
    PerformansRaporu,
    TopluPerformansSkoru,
    TopluPerformansSkorlari,
    DepartmanIstegi,
    DepartmanRaporu,
    CalisanSkorOzeti,
    CokluDepartmanGrafik,
    CalisanGrafikRaporu,
)
from app.services.calculator import PerformansHesaplayici
from app.services.generator import PerformanceReportGenerator

app = FastAPI(
    title="Personelim AI",
    version="0.2.0",
    description="Personelim uygulaması yapay zeka destekli performans analiz ve raporlama API'si.",
)

calculator = PerformansHesaplayici()
report_generator = PerformanceReportGenerator()


@app.get("/", tags=["Genel"])
def root():
    return {
        "status": "ok",
        "message": "Personelim AI API çalışıyor",
        "docs": "/docs",
        "endpoints": {
            "calisan_raporu": "POST /api/performans",
            "toplu_skor": "POST /api/topluskor",
            "departman_raporu": "POST /api/departman/rapor",
            "departman_grafikleri": "POST /api/departman/grafikler",
        },
    }


@app.get("/test", tags=["Genel"])
def health_check():
    return {"status": "ok", "message": "API çalışıyor"}


# ── Bireysel Performans Endpoints ─────────────────────────────────────────────

@app.post(
    "/api/performans",
    response_model=PerformansRaporu,
    tags=["Çalışan"],
    summary="Çalışan Performans Raporu Oluştur",

)
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


@app.post(
    "/api/performans/grafikler",
    response_model=CalisanGrafikRaporu,
    tags=["Çalışan"],
    summary="Çalışan Grafik Verilerini Getir",
)
def performans_grafikleri(istek: PerformansIstegi):
    """
    Çalışanın performans metriklerini yapay zeka raporu üretmeden sadece grafik verisi olarak hızlıca döner.
    Mobil tarafta bireysel çalışan grafikleri çizmek için idealdir.
    """
    try:
        skor = calculator.hesapla(istek)
        analiz = calculator.analiz_ozeti_getir(istek)
        
        grafik_verisi = {
            "mesai_karsilastirma": {
                "hedeflenen": istek.hedeflenen_mesai_saati,
                "gerceklesen": istek.gerceklesen_mesai_saati,
            },
            "performans_karsilastirma": {
                "guncel": round(skor, 2),
                "onceki": istek.onceki_performans_skoru,
            },
            "metrikler": {
                "tamamlanma_orani": analiz["tamamlanma_orani"],
                "verimlilik_skoru": analiz["verimlilik_skoru"],
                "deadline_uyum_skoru": analiz["deadline_uyum_skoru"],
                "zorluk_basari_dengesi": analiz["zorluk_basari_dengesi"],
                "mesai_kullanim_orani": analiz["mesai_kullanim_orani"],
                "ortalama_zorluk": analiz["ortalama_zorluk"],
            },
        }
        
        return CalisanGrafikRaporu(
            calisan_id=istek.calisan_id,
            performans_skoru=skor,
            grafik_verisi=grafik_verisi,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))



@app.post(
    "/api/topluskor",
    response_model=TopluPerformansSkorlari,
    tags=["Çalışan"],
    summary="Toplu Performans Skoru Hesapla",

)
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

@app.post(
    "/api/departman/rapor",
    response_model=DepartmanRaporu,
    tags=["Departman"],
    summary="Departman Performans Raporu Oluştur",

)
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
            istek, departman_skoru, calisan_skorlari_dict, departman_analizi,
            calisan_analizleri=calisan_analizleri,
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


# ── Çoklu Departman Grafik Karşılaştırma ─────────────────────────────────────

@app.post(
    "/api/departman/grafikler",
    response_model=CokluDepartmanGrafik,
    tags=["Departman"],
    summary="Çoklu Departman Grafik Karşılaştırma Verileri",
)
def departman_grafikleri(istekler: list[DepartmanIstegi]):
    """
    Birden fazla departmanın performans verilerini karşılaştırmalı grafik
    metrikleri olarak döner. AI raporu üretmez, sadece ham grafik verisi döner.
    Mobilciler bu veriyle departmanlar arası karşılaştırma grafikleri çizer.
    """
    try:
        if len(istekler) < 1:
            raise HTTPException(
                status_code=400,
                detail="En az 1 departman verisi gönderilmelidir.",
            )

        departman_verileri = []

        for dept in istekler:
            calisan_skorlari = []
            calisan_analizleri = []
            toplam_hedeflenen = 0.0
            toplam_gerceklesen = 0.0
            toplam_tamamlanan = 0
            toplam_tamamlanamayan = 0
            toplam_izin = 0

            for calisan in dept.calisanlar:
                skor = calculator.hesapla(calisan)
                analiz = calculator.analiz_ozeti_getir(calisan)
                calisan_skorlari.append(skor)
                calisan_analizleri.append(analiz)
                toplam_hedeflenen += calisan.hedeflenen_mesai_saati
                toplam_gerceklesen += calisan.gerceklesen_mesai_saati
                toplam_tamamlanan += calisan.tamamlanan_gorev_sayisi
                toplam_tamamlanamayan += calisan.tamamlanamayan_gorev_sayisi
                toplam_izin += calisan.kullanilan_izin_gunu

            dept_skor = calculator.departman_skoru_hesapla(
                calisan_skorlari, calisan_analizleri
            )
            dept_analiz = calculator.departman_analizi_getir(
                calisan_analizleri, calisan_skorlari
            )

            departman_verileri.append({
                "departman_id": str(dept.departman_id),
                "departman_adi": dept.departman_adi,
                "skor": round(dept_skor, 2),
                "calisan_sayisi": len(dept.calisanlar),
                "toplam_hedeflenen_mesai": round(toplam_hedeflenen, 1),
                "toplam_gerceklesen_mesai": round(toplam_gerceklesen, 1),
                "toplam_tamamlanan_gorev": toplam_tamamlanan,
                "toplam_tamamlanamayan_gorev": toplam_tamamlanamayan,
                "toplam_izin_gunu": toplam_izin,
                "analiz": dept_analiz,
            })

        # ── Grafik verileri oluştur ───────────────────────────────────────

        grafik_verisi = {
            # 1. Departman puan karşılaştırması (bar chart — yüksekten düşüğe)
            "departman_puan_karsilastirma": sorted(
                [
                    {"departman_adi": d["departman_adi"], "skor": d["skor"]}
                    for d in departman_verileri
                ],
                key=lambda x: x["skor"],
                reverse=True,
            ),

            # 2. Departman bazlı mesai karşılaştırması (grouped bar chart)
            "mesai_karsilastirma": [
                {
                    "departman_adi": d["departman_adi"],
                    "hedeflenen_toplam": d["toplam_hedeflenen_mesai"],
                    "gerceklesen_toplam": d["toplam_gerceklesen_mesai"],
                    "mesai_kullanim_orani": round(
                        (d["toplam_gerceklesen_mesai"] / d["toplam_hedeflenen_mesai"] * 100)
                        if d["toplam_hedeflenen_mesai"] > 0 else 0.0, 1
                    ),
                }
                for d in departman_verileri
            ],

            # 3. Departman bazlı görev tamamlanma oranı karşılaştırması (bar chart)
            "tamamlanma_orani_karsilastirma": [
                {
                    "departman_adi": d["departman_adi"],
                    "oran": d["analiz"]["ortalama_tamamlanma_orani"],
                }
                for d in departman_verileri
            ],

            # 4. Departman bazlı verimlilik karşılaştırması (bar chart)
            "verimlilik_karsilastirma": [
                {
                    "departman_adi": d["departman_adi"],
                    "verimlilik": d["analiz"]["ortalama_verimlilik"],
                }
                for d in departman_verileri
            ],

            # 5. Departman bazlı zorluk-başarı dengesi karşılaştırması (bar chart)
            "zorluk_basari_karsilastirma": [
                {
                    "departman_adi": d["departman_adi"],
                    "zorluk_basari": d["analiz"]["ortalama_zorluk_basari"],
                }
                for d in departman_verileri
            ],

            # 6. Departman bazlı çalışan sayısı dağılımı (pie / donut chart)
            "calisan_sayisi_dagilimi": [
                {
                    "departman_adi": d["departman_adi"],
                    "calisan_sayisi": d["calisan_sayisi"],
                }
                for d in departman_verileri
            ],

            # 7. Departman bazlı görev dağılımı (stacked bar chart)
            "gorev_dagilimi_karsilastirma": [
                {
                    "departman_adi": d["departman_adi"],
                    "tamamlanan": d["toplam_tamamlanan_gorev"],
                    "tamamlanamayan": d["toplam_tamamlanamayan_gorev"],
                    "toplam": d["toplam_tamamlanan_gorev"] + d["toplam_tamamlanamayan_gorev"],
                }
                for d in departman_verileri
            ],

            # 8. Departman bazlı deadline uyumu karşılaştırması (bar chart)
            "deadline_uyumu_karsilastirma": [
                {
                    "departman_adi": d["departman_adi"],
                    "deadline_uyumu": d["analiz"]["ortalama_deadline_uyumu"],
                }
                for d in departman_verileri
            ],

            # 9. Departman bazlı mesai kullanım oranı karşılaştırması (bar chart)
            "mesai_kullanim_karsilastirma": [
                {
                    "departman_adi": d["departman_adi"],
                    "mesai_kullanimi": d["analiz"]["ortalama_mesai_kullanimi"],
                }
                for d in departman_verileri
            ],

            # 10. Genel özet (summary card verileri)
            "genel_ozet": {
                "toplam_departman": len(departman_verileri),
                "toplam_calisan": sum(d["calisan_sayisi"] for d in departman_verileri),
                "ortalama_departman_skoru": round(
                    mean([d["skor"] for d in departman_verileri]), 2
                ),
                "en_yuksek_departman": {
                    "departman_adi": max(departman_verileri, key=lambda x: x["skor"])["departman_adi"],
                    "skor": max(departman_verileri, key=lambda x: x["skor"])["skor"],
                },
                "en_dusuk_departman": {
                    "departman_adi": min(departman_verileri, key=lambda x: x["skor"])["departman_adi"],
                    "skor": min(departman_verileri, key=lambda x: x["skor"])["skor"],
                },
                "toplam_hedeflenen_mesai": round(
                    sum(d["toplam_hedeflenen_mesai"] for d in departman_verileri), 1
                ),
                "toplam_gerceklesen_mesai": round(
                    sum(d["toplam_gerceklesen_mesai"] for d in departman_verileri), 1
                ),
                "toplam_tamamlanan_gorev": sum(d["toplam_tamamlanan_gorev"] for d in departman_verileri),
                "toplam_tamamlanamayan_gorev": sum(d["toplam_tamamlanamayan_gorev"] for d in departman_verileri),
            },
        }

        return CokluDepartmanGrafik(
            toplam_departman=len(departman_verileri),
            grafik_verisi=grafik_verisi,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))