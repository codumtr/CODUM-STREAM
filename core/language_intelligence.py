"""
Language Intelligence & Cultural Adaptation System - CODUM Production
Türk yayıncıların kültürel kalıplarını, deyimlerini ve anlık reaksiyonlarını
İngilizce konuşan bir yayıncının doğal biçimde söyleyeceği kalıplara dönüştürür.
Anlamı bozmadan, motamot (harfi harfine) çevirinin saçmalamasını engeller.
"""

from typing import Dict

# Türk Yayın Kültürü & Deyimsel Karşılıklar Veritabanı
CULTURAL_IDIOM_DATABASE: Dict[str, str] = {
    # Reaksiyonlar & Tepkiler
    "kafayı yersin": "that's completely insane",
    "kafayı yiyeceğim": "I'm losing my mind",
    "gözünü seveyim": "come on man, please",
    "hadi bakayım": "let's go, let's get it",
    "helal olsun": "respect bro, well played",
    "harbi mi": "no shot, are you serious?",
    "yok artık": "no way, that's impossible",
    "patladık": "we're so cooked",
    "sıctık": "we're totally done for",
    "içim elvermiyor": "I just can't bring myself to do it",
    "ağzına sağlık": "well said brother",
    "nazar değmesin": "knock on wood",
    "yapma be": "c'mon don't do this to me",
    "ayıp ettin": "you did me dirty",
    "eyvallah": "much love, appreciate it",
    "adamsın": "you're a legend",
    "dayı": "man",
    "aga": "bro",
    "kanka": "dude",
    "valla": "I swear to god",
    "yemin ederim": "on god, for real",
    "aynen öyle": "facts, exactly that",
    "kafam almıyor": "I cannot wrap my head around this",
    "yok yere": "for absolutely no reason",
    "boş yapma": "stop capping, stop talking nonsense",
    "dalga mı geçiyorsun": "are you trolling me right now?",
    "kendine gel": "get your head in the game",
    "şaka mısın": "are you for real right now?",
    "yalan yok": "not gonna lie, ngl"
}

class LanguageIntelligence:
    def __init__(self):
        self.idiom_db = dict(CULTURAL_IDIOM_DATABASE)

    def add_custom_idiom(self, tr_phrase: str, en_phrase: str):
        self.idiom_db[tr_phrase.lower().strip()] = en_phrase.strip()

    def build_intelligence_prompt(self, target_lang: str, style_mode: str, custom_glossary: dict = None) -> str:
        """
        LLM için derin kültürel ve gramatik uyarlama yönergesi üretir.
        """
        combined = dict(self.idiom_db)
        if custom_glossary:
            combined.update(custom_glossary)

        rules_list = "\n".join([f"- \"{k}\" ➔ \"{v}\"" for k, v in list(combined.items())[:35]])

        return (
            f"YOU ARE A HIGH-TIER LIVE GAMING STREAM DUBBING TRANSLATOR TO {target_lang.upper()}.\n"
            "YOUR OBJECTIVE:\n"
            "Do NOT translate literally word-by-word! Translate what the Turkish streamer MEANS into "
            "what a native English gamer/streamer on Twitch/Kick would naturally scream, say, or laugh about.\n\n"
            "CRITICAL CULTURAL ADAPTATION RULES:\n"
            f"{rules_list}\n\n"
            "GRAMMAR & FLOW REQUIREMENTS:\n"
            "1. Output ONLY the spoken translation. Zero explanations, zero quotes.\n"
            "2. Keep it punchy, rhythmic, and synchronized with live speech timing.\n"
            "3. If the Turkish speaker uses sarcasm or self-deprecating humor, preserve the exact comedic timing.\n"
            "4. NEVER output raw Turkish words in the English translation.\n"
            "5. If the utterance is unintelligible noise, return an empty string."
        )
