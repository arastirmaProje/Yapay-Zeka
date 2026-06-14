from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMesaj(BaseModel):
    """Tek bir sohbet mesajı. Backend tarafından saklanır ve her istekte gönderilir."""

    rol: str = Field(..., description="Mesaj rolü: 'user' veya 'model'")
    icerik: str = Field(..., description="Mesaj içeriği")


# ── Personel Chat ─────────────────────────────────────────────────────────────


class PersonelChatIstegi(BaseModel):
    """Personel chatbot isteği. Çalışan kendi verileriyle etkileşir."""

    kullanici_id: UUID = Field(..., description="Çalışanın benzersiz ID'si")
    business_id: UUID = Field(..., description="Çalışanın bağlı olduğu işletme ID'si")
    token: str = Field(..., description="Kullanıcının JWT token'ı (backend API çağrıları için)")
    mesaj: str = Field(..., description="Kullanıcının gönderdiği mesaj")
    gecmis: List[ChatMesaj] = Field(
        default_factory=list,
        description="Önceki konuşma geçmişi (backend tarafından gönderilir)",
    )


# ── Yönetici Chat ────────────────────────────────────────────────────────────


class MemberInfo(BaseModel):
    """Mobil taraftan gelen çalışan bilgisi (isim→ID eşleştirmesi için)."""

    user_id: str = Field(..., description="Çalışanın benzersiz ID'si")
    full_name: str = Field(..., description="Çalışanın tam adı soyadı")


class DepartmentInfo(BaseModel):
    """Mobil taraftan gelen departman bilgisi (isim→ID eşleştirmesi için)."""

    id: str = Field(..., description="Departmanın benzersiz ID'si")
    name: str = Field(..., description="Departmanın adı")


class YoneticiChatIstegi(BaseModel):
    """Yönetici chatbot isteği. Departman yönetimi ve ekip analizi."""

    kullanici_id: UUID = Field(..., description="Yöneticinin benzersiz ID'si")
    business_id: UUID = Field(..., description="Yöneticinin bağlı olduğu işletme ID'si")
    token: str = Field(..., description="Kullanıcının JWT token'ı (backend API çağrıları için)")
    departman_id: Optional[UUID] = Field(
        None, description="Yöneticinin departman ID'si (opsiyonel)"
    )
    mesaj: str = Field(..., description="Yöneticinin gönderdiği mesaj")
    gecmis: List[ChatMesaj] = Field(
        default_factory=list,
        description="Önceki konuşma geçmişi (backend tarafından gönderilir)",
    )
    members: List[MemberInfo] = Field(
        default_factory=list,
        description="İşletmedeki çalışan listesi (isim→ID eşleştirmesi için)",
    )
    departments: List[DepartmentInfo] = Field(
        default_factory=list,
        description="İşletmedeki departman listesi (isim→ID eşleştirmesi için)",
    )


# ── Chat Yanıtı ──────────────────────────────────────────────────────────────


class ChatYaniti(BaseModel):
    """Chatbot yanıt modeli."""

    yanit: str = Field(..., description="Chatbot'un metin yanıtı")
    islem_yapildi: Optional[str] = Field(
        None, description="Çağrılan tool adı (varsa)"
    )
    veri: Optional[Dict[str, Any]] = Field(
        None, description="Tool'dan dönen ek veri (grafik, skor vs.)"
    )
