from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

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
    
@app.post("/api/performans/html", response_class=HTMLResponse, summary="Görsel Rapor")
def performans_html(istek: PerformansIstegi):
    try:
        skor = calculator.hesapla(istek)
        analiz = calculator.analiz_ozeti_getir(istek)
        ozet, detay, grafik = report_generator.rapor_olustur(istek, skor, analiz)

        # Skor rengini belirle
        if skor >= 80:
            skor_renk = "#22c55e"
            skor_etiket = "Mükemmel"
        elif skor >= 60:
            skor_renk = "#3b82f6"
            skor_etiket = "İyi"
        elif skor >= 40:
            skor_renk = "#f59e0b"
            skor_etiket = "Geliştirilmeli"
        else:
            skor_renk = "#ef4444"
            skor_etiket = "Kritik"

        radar = grafik["radar"]
        gorev = grafik["gorev_dagilimi"]
        mesai = grafik["mesai_karsilastirma"]

        radar_kategoriler = str(radar["kategoriler"])
        radar_degerler = str(radar["degerler"])

        html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{istek.ad_soyad} - Performans Raporu</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f1f5f9;
            color: #1e293b;
            padding: 24px;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}

        .header {{
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            border-radius: 16px;
            padding: 32px;
            color: white;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 4px; }}
        .header p {{ font-size: 14px; opacity: 0.7; }}

        .skor-daire {{
            width: 100px;
            height: 100px;
            border-radius: 50%;
            border: 5px solid {skor_renk};
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: rgba(255,255,255,0.05);
        }}
        .skor-daire .sayi {{ font-size: 26px; font-weight: 800; color: {skor_renk}; }}
        .skor-daire .etiket {{ font-size: 11px; opacity: 0.8; margin-top: 2px; }}

        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .grid-3 {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}

        .kart {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        .kart h3 {{
            font-size: 13px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 16px;
        }}

        .metrik-kart {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            text-align: center;
        }}
        .metrik-kart .deger {{
            font-size: 28px;
            font-weight: 800;
            color: #1e293b;
        }}
        .metrik-kart .birim {{
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 4px;
        }}
        .metrik-kart .ad {{
            font-size: 12px;
            color: #64748b;
            margin-top: 4px;
        }}

        .rapor-box {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            margin-bottom: 20px;
            white-space: pre-wrap;
            line-height: 1.7;
            font-size: 14px;
            color: #334155;
        }}
        .rapor-box h3 {{
            font-size: 13px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 16px;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            background: {skor_renk}22;
            color: {skor_renk};
            margin-bottom: 8px;
        }}

        canvas {{ max-height: 260px; }}
    </style>
</head>
<body>
<div class="container">

    <!-- Header -->
    <div class="header">
        <div>
            <h1>{istek.ad_soyad}</h1>
            <p>Performans Raporu · {istek.calisan_id}</p>
            <div class="badge" style="margin-top:12px;">{skor_etiket}</div>
        </div>
        <div class="skor-daire">
            <span class="sayi">{skor:.0f}</span>
            <span class="etiket">/ 100</span>
        </div>
    </div>

    <!-- Metrik Kartları -->
    <div class="grid-3">
        <div class="metrik-kart">
            <div class="deger">{analiz['tamamlanma_orani']}<span style="font-size:16px;">%</span></div>
            <div class="ad">Görev Tamamlanma</div>
        </div>
        <div class="metrik-kart">
            <div class="deger">{analiz['verimlilik_skoru']}</div>
            <div class="ad">Verimlilik Skoru</div>
        </div>
        <div class="metrik-kart">
            <div class="deger">{analiz['mesai_kullanim_orani']}<span style="font-size:16px;">%</span></div>
            <div class="ad">Mesai Kullanımı</div>
        </div>
    </div>

    <!-- Grafikler -->
    <div class="grid-2">
        <div class="kart">
            <h3>Performans Radar</h3>
            <canvas id="radarChart"></canvas>
        </div>
        <div class="kart">
            <h3>Görev Dağılımı</h3>
            <canvas id="gorevChart"></canvas>
        </div>
    </div>

    <!-- Mesai Karşılaştırma -->
    <div class="kart" style="margin-bottom:20px;">
        <h3>Mesai Karşılaştırması (saat)</h3>
        <canvas id="mesaiChart"></canvas>
    </div>

    <!-- Rapor Özeti -->
    <div class="rapor-box">
        <h3>Özet</h3>
        {ozet}
    </div>

    <!-- Detaylı Rapor -->
    <div class="rapor-box">
        <h3>Detaylı Rapor</h3>
        {detay}
    </div>

</div>

<script>
const radarKategoriler = {radar_kategoriler};
const radarDegerler = {radar_degerler};

// Radar Chart
new Chart(document.getElementById('radarChart'), {{
    type: 'radar',
    data: {{
        labels: radarKategoriler,
        datasets: [{{
            label: 'Performans',
            data: radarDegerler,
            backgroundColor: 'rgba(59,130,246,0.15)',
            borderColor: '#3b82f6',
            borderWidth: 2,
            pointBackgroundColor: '#3b82f6',
        }}]
    }},
    options: {{
        responsive: true,
        scales: {{ r: {{ min: 0, max: 100, ticks: {{ stepSize: 25 }} }} }},
        plugins: {{ legend: {{ display: false }} }}
    }}
}});

// Görev Dağılımı
new Chart(document.getElementById('gorevChart'), {{
    type: 'doughnut',
    data: {{
        labels: ['Tamamlandı', 'Tamamlanamadı', 'Devam Ediyor'],
        datasets: [{{
            data: [{gorev['tamamlandi']}, {gorev['tamamlanamadi']}, {gorev['devam_ediyor']}],
            backgroundColor: ['#22c55e', '#ef4444', '#f59e0b'],
            borderWidth: 0,
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ position: 'bottom' }} }}
    }}
}});

// Mesai Chart
new Chart(document.getElementById('mesaiChart'), {{
    type: 'bar',
    data: {{
        labels: ['Hedeflenen', 'Gerçekleşen'],
        datasets: [{{
            data: [{mesai['hedeflenen']}, {mesai['gerceklesen']}],
            backgroundColor: ['#94a3b8', '#3b82f6'],
            borderRadius: 8,
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ y: {{ beginAtZero: true }} }}
    }}
}});
</script>
</body>
</html>
"""
        return HTMLResponse(content=html)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))