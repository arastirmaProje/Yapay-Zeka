"""
Backend API Client — HTTP Proxy Katmanı
───────────────────────────────────────
Chatbot tool fonksiyonlarının backend API'ye (C# .NET) istek atması için
kullanılan HTTP client modülü.

Base URL .env'deki BACKEND_API_URL'den okunur.
Tüm isteklerde JWT token Authorization header'ında gönderilir.
"""

import os
import logging
from typing import Optional

import httpx
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=ROOT_DIR / ".env")

logger = logging.getLogger(__name__)

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://178.104.144.148:8080")

# HTTP client timeout ayarları (saniye)
_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
_BULK_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)


# ══════════════════════════════════════════════════════════════════════════════
# Yardımcı: Header oluştur
# ══════════════════════════════════════════════════════════════════════════════


def _headers(token: str) -> dict:
    """JWT token ile Authorization header'ı oluşturur."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _parse_response(response: httpx.Response) -> dict:
    """
    Backend yanıtını parse eder.
    Backend ServiceResponse formatı: { success, message, data, errors }
    """
    try:
        body = response.json()
    except Exception:
        return {"hata": f"Yanıt parse edilemedi (HTTP {response.status_code})"}

    if response.status_code >= 400:
        errors = body.get("errors", [])
        message = body.get("message", "Bilinmeyen hata")
        return {"hata": message, "detaylar": errors}

    return body


# ══════════════════════════════════════════════════════════════════════════════
# Profil API Çağrısı
# ══════════════════════════════════════════════════════════════════════════════

async def profil_getir(token: str) -> dict:
    """Giriş yapan kullanıcının profil bilgilerini (ad, soyad vb.) getirir.
    GET /api/Profile
    """
    url = f"{BACKEND_API_URL}/api/Profile"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_headers(token))
            return _parse_response(resp)
    except Exception as exc:
        logger.exception("profil_getir hatası")
        return {"hata": str(exc)}


# ══════════════════════════════════════════════════════════════════════════════
# Performans API Çağrıları
# ══════════════════════════════════════════════════════════════════════════════


async def performans_getir(
    business_id: str, calisan_id: str, token: str
) -> dict:
    """
    Çalışanın performans verisini backend'den çeker.
    GET /api/Performance/business/{businessId}/employee/{employeeUserId}
    """
    url = f"{BACKEND_API_URL}/api/Performance/business/{business_id}/employee/{calisan_id}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_headers(token))
            return _parse_response(resp)
    except httpx.ConnectError:
        return {"hata": "Backend sunucusuna bağlanılamadı. Lütfen daha sonra tekrar deneyin."}
    except httpx.TimeoutException:
        return {"hata": "Backend sunucusu yanıt vermedi (zaman aşımı)."}
    except Exception as exc:
        logger.exception("performans_getir hatası")
        return {"hata": f"Beklenmeyen hata: {str(exc)}"}


async def departman_performans_getir(
    business_id: str, departman_id: str, token: str
) -> dict:
    """
    Departman performans verisini backend'den çeker.
    GET /api/Performance/business/{businessId}/department/{departmentId}
    """
    url = f"{BACKEND_API_URL}/api/Performance/business/{business_id}/department/{departman_id}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_headers(token))
            return _parse_response(resp)
    except httpx.ConnectError:
        return {"hata": "Backend sunucusuna bağlanılamadı."}
    except httpx.TimeoutException:
        return {"hata": "Backend sunucusu yanıt vermedi (zaman aşımı)."}
    except Exception as exc:
        logger.exception("departman_performans_getir hatası")
        return {"hata": f"Beklenmeyen hata: {str(exc)}"}


async def toplu_performans_getir(
    business_id: str, token: str,
    start_date: Optional[str] = None, end_date: Optional[str] = None,
) -> dict:
    """
    İşletmedeki tüm çalışanların performans skorlarını toplu çeker.
    POST /api/Performance/query-bulk-scores
    """
    url = f"{BACKEND_API_URL}/api/Performance/query-bulk-scores"
    payload = {"businessId": business_id}
    if start_date:
        payload["startDate"] = start_date
    if end_date:
        payload["endDate"] = end_date
    try:
        async with httpx.AsyncClient(timeout=_BULK_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=_headers(token))
            return _parse_response(resp)
    except httpx.ConnectError:
        return {"hata": "Backend sunucusuna bağlanılamadı."}
    except httpx.TimeoutException:
        return {"hata": "Backend sunucusu yanıt vermedi (zaman aşımı)."}
    except Exception as exc:
        logger.exception("toplu_performans_getir hatası")
        return {"hata": f"Beklenmeyen hata: {str(exc)}"}


async def departman_raporu_getir(
    business_id: str, departman_id: str, token: str,
    start_date: Optional[str] = None, end_date: Optional[str] = None,
) -> dict:
    """
    Departman performans raporunu backend'den çeker.
    POST /api/Performance/query-department
    """
    url = f"{BACKEND_API_URL}/api/Performance/query-department"
    payload = {
        "businessId": business_id,
        "departmentId": departman_id,
    }
    if start_date:
        payload["startDate"] = start_date
    if end_date:
        payload["endDate"] = end_date
    try:
        async with httpx.AsyncClient(timeout=_BULK_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=_headers(token))
            return _parse_response(resp)
    except httpx.ConnectError:
        return {"hata": "Backend sunucusuna bağlanılamadı."}
    except httpx.TimeoutException:
        return {"hata": "Backend sunucusu yanıt vermedi (zaman aşımı)."}
    except Exception as exc:
        logger.exception("departman_raporu_getir hatası")
        return {"hata": f"Beklenmeyen hata: {str(exc)}"}


# ══════════════════════════════════════════════════════════════════════════════
# Görev (Task) API Çağrıları
# ══════════════════════════════════════════════════════════════════════════════


async def gorevleri_getir(
    business_id: str, token: str, calisan_id: Optional[str] = None,
) -> dict:
    """
    Görevleri backend'den çeker.
    - calisan_id verilirse: GET /api/Task/my-tasks (token ile, kendi görevleri)
    - calisan_id verilmezse: GET /api/Task/business/{businessId} (tüm görevler)
    """
    if calisan_id:
        # Personel kendi görevlerini listeliyor
        url = f"{BACKEND_API_URL}/api/Task/my-tasks"
    else:
        url = f"{BACKEND_API_URL}/api/Task/business/{business_id}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_headers(token))
            return _parse_response(resp)
    except httpx.ConnectError:
        return {"hata": "Backend sunucusuna bağlanılamadı."}
    except httpx.TimeoutException:
        return {"hata": "Backend sunucusu yanıt vermedi (zaman aşımı)."}
    except Exception as exc:
        logger.exception("gorevleri_getir hatası")
        return {"hata": f"Beklenmeyen hata: {str(exc)}"}


async def gorev_olustur_api(
    business_id: str, calisan_id: str, gorev_adi: str,
    bitis_tarihi: str, token: str,
    aciklama: Optional[str] = None,
    baslangic_tarihi: Optional[str] = None,
) -> dict:
    """
    Yeni görev oluşturur.
    POST /api/Task/create
    """
    url = f"{BACKEND_API_URL}/api/Task/create"
    payload = {
        "businessId": business_id,
        "assignedToUserId": calisan_id,
        "title": gorev_adi,
        "endDate": bitis_tarihi,
    }
    if aciklama:
        payload["description"] = aciklama
    if baslangic_tarihi:
        payload["startDate"] = baslangic_tarihi
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=_headers(token))
            return _parse_response(resp)
    except httpx.ConnectError:
        return {"hata": "Backend sunucusuna bağlanılamadı."}
    except httpx.TimeoutException:
        return {"hata": "Backend sunucusu yanıt vermedi (zaman aşımı)."}
    except Exception as exc:
        logger.exception("gorev_olustur_api hatası")
        return {"hata": f"Beklenmeyen hata: {str(exc)}"}


# ══════════════════════════════════════════════════════════════════════════════
# İzin (Leave) API Çağrıları
# ══════════════════════════════════════════════════════════════════════════════


async def izin_talebi_olustur_api(
    business_id: str, baslangic: str, bitis: str, neden: str, token: str,
) -> dict:
    """
    Yeni izin talebi oluşturur.
    POST /api/Leave
    """
    url = f"{BACKEND_API_URL}/api/Leave"
    payload = {
        "businessId": business_id,
        "title": neden,
        "description": neden,
        "startDate": baslangic,
        "endDate": bitis,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=_headers(token))
            return _parse_response(resp)
    except httpx.ConnectError:
        return {"hata": "Backend sunucusuna bağlanılamadı."}
    except httpx.TimeoutException:
        return {"hata": "Backend sunucusu yanıt vermedi (zaman aşımı)."}
    except Exception as exc:
        logger.exception("izin_talebi_olustur_api hatası")
        return {"hata": f"Beklenmeyen hata: {str(exc)}"}


async def izinleri_getir(
    business_id: str, token: str,
) -> dict:
    """
    Kullanıcının izin taleplerini getirir.
    GET /api/Leave/my-leaves/{businessId}
    """
    url = f"{BACKEND_API_URL}/api/Leave/my-leaves/{business_id}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_headers(token))
            return _parse_response(resp)
    except httpx.ConnectError:
        return {"hata": "Backend sunucusuna bağlanılamadı."}
    except httpx.TimeoutException:
        return {"hata": "Backend sunucusu yanıt vermedi (zaman aşımı)."}
    except Exception as exc:
        logger.exception("izinleri_getir hatası")
        return {"hata": f"Beklenmeyen hata: {str(exc)}"}

