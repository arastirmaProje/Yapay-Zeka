"""
Entity Resolver — İsimden ID Otomatik Eşleştirme
─────────────────────────────────────────────────
Mobil ekibin Swift'te yazdığı ChatEntityResolver algoritmasının
Python karşılığı. Kullanıcı mesajından çalışan adı ve departman
adını algılayarak otomatik ID eşleştirmesi yapar.

Algoritma:
  1. Türkçe karakter normalizasyonu (ı→i, ğ→g, ü→u, ş→s, ö→o, ç→c)
  2. Kelime bazlı eşleşme skoru (intersection / target word count)
  3. Levenshtein edit mesafesi tabanlı benzerlik skoru
  4. İki skorun daha yüksek olanı alınır
  5. Eşik değer: >= 0.55 (mobil ekiple aynı)
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional, List


# ══════════════════════════════════════════════════════════════════════════════
# Veri modelleri
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class MemberDTO:
    """Mobil taraftan gelen çalışan bilgisi."""
    user_id: str
    full_name: str


@dataclass
class DepartmentDTO:
    """Mobil taraftan gelen departman bilgisi."""
    id: str
    name: str


@dataclass
class ResolvedEntity:
    """Eşleşme sonucu."""
    department_id: Optional[str] = None
    employee_user_id: Optional[str] = None
    matched_department_name: Optional[str] = None
    matched_employee_name: Optional[str] = None


MATCH_THRESHOLD = 0.55


def resolve(
    message: str,
    members: List[MemberDTO],
    departments: List[DepartmentDTO],
) -> ResolvedEntity:
    """
    Kullanıcı mesajından çalışan ve departman eşleştirmesi yapar.

    Args:
        message: Kullanıcının gönderdiği mesaj metni.
        members: İşletmedeki tüm çalışanların listesi.
        departments: İşletmedeki tüm departmanların listesi.

    Returns:
        ResolvedEntity: Eşleşen departman ve/veya çalışan ID'leri.
    """
    dept_match = _best_department_match(message, departments)
    member_match = _best_member_match(message, members)

    return ResolvedEntity(
        department_id=dept_match.id if dept_match else None,
        employee_user_id=member_match.user_id if member_match else None,
        matched_department_name=dept_match.name if dept_match else None,
        matched_employee_name=member_match.full_name if member_match else None,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Departman eşleştirme
# ══════════════════════════════════════════════════════════════════════════════


def _best_department_match(
    message: str,
    departments: List[DepartmentDTO],
) -> Optional[DepartmentDTO]:
    """Mesajdan en iyi departman eşleşmesini bulur."""
    if not departments:
        return None

    normalized_message = _normalize(message)

    scored = []
    for dept in departments:
        score = _similarity(normalized_message, _normalize(dept.name))
        if score >= MATCH_THRESHOLD:
            scored.append((dept, score))

    if not scored:
        return None

    # En yüksek skora sahip departmanı döndür
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0]


# ══════════════════════════════════════════════════════════════════════════════
# Çalışan eşleştirme
# ══════════════════════════════════════════════════════════════════════════════


def _best_member_match(
    message: str,
    members: List[MemberDTO],
) -> Optional[MemberDTO]:
    """Mesajdan en iyi çalışan eşleşmesini bulur."""
    if not members:
        return None

    normalized_message = _normalize(message)

    scored = []
    for member in members:
        score = _similarity(normalized_message, _normalize(member.full_name))
        if score >= MATCH_THRESHOLD:
            scored.append((member, score))

    if not scored:
        return None

    # En yüksek skora sahip çalışanı döndür
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0]


# ══════════════════════════════════════════════════════════════════════════════
# Normalizasyon — Türkçe karakter dönüşümü
# ══════════════════════════════════════════════════════════════════════════════

# Türkçe büyük harfler — lower() ÖNCESİ dönüştürülür (İ.lower() = i̇ sorunu)
_TR_UPPER_MAP = {
    "İ": "i",
    "I": "i",   # Türkçe I → i (ı değil)
    "Ğ": "g",
    "Ü": "u",
    "Ş": "s",
    "Ö": "o",
    "Ç": "c",
}

# Türkçe küçük harfler — lower() SONRASI dönüştürülür
_TR_LOWER_MAP = {
    "ı": "i",
    "ğ": "g",
    "ü": "u",
    "ş": "s",
    "ö": "o",
    "ç": "c",
}

# Regex: alfanümerik olmayan karakterleri temizle
_NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9\s]")


def _normalize(value: str) -> str:
    """
    Metni normalize eder:
    1. Türkçe büyük harfleri önce ASCII karşılıklarına dönüştür
       (Python'da 'İ'.lower() → 'i̇' sorunu önlenir)
    2. Küçük harfe çevir
    3. Kalan Türkçe küçük harfleri ASCII karşılıklarına dönüştür
    4. '&' karakterini boşluğa çevir
    5. Alfanümerik olmayan karakterleri temizle
    6. Boşluklarla birleştir

    Swift taraftaki normalize fonksiyonuyla birebir aynı mantık.
    """
    result = value

    # Önce Türkçe BÜYÜK harfleri dönüştür (lower() öncesi — İ sorunu için kritik)
    for tr_upper, ascii_lower in _TR_UPPER_MAP.items():
        result = result.replace(tr_upper, ascii_lower)

    # Küçük harfe çevir
    result = result.lower()

    # & → boşluk
    result = result.replace("&", " ")

    # Kalan Türkçe küçük harfleri dönüştür
    for tr_char, ascii_char in _TR_LOWER_MAP.items():
        result = result.replace(tr_char, ascii_char)

    # Alfanümerik olmayan karakterleri temizle
    result = _NON_ALNUM_PATTERN.sub(" ", result)

    # Boş olmayan kelimeleri boşlukla birleştir
    words = [w for w in result.split() if w]
    return " ".join(words)


# ══════════════════════════════════════════════════════════════════════════════
# Benzerlik hesaplama
# ══════════════════════════════════════════════════════════════════════════════


def _similarity(text: str, target: str) -> float:
    """
    İki normalize metin arasındaki benzerlik skorunu hesaplar.

    İki farklı metrik kullanır ve daha yüksek olanı döner:
    1. Kelime eşleşme skoru (intersection / target kelime sayısı)
    2. Levenshtein edit mesafesi tabanlı benzerlik (1 - distance/maxLength)

    Swift taraftaki similarity fonksiyonuyla birebir aynı mantık.
    """
    # Tam içerme kontrolü
    if target in text:
        return 1.0

    text_words = set(text.split())
    target_words = set(target.split())

    if not target_words:
        return 0.0

    # Kelime bazlı eşleşme skoru
    intersection = len(text_words & target_words)
    word_score = intersection / len(target_words)

    # Levenshtein tabanlı edit skoru
    distance = _levenshtein(text, target)
    max_length = max(len(text), len(target))

    if max_length == 0:
        return word_score

    edit_score = 1.0 - (distance / max_length)

    return max(word_score, edit_score)


# ══════════════════════════════════════════════════════════════════════════════
# Levenshtein mesafesi
# ══════════════════════════════════════════════════════════════════════════════


def _levenshtein(lhs: str, rhs: str) -> int:
    """
    İki string arasındaki Levenshtein edit mesafesini hesaplar.

    Klasik dinamik programlama yaklaşımı.
    Swift taraftaki levenshtein fonksiyonuyla birebir aynı mantık.
    """
    lhs_len = len(lhs)
    rhs_len = len(rhs)

    # Basit durumlar
    if lhs_len == 0:
        return rhs_len
    if rhs_len == 0:
        return lhs_len

    # DP matrisi
    distances = [[0] * (rhs_len + 1) for _ in range(lhs_len + 1)]

    for i in range(lhs_len + 1):
        distances[i][0] = i

    for j in range(rhs_len + 1):
        distances[0][j] = j

    for i in range(1, lhs_len + 1):
        for j in range(1, rhs_len + 1):
            if lhs[i - 1] == rhs[j - 1]:
                distances[i][j] = distances[i - 1][j - 1]
            else:
                distances[i][j] = min(
                    distances[i - 1][j] + 1,      # silme
                    distances[i][j - 1] + 1,      # ekleme
                    distances[i - 1][j - 1] + 1,  # değiştirme
                )

    return distances[lhs_len][rhs_len]
