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
    mesaj: str = Field(..., description="Kullanıcının gönderdiği mesaj")
    gecmis: List[ChatMesaj] = Field(
        default_factory=list,
        description="Önceki konuşma geçmişi (backend tarafından gönderilir)",
    )


# ── Yönetici Chat ────────────────────────────────────────────────────────────


class YoneticiChatIstegi(BaseModel):
    """Yönetici chatbot isteği. Departman yönetimi ve ekip analizi."""

    kullanici_id: UUID = Field(..., description="Yöneticinin benzersiz ID'si")
    departman_id: Optional[UUID] = Field(
        None, description="Yöneticinin departman ID'si (opsiyonel)"
    )
    mesaj: str = Field(..., description="Yöneticinin gönderdiği mesaj")
    gecmis: List[ChatMesaj] = Field(
        default_factory=list,
        description="Önceki konuşma geçmişi (backend tarafından gönderilir)",
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
