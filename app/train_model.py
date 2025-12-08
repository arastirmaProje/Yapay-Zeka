import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
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

#model eğitimi
#?? performans skoru hesaplama
def skor_puani_hesapla(row):
    max_gorev=5
    gorev_skoru = (row['tamamlanan_gorev_sayisi'] - row['tamamlanamayan_gorev_sayisi']) / max_gorev * 100
    mesai_farki= abs(row['hedeflenen_haftalik_mesai_saati'] - row['gerceklesen_haftalik_mesai_saati'])
    mesai_skoru = max(0, 100 - mesai_farki * 2)  # Mesai farkı arttıkça skor düşer
    toplam_skor = (gorev_skoru * 0.6) + (mesai_skoru * 0.4)
    return max(0,min(100,toplam_skor))

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



feature_names = [
    'hedeflenen_gunluk_mesai_saati',
    'hedeflenen_haftalik_mesai_saati',
    'gerceklesen_gunluk_mesai_saati',
    'gerceklesen_haftalik_mesai_saati',
    'tamamlanan_gorev_sayisi',
    'tamamlanamayan_gorev_sayisi',
    'zorluk_seviyesi_encoded'
]


X = df[feature_names] 
y = df['performans_skoru']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"Eğitim seti boyutu: {len(X_train)}")
print(f"Test seti boyutu: {len(X_test)}")

model = RandomForestRegressor(
    n_estimators=100,
    random_state=42,
    min_samples_split=5,
    max_depth=15,
    min_samples_leaf=2,
    n_jobs=-1
)

model.fit(X_train, y_train)

#tahmin değerlendirme
y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

#eğitim seti
print("eğitim Seti Değerlendirme:")
print(f" MAE: {mean_absolute_error(y_train, y_pred_train):.2f}")
print(f" RMSE: {np.sqrt(np.mean((y_train - y_pred_train) ** 2)):.2f}")
print(f" R²: {r2_score(y_train, y_pred_train):.4f}")
#test
print("Test Seti Değerlendirme:")
print(f" MAE: {mean_absolute_error(y_test, y_pred_test):.2f}")
print(f" RMSE: {np.sqrt(np.mean((y_test - y_pred_test) ** 2)):.2f}")
print(f" R²: {r2_score(y_test, y_pred_test):.4f}")



joblib.dump(model, 'performans_model.pkl')
print(" Model kaydedildi: performans_model.pkl")

joblib.dump(zorluk_haritasi, 'zorluk_haritasi.pkl')
print("Zorluk haritası kaydedildi: zorluk_haritasi.pkl")

joblib.dump(feature_names, 'feature_names.pkl')
print("Feature isimleri kaydedildi: feature_names.pkl")
