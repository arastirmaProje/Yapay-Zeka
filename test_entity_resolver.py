"""
Entity Resolver unit testleri.
Türkçe karakter normalizasyonu, benzerlik hesaplama ve eşleştirme doğruluğu.
"""
import sys
from pathlib import Path

# Proje kök dizinini path'e ekle
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.entity_resolver import (
    resolve,
    MemberDTO,
    DepartmentDTO,
    _normalize,
    _similarity,
    _levenshtein,
)


# ══════════════════════════════════════════════════════════════════════════════
# Test verileri
# ══════════════════════════════════════════════════════════════════════════════

MEMBERS = [
    MemberDTO(user_id="user-001", full_name="Yunus Emre Şimşek"),
    MemberDTO(user_id="user-002", full_name="Ahmet Yılmaz"),
    MemberDTO(user_id="user-003", full_name="Fatma Kaya"),
    MemberDTO(user_id="user-004", full_name="Mehmet Ali Çelik"),
    MemberDTO(user_id="user-005", full_name="Ayşe Güneş"),
]

DEPARTMENTS = [
    DepartmentDTO(id="dept-001", name="IT Departmanı"),
    DepartmentDTO(id="dept-002", name="İnsan Kaynakları"),
    DepartmentDTO(id="dept-003", name="Muhasebe"),
    DepartmentDTO(id="dept-004", name="Pazarlama & Satış"),
    DepartmentDTO(id="dept-005", name="Ar-Ge"),
]

PASSED = 0
FAILED = 0


def assert_eq(test_name, actual, expected):
    global PASSED, FAILED
    if actual == expected:
        PASSED += 1
        print(f"  OK {test_name}")
    else:
        FAILED += 1
        print(f"  FAIL {test_name}")
        print(f"     Beklenen: {expected}")
        print(f"     Alınan:   {actual}")


def assert_gte(test_name, actual, threshold):
    global PASSED, FAILED
    if actual >= threshold:
        PASSED += 1
        print(f"  OK {test_name} (skor: {actual:.3f} >= {threshold})")
    else:
        FAILED += 1
        print(f"  FAIL {test_name}")
        print(f"     Skor: {actual:.3f} < eşik: {threshold}")


def assert_lt(test_name, actual, threshold):
    global PASSED, FAILED
    if actual < threshold:
        PASSED += 1
        print(f"  OK {test_name} (skor: {actual:.3f} < {threshold})")
    else:
        FAILED += 1
        print(f"  FAIL {test_name}")
        print(f"     Skor: {actual:.3f} >= eşik: {threshold}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. Normalize testleri
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("TEST GRUBU 1: Türkçe Karakter Normalizasyonu")
print("=" * 60)

assert_eq(
    "Basit Türkçe normalize",
    _normalize("Şimşek"),
    "simsek",
)

assert_eq(
    "Tam isim normalize",
    _normalize("Yunus Emre Şimşek"),
    "yunus emre simsek",
)

assert_eq(
    "Büyük İ normalize",
    _normalize("İnsan Kaynakları"),
    "insan kaynaklari",
)

assert_eq(
    "& karakteri boşluğa çevrilir",
    _normalize("Pazarlama & Satış"),
    "pazarlama satis",
)

assert_eq(
    "Özel karakterler temizlenir",
    _normalize("Ar-Ge"),
    "ar ge",
)

assert_eq(
    "Çoklu boşluklar temizlenir",
    _normalize("  Mehmet   Ali   Çelik  "),
    "mehmet ali celik",
)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Levenshtein testleri
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("TEST GRUBU 2: Levenshtein Mesafesi")
print("=" * 60)

assert_eq("Aynı string", _levenshtein("test", "test"), 0)
assert_eq("Bir karakter fark", _levenshtein("test", "tast"), 1)
assert_eq("Boş string", _levenshtein("", "abc"), 3)
assert_eq("Her ikisi boş", _levenshtein("", ""), 0)
assert_eq("Tamamen farklı", _levenshtein("abc", "xyz"), 3)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Similarity testleri
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("TEST GRUBU 3: Benzerlik Skoru")
print("=" * 60)

# Tam içerme → 1.0
assert_eq(
    "Tam içerme skoru 1.0",
    _similarity("yunus emre simsek gorevlerini ver", "yunus emre simsek"),
    1.0,
)

# Kelime eşleşmesi
assert_gte(
    "Kelime eşleşmesi (2/3 kelime)",
    _similarity("yunus emre gorevleri", "yunus emre simsek"),
    0.55,
)

# Düşük benzerlik
assert_lt(
    "Düşük benzerlik",
    _similarity("merhaba nasilsin", "yunus emre simsek"),
    0.55,
)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Çalışan eşleştirme testleri
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("TEST GRUBU 4: Çalışan Eşleştirme")
print("=" * 60)

result = resolve("Yunus Emre Şimşek görevlerini ver", MEMBERS, DEPARTMENTS)
assert_eq("Tam isim eşleşme", result.employee_user_id, "user-001")
assert_eq("Eşleşen isim", result.matched_employee_name, "Yunus Emre Şimşek")

result = resolve("Ahmet Yılmaz performansı nasıl?", MEMBERS, DEPARTMENTS)
assert_eq("Ahmet Yılmaz eşleşme", result.employee_user_id, "user-002")

result = resolve("Fatma Kaya'ya görev ata", MEMBERS, DEPARTMENTS)
assert_eq("Fatma Kaya eşleşme", result.employee_user_id, "user-003")

result = resolve("Mehmet Ali Çelik izin durumu", MEMBERS, DEPARTMENTS)
assert_eq("Mehmet Ali Çelik eşleşme", result.employee_user_id, "user-004")

result = resolve("merhaba nasılsın", MEMBERS, DEPARTMENTS)
assert_eq("Eşleşme yok", result.employee_user_id, None)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Departman eşleştirme testleri
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("TEST GRUBU 5: Departman Eşleştirme")
print("=" * 60)

result = resolve("IT departmanı performansı nasıl?", MEMBERS, DEPARTMENTS)
assert_eq("IT departmanı eşleşme", result.department_id, "dept-001")
assert_eq("Eşleşen departman adı", result.matched_department_name, "IT Departmanı")

result = resolve("İnsan kaynakları çalışanları listele", MEMBERS, DEPARTMENTS)
assert_eq("İnsan Kaynakları eşleşme", result.department_id, "dept-002")

result = resolve("Muhasebe departmanı raporu", MEMBERS, DEPARTMENTS)
assert_eq("Muhasebe eşleşme", result.department_id, "dept-003")

result = resolve("Pazarlama satış ekibi", MEMBERS, DEPARTMENTS)
assert_eq("Pazarlama & Satış eşleşme", result.department_id, "dept-004")

result = resolve("Bugün hava güzel", MEMBERS, DEPARTMENTS)
assert_eq("Departman eşleşme yok", result.department_id, None)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Birleşik eşleştirme testleri (hem çalışan hem departman)
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("TEST GRUBU 6: Birleşik Eşleştirme")
print("=" * 60)

result = resolve(
    "IT departmanında Ahmet Yılmaz'ın görevlerini listele",
    MEMBERS,
    DEPARTMENTS,
)
assert_eq("Birleşik - çalışan", result.employee_user_id, "user-002")
assert_eq("Birleşik - departman", result.department_id, "dept-001")


# ══════════════════════════════════════════════════════════════════════════════
# 7. Boş liste testleri
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("TEST GRUBU 7: Boş Liste Dayanıklılığı")
print("=" * 60)

result = resolve("Yunus Emre görevleri", [], [])
assert_eq("Boş listeler - çalışan", result.employee_user_id, None)
assert_eq("Boş listeler - departman", result.department_id, None)

result = resolve("IT departmanı", MEMBERS, [])
assert_eq("Boş departman listesi", result.department_id, None)

result = resolve("Ahmet Yılmaz", [], DEPARTMENTS)
assert_eq("Boş üye listesi", result.employee_user_id, None)


# ══════════════════════════════════════════════════════════════════════════════
# Özet
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
total = PASSED + FAILED
print(f"SONUC: {PASSED}/{total} test basarili", end="")
if FAILED > 0:
    print(f" -- {FAILED} BASARISIZ!")
else:
    print(" [OK]")
print("=" * 60)
