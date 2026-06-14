# BIST100 Otonom Temel Analiz Botu - Proje Raporu

BIST100 endeksindeki şirketlerin günlük temel analiz verilerini toplayan, rasyoları hesaplayan, risk puanı oluşturan ve Türkçe dilinde yatırımcı dostu yorumlar ve kararlar (AL, TUT, KAÇIN) üreten çoklu-ajanlı bot projesi başarıyla kurulmuş ve test edilmiştir.

## Proje Klasör Yapısı
Proje, `C:\Users\bahad\Desktop\bist100_fundamentals_bot\` dizini altında oluşturulmuştur:
- [main.py](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/main.py): Uygulama giriş noktası ve günlük bülten basımı.
- [config/settings.py](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/config/settings.py): Yapılandırma ve çevre değişkeni sınıfları.
- [config/secrets.template](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/config/secrets.template): Çevre değişkeni şablonu.
- [models/schemas.py](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/models/schemas.py): Pydantic veri şemaları.
- [agents/data_collector.py](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/agents/data_collector.py): Ham finansal veri çekim ajanı.
- [agents/fundamentals_calculator.py](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/agents/fundamentals_calculator.py): Temel finansal oran hesaplama ajanı.
- [agents/commentary_generator.py](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/agents/commentary_generator.py): LLM entegrasyonu ve kural tabanlı fallback yorum ajanı.
- [agents/orchestrator.py](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/agents/orchestrator.py): Ajan iş akışı koordinatörü.
- [tests/test_data_integrity.py](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/tests/test_data_integrity.py): Rasyo ve veri doğruluk testleri.
- [tests/test_commentary_logic.py](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/tests/test_commentary_logic.py): Yorum uzunluğu ve mantık testleri.
- [requirements.txt](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/requirements.txt): Python bağımlılıkları.
- [Dockerfile](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/Dockerfile): Docker konteyner ayarları.
- [Makefile](file:///C:/Users/bahad/Desktop/bist100_fundamentals_bot/Makefile): Kolay kurulum ve çalıştırma komutları.

## Kurulum ve Çalıştırma Adımları

1. **Bağımlılıkların Kurulması (Sanal Ortam):**
   ```bash
   make setup
   ```

2. **Testlerin Çalıştırılması:**
   ```bash
   make test
   ```

3. **Uygulamanın Tetiklenmesi (Günlük Rapor Üretimi):**
   ```bash
   make run
   ```

## Test ve Çalışma Sonuçları
Tüm birim testleri başarıyla geçmiştir. Uygulama çalıştırıldığında alınan test çıktısı:
- **THYAO:** TUT Sinyali (Dengeli finansal yapı, dengeli likidite)
- **EREGL:** AL Sinyali (Düşük F/K, yüksek cari oran ve güçlü likidite yapısı)
- **ASELS:** AL Sinyali (Düşük F/K ve güvenli cari oran seviyesi)
- **TUPRS:** TUT Sinyali (Orta risk seviyesi, dengeli rasyolar)
