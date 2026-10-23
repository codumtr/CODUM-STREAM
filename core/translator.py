"""
Streamer Personality & Culture Engine Translator - CODUM Production
Yayıncının seçtiği AI motorunu (Gemini 2.0 Flash veya Groq LLaMA 3.3) kesinlikle dikkate alır.
Language Intelligence sistemi ile motamot çeviri yerine kültürel adaptasyon ve doğal gramer uygular.
"""

import os
import json
import aiohttp
from pathlib import Path
from config import engine_config
from core.language_intelligence import LanguageIntelligence

class StreamerTranslator:
    def __init__(self, streamer_id: str = "default", backend: str = None):
        self.streamer_id = streamer_id
        # Yayıncının seçtiği motor (Varsayılan config'den veya "auto", "gemini", "groq")
        self.backend = (backend or engine_config.TRANSLATOR_BACKEND).lower().strip()
        self.profile = self._load_profile(streamer_id)
        self.slang_mode = "gamer_hype" # "gamer_hype", "casual", "clean"
        self.custom_glossary = {}
        self.lang_intel = LanguageIntelligence()

    def _load_profile(self, streamer_id: str) -> dict:
        profile_path = Path("profiles") / f"{streamer_id}.json"
        if profile_path.exists():
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "display_name": "Streamer",
            "llm_persona_prompt": "You are a real-time live gaming streamer dubber.",
            "slang_dictionary": {}
        }

    def set_ai_engine(self, engine_name: str):
        """Panelden canlı olarak yapay zekâ motorunu değiştirir."""
        clean_name = engine_name.lower().strip()
        if clean_name in ["gemini", "groq", "auto", "llama"]:
            self.backend = "groq" if clean_name == "llama" else clean_name
            print(f"🔄 [AI Engine Swapped] Çeviri Motoru Değiştirildi: {self.backend.upper()}")

    def update_settings(self, slang_mode: str = None, glossary: dict = None, engine_name: str = None):
        if slang_mode in ["gamer_hype", "casual", "clean"]:
            self.slang_mode = slang_mode
        if glossary and isinstance(glossary, dict):
            self.custom_glossary.update(glossary)
        if engine_name:
            self.set_ai_engine(engine_name)

    def _build_prompt(self, target_lang: str, is_high_energy: bool) -> str:
        base_prompt = self.lang_intel.build_intelligence_prompt(target_lang, self.slang_mode, self.custom_glossary)
        if is_high_energy:
            base_prompt += "\n\n🔥 THE STREAMER IS SCREAMING / HYPED! Match their screaming energy with exclamation marks and intense gamer banter!"
        return base_prompt

    async def translate(self, text: str, target_lang: str = "en", is_high_energy: bool = False, health_monitor = None) -> tuple[str, int]:
        """
        Kullanıcının belirlediği motoru ÖNCELİKLİ çalıştırır.
        Hata durumunda diğer motora akıllı failover yapar.
        """
        clean_text = text.strip() if text else ""
        if not clean_text:
            return "", 0

        word_count = len(clean_text.split())
        prompt = self._build_prompt(target_lang, is_high_energy)

        gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or engine_config.GEMINI_API_KEY
        groq_key = os.getenv("GROQ_API_KEY", "").strip() or engine_config.GROQ_API_KEY

        # 1. Kullanıcı GEMINI Seçtiyse -> Önce Gemini'yi çalıştır
        if self.backend == "gemini":
            if gemini_key:
                translated = await self._translate_gemini(clean_text, prompt, gemini_key)
                if translated:
                    return translated, word_count
                elif health_monitor:
                    health_monitor.trigger_failover("LLM", "Google Gemini 2.0 Flash", "Groq LLaMA 3.3", "Zaman aşımı / API hatası")

            # Gemini başarısız veya anahtarsızsa -> Groq'a geç
            if groq_key:
                translated = await self._translate_groq(clean_text, prompt, groq_key)
                if translated:
                    return translated, word_count

        # 2. Kullanıcı GROQ veya AUTO Seçtiyse -> Önce Groq LLaMA 3.3'ü çalıştır (~120ms)
        else:
            if groq_key:
                translated = await self._translate_groq(clean_text, prompt, groq_key)
                if translated:
                    return translated, word_count
                elif health_monitor:
                    health_monitor.trigger_failover("LLM", "Groq LLaMA 3.3", "Google Gemini 2.0 Flash", "Zaman aşımı")

            # Groq başarısız veya anahtarsızsa -> Gemini'ye geç
            if gemini_key:
                translated = await self._translate_gemini(clean_text, prompt, gemini_key)
                if translated:
                    return translated, word_count

        # 3. İki API de yoksa veya çöktüyse -> Kültürel Deyim Veritabanı (Fallback)
        fallback = self._rule_based_fallback(clean_text)
        return fallback, word_count

    async def _translate_groq(self, text: str, prompt: str, api_key: str = None) -> str:
        groq_key = api_key or os.getenv("GROQ_API_KEY", "").strip() or engine_config.GROQ_API_KEY
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.25,
            "max_tokens": 100
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=2.5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        res = data["choices"][0]["message"]["content"].strip()
                        return res.replace('"', '').strip()
        except Exception:
            pass
        return ""

    async def _translate_gemini(self, text: str, prompt: str, api_key: str = None) -> str:
        gemini_key = api_key or os.getenv("GEMINI_API_KEY", "").strip() or engine_config.GEMINI_API_KEY
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": f"{prompt}\n\nTRANSLATE THIS TURKISH UTTERANCE:\n{text}"}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 80}
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=2.5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        res = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        return res.replace('"', '').strip()
        except Exception:
            pass
        return ""

    def _rule_based_fallback(self, text: str) -> str:
        """API'ler kapalıyken bile motamot değil kültürel deyim karşılıklarıyla çevirir"""
        combined = dict(self.lang_intel.idiom_db)
        combined.update(self.custom_glossary)
        lower_text = text.lower().strip()

        # Deyim eşleşmesi var mı?
        for idiom, replacement in combined.items():
            if idiom in lower_text:
                lower_text = lower_text.replace(idiom, replacement)

        return lower_text
