# BIST100 Otonom Temel Analiz Botu

Bu bot, BIST100 endeksindeki hisselerin finansal verilerini analiz eder, oranları hesaplar, sektörel ve genel risk analizini gerçekleştirir ve son olarak doğal dilde (Türkçe) yatırımcı dostu bir günlük yorum üretir.

## Özellikler
- **DataCollectorAgent:** KAP ve finans sağlayıcılarından ham verileri çeker.
- **FundamentalsCalculatorAgent:** F/K, F/DD, Cari Oran ve Kaldıraç oranlarını hesaplar.
- **CommentaryGeneratorAgent:** OpenAI API desteği (veya otomatik kural tabanlı fallback) ile 3 cümlelik Türkçe yorum üretir.
- **OrchestratorAgent:** Tüm veri işleme, analiz ve yorumlama adımlarını koordine eder.

## Proje Kurulumu
Bir terminal açarak projenin dizinine gidin ve aşağıdaki komutla sanal ortamı kurup paketleri yükleyin:
```bash
make setup
```

## Testlerin Çalıştırılması
Hesaplama ve yorumlama mantığını test etmek için:
```bash
make test
```

## Çalıştırma
Sistemi tek seferlik çalıştırmak ve bülteni yazdırmak için:
```bash
make run
```
