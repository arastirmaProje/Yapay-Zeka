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
    from app.services import backend_client

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
    from . import backend_client



# System Prompt'lar


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
- KÜFÜR VE HAKARET YASAKTIR: Kullanıcı küfür, argo, hakaret veya saldırgan bir dil kullanırsa, KESİNLİKLE araç (tool) çağırma ve işlemi reddet. Profesyonel ve resmi bir dille bu tarz ifadelere izin verilmediğini belirterek soruyu yanıtsız bırak.
- ŞİRKET DIŞI KONULAR YASAKTIR: Sen bir iş asistanısın. Hava durumu, genel geyik muhabbeti, tarih, siyaset gibi saçma veya iş dışı sorulara yanıt verme. "Ben bir şirket asistanıyım, sadece iş süreçleri hakkında yardımcı olabilirim" diyerek kibarca reddet.
- KİŞİSELLEŞTİRME VE GİZLİLİK: Kullanıcıya asla ID (UUID vb.) detaylarından bahsetme. "ID'mi biliyor musun?" diyenlere "Sisteme giriş yaptığınız için sizi tanıyorum" şeklinde yanıt ver. "Benim görevlerim neler" dediğinde sana arka planda verilen ID'yi gizlice kullanarak ilgili araçları (tool) çalıştır.
- GENEL ŞİRKET VERİSİ YASAKTIR: Eğer şirkette kaç kişi var, kaç departman var veya başkasının performansı nasıl gibi sorular gelirse: "Bu tarz genel şirket verilerine sadece yöneticiler erişebilir, ben size sadece kendi verileriniz hakkında yardımcı olabilirim" diyerek reddet.
- Kullanıcının ID'si ve adı her istekte sana arka planda verilecek, tool çağrılarında sadece bu ID'yi kullan ve kullanıcıyla adı üzerinden iletişim kur."""

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
- KÜFÜR VE HAKARET YASAKTIR: Kullanıcı küfür, argo, hakaret veya saldırgan bir dil kullanırsa, KESİNLİKLE araç (tool) çağırma ve işlemi reddet. Profesyonel ve resmi bir dille bu tarz ifadelere izin verilmediğini belirterek soruyu yanıtsız bırak.
- ŞİRKET DIŞI KONULAR YASAKTIR: Sen bir iş asistanısın. Hava durumu, genel geyik muhabbeti, tarih, siyaset gibi saçma veya iş dışı sorulara yanıt verme. "Ben bir şirket asistanıyım, sadece iş süreçleri hakkında yardımcı olabilirim" diyerek kibarca reddet.
- KİŞİSELLEŞTİRME VE GİZLİLİK: Kullanıcıya asla ID (UUID vb.) detaylarından bahsetme. "ID'mi biliyor musun?" diyenlere "Sisteme giriş yaptığınız için sizi tanıyorum" şeklinde yanıt ver. Sana arka planda verilen kendi yöneticilik yetkilerindeki departman/çalışan listesini kullanarak doğal iletişim kur.
- ŞİRKET İSTATİSTİKLERİ: Sana arka planda şirketteki departman ve çalışan sayıları verilecek, istendiğinde bunları paylaşabilirsin.
- Kullanıcının kendi ID'si, adı ve departman ID'si her istekte sana verilecek. Kullanıcı SADECE KENDİSİYLE ilgili bir işlem (ör: kendi izin talebi, kendi görevleri) yapıyorsa bu ID'yi kullan.
- BAŞKASINA (bir çalışana) yönelik işlem (ör: görev oluşturma, performans sorgulama) yapılacaksa ve mesajda kişi belirtilmemişse, mutlaka "Kime / Hangi çalışana?" diye sor. Asla varsayılan olarak yöneticinin kendi ID'sini bu tür işlemler için kullanma.
- Mesajda bir çalışan adı veya departman adı geçtiğinde, sistem otomatik olarak eşleşen ID'yi bulur ve sana context olarak verir. Bu ID'leri tool çağrılarında doğrudan kullan, kullanıcıdan tekrar ID sorma.
- Eğer otomatik eşleşme bulunamazsa ve tool çağrısı için departman veya çalışan ID'si gerekiyorsa, o zaman kullanıcıya nazikçe sor."""



# Tool dispatch haritası


# Tool fonksiyonlarını isimleriyle eşle (Gemini function_call.name ile çağırmak için)
_TOOL_DISPATCH: Dict[str, callable] = {}
for fn in YONETICI_TOOLS:
    _TOOL_DISPATCH[fn.__name__] = fn



# ChatbotService



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
        try:
            response = chat.send_message(
                tam_mesaj,
                tool_config=self.tool_config,
            )
        except Exception as e:
            return ChatYaniti(
                yanit=f"Üzgünüm, mesajınızı işlerken yapay zeka servisinde bir sorun oluştu: {str(e)}",
                islem_yapildi=None,
                veri=None,
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

            # Gemini, FunctionResponse.response için her zaman dict bekler.
            # tool_sonucu liste veya başka bir tür dönmüşse dict içine sar.
            safe_response = tool_sonucu if isinstance(tool_sonucu, dict) else {"sonuc": tool_sonucu}

            # Tool sonucunu Gemini'ye geri gönder
            tool_response = genai.protos.Content(
                role="function",
                parts=[
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=tool_adi,
                            response=safe_response,
                        )
                    )
                ],
            )

            # Gemini'den son yanıtı al
            try:
                response = chat.send_message(tool_response)
            except Exception as e:
                return ChatYaniti(
                    yanit=f"İşleminiz yapıldı ancak sonucun raporlanmasında bir sorun oluştu: {str(e)}",
                    islem_yapildi=tool_adi,
                    veri=tool_sonucu,
                )

        # 6) Son yanıt metnini al
        yanit_metni = ""
        try:
            yanit_metni = response.text
        except ValueError:
            # response.text ValueError fırlatırsa (part yoksa), manuel deneyelim veya boş bırakalım.
            if response.candidates and response.candidates[0].content.parts:
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
        # 1. API'den kullanıcının adını/soyadını alalım (Kişiselleştirme)
        profil_verisi = await backend_client.profil_getir(istek.token)
        profil_data = profil_verisi.get("data") or profil_verisi.get("Data") or profil_verisi
        ad = profil_data.get("firstName") or profil_data.get("FirstName") or ""
        soyad = profil_data.get("lastName") or profil_data.get("LastName") or ""
        ad_soyad = f"{ad} {soyad}".strip() or "Değerli Çalışanımız"

        # 2. Çalışanın kendi departman/pozisyon bilgisini alalım
        calisan_listesi_res = await backend_client.calisan_listesi_getir(str(istek.business_id), istek.token)
        calisanlar_api = calisan_listesi_res.get("data") or calisan_listesi_res.get("Data") or calisan_listesi_res.get("items") or [] if isinstance(calisan_listesi_res, dict) else (calisan_listesi_res if isinstance(calisan_listesi_res, list) else [])
        
        benim_departmanim = "Bilinmiyor"
        benim_pozisyonum = "Bilinmiyor"
        for c in calisanlar_api:
            c_id = str(c.get("userId") or c.get("UserId") or c.get("userid") or "")
            if c_id == str(istek.kullanici_id):
                benim_departmanim = str(c.get("departmentName") or c.get("DepartmentName") or "Bilinmiyor")
                benim_pozisyonum = str(c.get("positionName") or c.get("PositionName") or "Bilinmiyor")
                break

        ek_context = (
            f"[Sistem bilgisi — kullanıcıya GİZLİ olarak verilen veri]\n"
            f"Senin konuştuğun kişinin adı: {ad_soyad}.\n"
            f"Kullanıcının sistem ID'si: {istek.kullanici_id}\n"
            f"Kullanıcının departmanı: {benim_departmanim}\n"
            f"Kullanıcının pozisyonu: {benim_pozisyonum}\n"
            f"Eğer kullanıcı 'görevlerim', 'performansım' gibi KENDİ verilerini sorarsa "
            f"bu ID'yi kullanarak araçlarını (tool) çalıştır. Ancak kullanıcıya asla bu ID bilgisini gösterme, sadece 'isminizi biliyorum' de."
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
        # 1. API'den yöneticinin adını/soyadını alalım
        profil_verisi = await backend_client.profil_getir(istek.token)
        profil_data = profil_verisi.get("data") or profil_verisi.get("Data") or profil_verisi
        ad = profil_data.get("firstName") or profil_data.get("FirstName") or ""
        soyad = profil_data.get("lastName") or profil_data.get("LastName") or ""
        ad_soyad = f"{ad} {soyad}".strip() or "Değerli Yöneticimiz"

        dept_bilgi = (
            f"\nYönettiği departman ID'si: {istek.departman_id}"
            if istek.departman_id
            else ""
        )
        
        # 2. Departman Listesini Kontrol Et / API'den Güncelle
        # Mobil taraftan departments listesi boş gelme ihtimaline karşı backend'den tam listeyi çekelim.
        departman_listesi_res = await backend_client.departman_listesi_getir(str(istek.business_id), istek.token)
        
        if isinstance(departman_listesi_res, dict):
            departmanlar_api = departman_listesi_res.get("data") or departman_listesi_res.get("Data") or departman_listesi_res.get("items") or []
        elif isinstance(departman_listesi_res, list):
            departmanlar_api = departman_listesi_res
        else:
            departmanlar_api = []
        
        if departmanlar_api and len(departmanlar_api) > 0:
            departman_sayisi = len(departmanlar_api)
            # Mobil uygulamadan departments dizisi boş gelmişse dolduralım (AI tolları için gerekli)
            if not istek.departments:
                from app.chatbot_models import DepartmentInfo
                for d in departmanlar_api:
                    d_id = str(d.get("id") or d.get("Id") or d.get("ID") or "")
                    d_name = str(d.get("name") or d.get("Name") or "")
                    if d_id and d_name:
                        istek.departments.append(DepartmentInfo(id=d_id, name=d_name))
        else:
            departman_sayisi = len(istek.departments)

        # 3. Çalışan Listesini Kontrol Et / API'den Güncelle
        # Mobil taraftan members (çalışanlar) listesi boş gelirse, ID eşleştirmesi çalışmaz.
        calisan_listesi_res = await backend_client.calisan_listesi_getir(str(istek.business_id), istek.token)
        
        if isinstance(calisan_listesi_res, dict):
            calisanlar_api = calisan_listesi_res.get("data") or calisan_listesi_res.get("Data") or calisan_listesi_res.get("items") or []
        elif isinstance(calisan_listesi_res, list):
            calisanlar_api = calisan_listesi_res
        else:
            calisanlar_api = []
            
        if calisanlar_api and len(calisanlar_api) > 0:
            calisan_sayisi = len(calisanlar_api)
            if not istek.members:
                from app.chatbot_models import MemberInfo
                for c in calisanlar_api:
                    c_id = str(c.get("userId") or c.get("UserId") or c.get("userid") or "")
                    c_name = str(c.get("fullName") or c.get("FullName") or c.get("fullname") or "")
                    if c_id and c_name:
                        istek.members.append(MemberInfo(user_id=c_id, full_name=c_name))
        else:
            calisan_sayisi = len(istek.members)

        benim_departmanim = "Bilinmiyor"
        benim_pozisyonum = "Bilinmiyor"
        for c in calisanlar_api:
            c_id = str(c.get("userId") or c.get("UserId") or c.get("userid") or "")
            if c_id == str(istek.kullanici_id):
                benim_departmanim = str(c.get("departmentName") or c.get("DepartmentName") or "Bilinmiyor")
                benim_pozisyonum = str(c.get("positionName") or c.get("PositionName") or "Bilinmiyor")
                break

        departman_listesi_str = ", ".join([f"{d.name} (ID: {d.id})" for d in istek.departments]) if istek.departments else "Bilinmiyor"

        ek_context = (
            f"[Sistem bilgisi — kullanıcıya GİZLİ olarak verilen veri]\n"
            f"Şu an konuştuğun yöneticinin adı: {ad_soyad}.\n"
            f"Kullanıcının kendi departmanı: {benim_departmanim}\n"
            f"Kullanıcının kendi pozisyonu: {benim_pozisyonum}\n"
            f"Şirkette toplam {calisan_sayisi} çalışan ve {departman_sayisi} departman bulunmaktadır.{dept_bilgi}\n"
            f"Departman Listesi (İsim ve ID Eşleştirmesi): {departman_listesi_str}\n"
            f"Kullanıcının kendi ID'si: {istek.kullanici_id}\n"
            f"Eğer yönetici kendi performansını veya görevlerini sorarsa bu ID'yi gizlice kullan.\n"
            f"Ayrıca, isim eşleştirmeleri otomatik yapılmaktadır. Ancak sistem isim-id ve departman-id eşleştirmesini senin için yapıyor. Tool çağırırken her zaman bu listedeki ID'leri kullan."
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
