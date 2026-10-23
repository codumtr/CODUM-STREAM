# Katkıda Bulunma Rehberi (Contributing Guidelines)

**CODUM.TR STREAM** projesine katkıda bulunmak istediğiniz için teşekkürler!

Proje yayıncılar için ücretsiz olarak sunulmakta olup, topluluk katkılarına açıktır. Lütfen katkı sağlamadan önce aşağıdaki kuralları inceleyin:

---

### 1. Kültürel Deyim ve Argo Katkıları (Language Intelligence)
Türkçe oyun ve yayıncılık argosunu geliştirmek için en değerli katkı yeni deyim ve jargon eklemeleridir:
* `core/language_intelligence.py` dosyasındaki `CULTURAL_IDIOM_DATABASE` sözlüğüne yeni kalıplar ekleyebilirsiniz.
* Eklenen karşılıkların motamot (harfi harfine) olmamasına, İngilizce konuşan Twitch/Kick yayıncılarının doğal olarak kullandığı ifadeler olmasına özen gösterin.

### 2. Kod Standartları
* Python kodu PEP 8 standartlarına uygun olmalıdır.
* Asenkron fonksiyonlarda (`async`/`await`) bloklayıcı kütüphaneler (`time.sleep` veya senkron `requests`) kullanılmamalı, daima `asyncio` ve `aiohttp` tercih edilmelidir.
* Tüm hassas API anahtarları `.env` üzerinden yönetilmelidir; kodun içine hiçbir zaman anahtar gömülmemelidir.

### 3. Fikri Mülkiyet ve Marka Koruması
* Katkıda bulunurken **CODUM.TR STREAM** telif bildirimleri ve `core/license_guard.py` dosyasındaki orijinallik mührü korunmalıdır.
* Projeyi kopyalayıp başka bir marka adı altında yayınlamak lisans ihlali teşkil eder.

### 4. Pull Request (PR) Süreci
1. Projeyi Fork edin.
2. Yeni bir özellik dalı (feature branch) oluşturun: `git checkout -b feature/yeni-deyimler`.
3. Değişikliklerinizi commit edin: `git commit -m "feat: 10 yeni turkce argo deyim eklendi"`.
4. Dalınızı pushlayın: `git push origin feature/yeni-deyimler`.
5. Ana depoya Pull Request açın.
