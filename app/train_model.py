import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib
import random
from sklearn.preprocessing import LabelEncoder


n=10000

calisan_id = np.random.randint(1, 10001, n)
gerceklesen_is_gunu = np.random.randint(15, 23, n)
hedeflenen_gunluk_mesai_saati = np.random.uniform(7.5, 10.0, n)
hedeflenen_haftalik_mesai_saati = np.random.uniform(40, 50, n)
gerceklesen_gunluk_mesai_saati = hedeflenen_gunluk_mesai_saati + np.random.normal(0, 3, n)
gerceklesen_haftalik_mesai_saati = hedeflenen_haftalik_mesai_saati + np.random.normal(0, 6, n)
kullanilan_izin_gunu = np.random.randint(0, 16, n)
zorluk_seviyesi = np.random.choice(['çok kolay','kolay', 'orta', 'zor','çok zor'], n)
tamamlanan_gorev_sayisi = np.random.randint(0, 6, n)
tamamlanamayan_gorev_sayisi = np.random.randint(0, 4, n)
#geri dönüt eklencek

olasi_basliklar = ["Login Sayfası", "Veritabanı Yedekleme", "API Entegrasyonu", "Hata Düzeltme", "Raporlama Ekranı", "CSS Düzenlemesi", "Performans Testi"]
olasi_durumlar = ["Tamamlandı", "Tamamlanmadı"]

gorevler_listesi = []

for i in range(n):
    gorev_sayisi = np.random.randint(1, 6)
    mevcut_calisan_gorevler = []
    for j in range(gorev_sayisi):
        gorev={
            "id": random.randint(1000, 20000), #random görev id
            "baslik": random.choice(olasi_basliklar),
            "durum": random.choice(olasi_durumlar)
        }
        mevcut_calisan_gorevler.append(gorev)
    gorevler_listesi.append(mevcut_calisan_gorevler)

df= pd.DataFrame({
    'calisan_id': calisan_id,
    'gerceklesen_is_gunu': gerceklesen_is_gunu,
    'hedeflenen_gunluk_mesai_saati': hedeflenen_gunluk_mesai_saati,
    'hedeflenen_haftalik_mesai_saati': hedeflenen_haftalik_mesai_saati,
    'gerceklesen_gunluk_mesai_saati': gerceklesen_gunluk_mesai_saati,
    'gerceklesen_haftalik_mesai_saati': gerceklesen_haftalik_mesai_saati,
    'kullanilan_izin_gunu': kullanilan_izin_gunu,
    'zorluk_seviyesi': zorluk_seviyesi,
    'tamamlanan_gorev_sayisi': tamamlanan_gorev_sayisi,
    'tamamlanamayan_gorev_sayisi': tamamlanamayan_gorev_sayisi,
    'gorevler': gorevler_listesi
})
df.head()

# Model eğitimi
def skor_puani_hesapla(row):
    """
    Latent (gizli) ağırlıklarla sentetik skor:
    - Program, görev/mesai/izin/zorluk önemini kendisi öğrenir (MLP/Regresör).
    - Burada yalnızca "gerçek" skoru üretmek için kullanılacak karma fonksiyon var.
    """
    tamamlanan = row["tamamlanan_gorev_sayisi"]
    tamamlanamayan = row["tamamlanamayan_gorev_sayisi"]
    toplam_gorev = max(tamamlanan + tamamlanamayan, 1)

    completion_rate = tamamlanan / toplam_gorev
    failure_rate = tamamlanamayan / toplam_gorev

    # Mesai uyumu (0-1 arası pozitif, sapma büyüdükçe azalır)
    mesai_gap = abs(row["hedeflenen_haftalik_mesai_saati"] - row["gerceklesen_haftalik_mesai_saati"])
    mesai_alignment = max(0.0, 1.0 - (mesai_gap / 20))  # ~20 saat sapma sıfırlar

    # İzin: 0-1 arası, 5 güne kadar nötr, üstü azalan
    izin = row["kullanilan_izin_gunu"]
    izin_factor = 1.0 if izin <= 5 else max(0.0, 1.0 - (izin - 5) / 15)

    # Zorluk: ölçeklenmiş katkı
    zorluk_map = {"çok kolay": 1, "kolay": 2, "orta": 3, "zor": 4, "çok zor": 5}
    zorluk_raw = row.get("zorluk_seviyesi", "orta")
    zorluk_val = zorluk_map.get(str(zorluk_raw).lower(), 3)
    zorluk_factor = (zorluk_val - 3) / 2  # -1..+1 aralığına yakınlar

    # Gizli ağırlıklar (model bilmiyor, sadece "gerçek" skor için)
    w_completion = 0.45
    w_failure = -0.25
    w_mesai = 0.20
    w_izin = 0.08
    w_zorluk = 0.12
    bias = 0.05

    latent_score = (
        w_completion * completion_rate
        + w_failure * failure_rate
        + w_mesai * mesai_alignment
        + w_izin * izin_factor
        + w_zorluk * zorluk_factor
        + bias
    )

    noise = np.random.normal(0, 0.02)
    latent_score = latent_score + noise

    # 0-100 skalasına taşı
    skor = max(0, min(100, (latent_score * 100)))
    return skor

df['performans_skoru'] = df.apply(skor_puani_hesapla, axis=1)

print("=" * 60)
print("VERİ SETİ HAZIR")
print("=" * 60)
print(f"Toplam kayıt sayısı: {len(df)}")
print(f"Ortalama performans skoru: {df['performans_skoru'].mean():.2f}")
print(f"Min performans skoru: {df['performans_skoru'].min():.2f}")
print(f"Max performans skoru: {df['performans_skoru'].max():.2f}")


le=LabelEncoder()
zorluk_haritasi={
    'çok kolay':1,
    'kolay':2,
    'orta':3,
    'zor':4,
    'çok zor':5
}

df['zorluk_seviyesi_encoded']=df['zorluk_seviyesi'].map(zorluk_haritasi)

df['toplam_gorev'] = (df['tamamlanan_gorev_sayisi'] + df['tamamlanamayan_gorev_sayisi']).apply(lambda x: max(x, 1))

df['tamamlanma_orani'] = df['tamamlanan_gorev_sayisi'] / df['toplam_gorev']

df['mesai_sapmasi_mutlak'] = abs(df['hedeflenen_haftalik_mesai_saati'] - df['gerceklesen_haftalik_mesai_saati'])

df['izin_esik_ustu'] = df['kullanilan_izin_gunu'].apply(lambda x: max(0, x - 5))

feature_names = [
    'hedeflenen_gunluk_mesai_saati',
    'hedeflenen_haftalik_mesai_saati',
    'gerceklesen_gunluk_mesai_saati',
    'gerceklesen_haftalik_mesai_saati',
    'tamamlanan_gorev_sayisi',
    'tamamlanamayan_gorev_sayisi',
    'zorluk_seviyesi_encoded',
    'tamamlanma_orani',
    'mesai_sapmasi_mutlak',
    'izin_esik_ustu'
]

X = df[feature_names]
y = df['performans_skoru']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"Eğitim seti boyutu: {len(X_train)}")
print(f"Test seti boyutu: {len(X_test)}")

# MLPRegressor + StandardScaler pipeline
mlp_reg = Pipeline(
    steps=[
        ("scaler", StandardScaler()),
        (
            "mlp",
            MLPRegressor(
                hidden_layer_sizes=(128, 64, 32), # Daha derin katmanlar
                activation="relu",
                solver="adam",
                alpha=1e-4, # Daha düşük ceza katsayısı
                learning_rate="adaptive",
                max_iter=1000, # Daha uzun eğitim
                random_state=42,
                early_stopping=True,
                n_iter_no_change=20, # Sabır arttı
                tol=1e-5 # Hassasiyet arttı
            ),
        ),
    ]
)
model = mlp_reg
model.fit(X_train, y_train)

# Tahmin değerlendirme
y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

# Eğitim seti
print("Eğitim Seti Değerlendirme:")
print(f" MAE: {mean_absolute_error(y_train, y_pred_train):.2f}")
print(f" RMSE: {np.sqrt(np.mean((y_train - y_pred_train) ** 2)):.2f}")
print(f" R²: {r2_score(y_train, y_pred_train):.4f}")
# Test
print("Test Seti Değerlendirme:")
print(f" MAE: {mean_absolute_error(y_test, y_pred_test):.2f}")
print(f" RMSE: {np.sqrt(np.mean((y_test - y_pred_test) ** 2)):.2f}")
print(f" R²: {r2_score(y_test, y_pred_test):.4f}")

# Model ve yardımcı dosyaları kaydet
joblib.dump(model, 'performans_model.pkl')
print(" Model kaydedildi: performans_model.pkl")

joblib.dump(zorluk_haritasi, 'zorluk_haritasi.pkl')
print("Zorluk haritası kaydedildi: zorluk_haritasi.pkl")

joblib.dump(feature_names, 'feature_names.pkl')
print("Feature isimleri kaydedildi: feature_names.pkl")
