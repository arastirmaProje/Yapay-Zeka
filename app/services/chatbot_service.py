"""
Chatbot Service — Ana Chatbot Motoru
────────────────────────────────────
Gemini 2.5 Flash + Function Calling ile çalışan akıllı sohbet motoru.
Personel ve yönetici olmak üzere iki ayrı chatbot rolü desteklenir.

Önemli kararlar:
  - Konuşma geçmişi backend ekibi tarafından tutulur, biz saklamıyoruz.
  - Tek mesajda tek tool çağrısı (tool_config → ONE mode).
  - Maliyet kontrolü: Flash model, kısa token limiti, resim üretimi yok.
"""

import os
import sys
import json
from typing import Dict, Any, Optional

import google.generativeai as genai
from google.generativeai import types
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
load_dotenv(dotenv_path=ROOT_DIR / ".env")

try:
    from app.chatbot_models import (
        PersonelChatIstegi,
        YoneticiChatIstegi,
        ChatYaniti,
        ChatMesaj,
    )
    from app.services.chatbot_tools import PERSONEL_TOOLS, YONETICI_TOOLS, ALL_TOOLS
    from app.services.entity_resolver import (
        resolve as resolve_entities,
        MemberDTO,
        DepartmentDTO,
    )
except ImportError:
    from ..chatbot_models import (
        PersonelChatIstegi,
        YoneticiChatIstegi,
        ChatYaniti,
        ChatMesaj,
    )
    from .chatbot_tools import PERSONEL_TOOLS, YONETICI_TOOLS, ALL_TOOLS
    from .entity_resolver import (
        resolve as resolve_entities,
        MemberDTO,
        DepartmentDTO,
    )


# ══════════════════════════════════════════════════════════════════════════════
# System Prompt'lar
# ══════════════════════════════════════════════════════════════════════════════

PERSONEL_SYSTEM_PROMPT = """Sen "Personelim" uygulamasının yapay zeka asistanısın.
Bir çalışana yardımcı oluyorsun. Görevin:

1. Çalışanın performans skorunu sorgulamak
2. Görevlerini listelemek ve durumlarını bildirmek
3. İzin talebi oluşturmak
4. Performans geçmişini göstermek

KURALLAR:
- Her zaman Türkçe konuş, profesyonel ve samimi ol.
- Sadece çalışanın KENDİ verileriyle ilgili sorulara cevap ver.
- Başka çalışanların verilerini paylaşma.
- Yanıtlarını kısa ve öz tut, mobil ekranda rahat okunacak şekilde yaz.
- Markdown biçimlendirme kullanma (yıldız, diyez, backtick vs.). Düz metin yaz.
- Eğer sana verilen tool'larla cevaplayamayacağın bir soru gelirse, kibarca bunu belirt.
- Kullanıcının ID'si her istekte sana verilecek, tool çağrılarında bu ID'yi kullan."""

YONETICI_SYSTEM_PROMPT = """Sen "Personelim" uygulamasının yönetici yapay zeka asistanısın.
Bir departman yöneticisine yardımcı oluyorsun. Görevin:

1. Departman performansını sorgulamak ve analiz etmek
2. Çalışanları karşılaştırmak
3. Görev oluşturmak ve atamak
4. Çalışanların performansını sorgulamak
5. İzin taleplerini yönetmek
6. Departman raporu oluşturmak

KURALLAR:
- Her zaman Türkçe konuş, profesyonel ve yönetici diline uygun ol.
- Departman geneli ve bireysel çalışan verileri hakkında bilgi verebilirsin.
- Stratejik önerilerde bulun, yöneticiye karar desteği sağla.
- Yanıtlarını kısa ve öz tut, mobil ekranda rahat okunacak şekilde yaz.
- Markdown biçimlendirme kullanma (yıldız, diyez, backtick vs.). Düz metin yaz.
- Eğer sana verilen tool'larla cevaplayamayacağın bir soru gelirse, kibarca bunu belirt.
- Kullanıcının ID'si ve departman ID'si her istekte sana verilecek, tool çağrılarında bunları kullan.
- Mesajda bir çalışan adı veya departman adı geçtiğinde, sistem otomatik olarak eşleşen ID'yi bulur ve sana context olarak verir. Bu ID'leri tool çağrılarında doğrudan kullan, kullanıcıdan tekrar ID sorma.
- Eğer otomatik eşleşme sonucu context'te bir calisan_id veya departman_id verilmişse, onu doğrudan tool parametresi olarak kullan.
- Eğer otomatik eşleşme bulunamazsa ve tool çağrısı için ID gerekiyorsa, o zaman kullanıcıya nazikçe sor."""


# ══════════════════════════════════════════════════════════════════════════════
# Tool dispatch haritası
# ══════════════════════════════════════════════════════════════════════════════

# Tool fonksiyonlarını isimleriyle eşle (Gemini function_call.name ile çağırmak için)
_TOOL_DISPATCH: Dict[str, callable] = {}
for fn in YONETICI_TOOLS:
    _TOOL_DISPATCH[fn.__name__] = fn


# ══════════════════════════════════════════════════════════════════════════════
# ChatbotService
# ══════════════════════════════════════════════════════════════════════════════


class ChatbotService:
    """
    Gemini 2.5 Flash tabanlı chatbot motoru.
    Personel ve yönetici rolleri için ayrı model konfigürasyonları kullanır.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash") -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY çevre değişkeni tanımlanmadı.")
        genai.configure(api_key=api_key)

        self.model_name = model_name

        # ── Maliyet kontrollü generation config ───────────────────────────
        self.generation_config = types.GenerationConfig(
            max_output_tokens=1024,
            temperature=0.7,
        )

        # ── Tool config: tek mesajda tek tool ─────────────────────────────
        self.tool_config = {"function_calling_config": {"mode": "AUTO"}}

        # ── Personel modeli ───────────────────────────────────────────────
        self.personel_model = genai.GenerativeModel(
            model_name=model_name,
            tools=PERSONEL_TOOLS,
            system_instruction=PERSONEL_SYSTEM_PROMPT,
            generation_config=self.generation_config,
        )

        # ── Yönetici modeli ───────────────────────────────────────────────
        self.yonetici_model = genai.GenerativeModel(
            model_name=model_name,
            tools=YONETICI_TOOLS,
            system_instruction=YONETICI_SYSTEM_PROMPT,
            generation_config=self.generation_config,
        )

    # ── Yardımcı: Geçmişi Gemini formatına çevir ─────────────────────────

    def _gecmisi_donustur(self, gecmis: list[ChatMesaj]) -> list[dict]:
        """Backend'den gelen konuşma geçmişini Gemini Content formatına çevirir."""
        history = []
        for mesaj in gecmis:
            history.append(
                {"role": mesaj.rol, "parts": [mesaj.icerik]}
            )
        return history

    # ── Yardımcı: Tool fonksiyonlarına context inject et ───────────────────

    def _inject_context(self, business_id: str, token: str, departments: list = None) -> None:
        """Tüm tool fonksiyonlarına business_id, token ve departments inject eder."""
        for fn in ALL_TOOLS:
            if hasattr(fn, '_injected'):
                fn._injected = {
                    "business_id": business_id,
                    "token": token,
                    "departments": departments or [],
                }

    # ── Yardımcı: Tool çağrısını işle ─────────────────────────────────────

    async def _tool_cagri_isle(
        self, function_call
    ) -> tuple[str, dict, Optional[str]]:
        """
        Gemini'den gelen function_call nesnesini çalıştırır.
        Tool fonksiyonları async olduğu için await ile çağrılır.

        Returns:
            (tool_adi, tool_sonucu, None) veya hata durumunda
            (tool_adi, hata_dict, hata_mesaji)
        """
        tool_adi = function_call.name
        tool_args = dict(function_call.args) if function_call.args else {}

        fn = _TOOL_DISPATCH.get(tool_adi)
        if fn is None:
            return (
                tool_adi,
                {"hata": f"Bilinmeyen tool: {tool_adi}"},
                f"Bilinmeyen tool: {tool_adi}",
            )

        try:
            sonuc = await fn(**tool_args)
            return tool_adi, sonuc, None
        except Exception as exc:
            return (
                tool_adi,
                {"hata": str(exc)},
                str(exc),
            )

    # ── Ana chat akışı ────────────────────────────────────────────────────

    async def _chat_isle(
        self,
        model: genai.GenerativeModel,
        mesaj: str,
        gecmis: list[ChatMesaj],
        business_id: str,
        token: str,
        ek_context: str = "",
        departments: list = None,
    ) -> ChatYaniti:
        """
        Genel chat akışı:
        1. Tool fonksiyonlarına business_id/token inject et
        2. Geçmişi Gemini formatına çevir
        3. Kullanıcı mesajını ekle (ek context ile)
        4. Gemini'ye gönder
        5. Tool call varsa çalıştır, sonucu Gemini'ye geri gönder
        6. Son yanıtı ChatYaniti olarak döndür
        """

        # 0) Tool fonksiyonlarına context inject et
        self._inject_context(business_id=business_id, token=token, departments=departments)

        # 1) Konuşma geçmişini hazırla
        history = self._gecmisi_donustur(gecmis)

        # 2) Chat oturumu başlat
        chat = model.start_chat(history=history)

        # 3) Mesajı hazırla (ek context varsa ekle)
        tam_mesaj = f"{ek_context}\n\n{mesaj}" if ek_context else mesaj

        # 4) Gemini'ye gönder
        response = chat.send_message(
            tam_mesaj,
            tool_config=self.tool_config,
        )

        # 5) Tool call kontrolü
        islem_yapildi = None
        tool_verisi = None

        # İlk yanıtta function call var mı kontrol et
        candidate = response.candidates[0]
        parts = candidate.content.parts

        function_call_part = None
        for part in parts:
            if hasattr(part, "function_call") and part.function_call.name:
                function_call_part = part
                break

        if function_call_part is not None:
            # Tool çağrısını işle (async)
            tool_adi, tool_sonucu, hata = await self._tool_cagri_isle(
                function_call_part.function_call
            )
            islem_yapildi = tool_adi
            tool_verisi = tool_sonucu

            # Tool sonucunu Gemini'ye geri gönder
            tool_response = genai.protos.Content(
                role="function",
                parts=[
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=tool_adi,
                            response=tool_sonucu,
                        )
                    )
                ],
            )

            # Gemini'den son yanıtı al
            response = chat.send_message(tool_response)

        # 6) Son yanıt metnini al
        yanit_metni = ""
        if hasattr(response, "text"):
            yanit_metni = response.text
        else:
            # Parts'lardan metin topla
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    yanit_metni += part.text

        if not yanit_metni:
            yanit_metni = "Üzgünüm, yanıt oluşturulamadı. Lütfen tekrar deneyin."

        return ChatYaniti(
            yanit=yanit_metni.strip(),
            islem_yapildi=islem_yapildi,
            veri=tool_verisi,
        )

    # ── Personel Chat ─────────────────────────────────────────────────────

    async def personel_chat(self, istek: PersonelChatIstegi) -> ChatYaniti:
        """Personel chatbot'u — çalışan kendi verileriyle etkileşir."""
        ek_context = (
            f"[Sistem bilgisi — kullanıcıya gösterme] "
            f"Konuşan çalışanın ID'si: {istek.kullanici_id}"
        )
        return await self._chat_isle(
            model=self.personel_model,
            mesaj=istek.mesaj,
            gecmis=istek.gecmis,
            business_id=str(istek.business_id),
            token=istek.token,
            ek_context=ek_context,
        )

    # ── Yönetici Chat ────────────────────────────────────────────────────

    async def yonetici_chat(self, istek: YoneticiChatIstegi) -> ChatYaniti:
        """Yönetici chatbot'u — departman yönetimi ve ekip analizi."""
        dept_bilgi = (
            f", departman ID'si: {istek.departman_id}"
            if istek.departman_id
            else ""
        )
        ek_context = (
            f"[Sistem bilgisi — kullanıcıya gösterme] "
            f"Konuşan yöneticinin ID'si: {istek.kullanici_id}{dept_bilgi}"
        )

        # ── Entity Resolution: isimden otomatik ID eşleştirme ─────────
        if istek.members or istek.departments:
            members_dto = [
                MemberDTO(user_id=m.user_id, full_name=m.full_name)
                for m in istek.members
            ]
            departments_dto = [
                DepartmentDTO(id=d.id, name=d.name)
                for d in istek.departments
            ]

            resolved = resolve_entities(
                message=istek.mesaj,
                members=members_dto,
                departments=departments_dto,
            )

            resolve_parts = []
            if resolved.employee_user_id:
                resolve_parts.append(
                    f"Mesajda tespit edilen calisan: {resolved.matched_employee_name} "
                    f"(calisan_id: {resolved.employee_user_id})"
                )
            if resolved.department_id:
                resolve_parts.append(
                    f"Mesajda tespit edilen departman: {resolved.matched_department_name} "
                    f"(departman_id: {resolved.department_id})"
                )

            if resolve_parts:
                ek_context += (
                    "\n\n[Otomatik esleme sonucu]\n"
                    + "\n".join(resolve_parts)
                    + "\nBu ID'leri tool cagirislarinda dogrudan kullan, "
                    "kullanicidan tekrar ID sorma."
                )

        return await self._chat_isle(
            model=self.yonetici_model,
            mesaj=istek.mesaj,
            gecmis=istek.gecmis,
            business_id=str(istek.business_id),
            token=istek.token,
            ek_context=ek_context,
            departments=[d.model_dump() for d in istek.departments]
        )
