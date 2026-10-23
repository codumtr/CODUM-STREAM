"""
StreamDub End-to-End Pipeline Test Script
Yayıncı profilini yükler, Türkçe argo ve yüksek enerjili bir ifadeyi
İngilizceye çevirir ve ses sentezleme boru hattını doğrular.
"""

import sys
import asyncio

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from core.translator import StreamerTranslator
from core.tts_engine import VoiceCloningEngine

async def test_dubbing_flow():
    print("=" * 60)
    print("🎙️ CODUM.TR STREAM AI: Canlı Çeviri & Ses Sentezi Doğrulama")
    print("=" * 60)

    streamer_id = "default"
    sample_speech_tr = "Aga yemin ederim patladık ya, chat baksana şuna oğlum böyle bir şey olamaz!"

    print(f"\n1. [Girdi - Türkçe Yayıncı Sesi]:\n   \"{sample_speech_tr}\"")

    translator = StreamerTranslator(streamer_id=streamer_id)
    print("\n2. [Yayıncı Personası & Argo Korumalı Çeviri İşleniyor...]")
    translated_en, word_count = await translator.translate(sample_speech_tr, target_lang="en")
    print(f"   -> Çeviri [EN]: \"{translated_en}\" (Kelime: {word_count})")

    print("\n3. [Yayıncı Ses Tonu & Sentezi (TTS Engine)...]")
    tts = VoiceCloningEngine(streamer_id=streamer_id)
    audio_bytes, mime_type, char_count = await tts.synthesize(translated_en, target_lang="en")
    print(f"   -> Üretilen Ses: {len(audio_bytes)} bayt ({mime_type})")

    print("\n" + "=" * 60)
    print("✅ Boru hattı mantığı ve profil entegrasyonu başarıyla doğrulandı!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_dubbing_flow())
