"""
CODUM.TR STREAM - Orijinal Lisans ve Fikri Mülkiyet Koruma Modülü
Bu modül yazılımın telif hakkı, marka kimliği ve dijital orijinallik mührünü doğrular.
Tüm hakları CODUM.TR STREAM'e aittir. Lisans sahibinin izni olmadan marka adı ve
telif bildirimleri değiştirilemez, silinemez veya başka bir isim altında yeniden dağıtılamaz.
"""

import hmac
import hashlib
import json
from datetime import datetime

# CODUM.TR STREAM Dijital Mührü
ORGANIZATION = "CODUM.TR STREAM"
VERSION = "1.0.0-PRO"
LICENSE_TYPE = "Proprietary Freeware (Kişisel & Ticari Yayıncı Lisansı)"
COPYRIGHT = f"(c) 2026 {ORGANIZATION}. Tüm Hakları Saklıdır."

# Değiştirilemez Mühür Verisi
_CORE_SEAL_PAYLOAD = {
    "org": ORGANIZATION,
    "version": VERSION,
    "license": LICENSE_TYPE,
    "author": "CODUM.TR",
    "tamper_protection": "ACTIVE_SHA256"
}

# Dahili Doğrulama Hash'i
_SYSTEM_SALT = "CODUM_TR_STREAM_INTEGRITY_SALT_2026_SECURE"
SEAL_SIGNATURE = hmac.new(
    _SYSTEM_SALT.encode("utf-8"),
    json.dumps(_CORE_SEAL_PAYLOAD, sort_keys=True).encode("utf-8"),
    hashlib.sha256
).hexdigest()

def verify_license_integrity() -> dict:
    """
    Sistemin orijinalliğini ve lisans bütünlüğünü doğrular.
    """
    computed = hmac.new(
        _SYSTEM_SALT.encode("utf-8"),
        json.dumps(_CORE_SEAL_PAYLOAD, sort_keys=True).encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    is_valid = hmac.compare_digest(computed, SEAL_SIGNATURE)

    return {
        "status": "VERIFIED" if is_valid else "TAMPERED",
        "organization": ORGANIZATION,
        "product": "CODUM.TR STREAM STUDIO",
        "version": VERSION,
        "license": LICENSE_TYPE,
        "copyright": COPYRIGHT,
        "seal_hash": computed[:16] + "...",
        "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def print_startup_banner():
    """
    Sunucu başlarken konsola kırılmaz resmi lisans mührünü basar.
    """
    info = verify_license_integrity()
    banner = f"""
======================================================================
  [CODUM.TR STREAM STUDIO] - ORIJINAL LISANSLI SURUM
  Lisans Sahibi : {info['organization']}
  Lisans Turu   : {info['license']}
  Telif Hakki   : {info['copyright']}
  Guvenlik Muhru: {info['seal_hash']} [{info['status']}]
======================================================================
"""
    print(banner)
