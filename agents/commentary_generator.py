import logging
import json
import asyncio
import aiohttp
import time
from openai import AsyncOpenAI

from models.schemas import CalculatedMetrics, AnalysisResult, MacroData, RawStockData
from config.settings import settings

logger = logging.getLogger("CommentaryGenerator")

# Global variables for Gemini Rate Limiting
GEMINI_LOCK = asyncio.Lock()
LAST_GEMINI_CALL = 0.0

class CommentaryGeneratorAgent:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.gemini_key = settings.GEMINI_API_KEY
        self.provider = settings.LLM_PROVIDER.lower()
        if self.provider == "local":
            self.client = AsyncOpenAI(api_key="local-key", base_url=settings.LOCAL_LLM_URL)
        elif self.provider == "openai" and self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None

    async def generate_commentary(
        self, 
        session: aiohttp.ClientSession,
        raw_data: RawStockData,
        metrics: CalculatedMetrics, 
        macro_data: MacroData,
        risk_score: int
    ) -> AnalysisResult:
        
        news_context = ""
        if raw_data.recent_news:
            news_context = "\nSon KAP Gelişmeleri / Piyasa Haberleri:\n" + "\n".join([f"- {news}" for news in raw_data.recent_news])

        prompt = f"""
Rol: Baş Finans Analisti ve Yatırım Danışmanı.

Görev: BIST100 hissesi '{metrics.ticker}' için detaylı, ancak BORSAYA YENİ BAŞLAYAN BİR İNSANIN kolayca anlayabileceği seviyede kapsamlı bir temel analiz raporu oluştur. Yorum uzunluğu kısıtlaması yoktur, önemli olan sade, eğitici ve kapsamlı olmasıdır. Tüm terimleri kısaca açıkla. Kararını (AL/TUT/KAÇIN) SADECE aşağıdaki finansal verilere dayanarak, sağlam temellere oturtarak ver.

Şirket Verileri:
- F/K Oranı: {metrics.pe_ratio}
- F/DD Oranı: {metrics.pb_ratio}
- Borç/Özsermaye Oranı: {metrics.debt_to_equity}
- Cari Oran: {metrics.current_ratio}
- Brüt Kâr: {raw_data.gross_profit} TL
- Esas Faaliyet Kârı: {raw_data.operating_profit} TL
- Net Kâr: {raw_data.net_profit} TL
- Özkaynak Kârlılığı (ROE): {raw_data.roe}
- Sistem Risk Skoru: {risk_score} / 100

Makroekonomik Veriler:
- Güncel TÜFE (Enflasyon): %{macro_data.inflation_rate}
- TCMB Politika Faizi: %{macro_data.policy_rate}
{news_context}

Kurallar:
1. Yanıtın TAMAMEN TÜRKÇE olması zorunludur. İngilizce kelime/cümle YASAKTIR.
2. Açıklamalar eğitici, anlaşılır ve detaylı olmalı. Cümle sayısında bir kısıtlama YOKTUR, açıklayıcı olun.
3. AL, TUT veya KAÇIN sinyalini finansal gerçeklere tam olarak bağdaştırarak karar ver.
4. Çıktıyı tam olarak aşağıdaki JSON şemasında dön:
   {{
     "signal": "AL, TUT veya KAÇIN",
     "commentary": "Kapsamlı ve anlaşılır yatırımcı yorumu..."
   }}
"""

        if self.provider == "local" or self.provider == "openai":
            if not self.client:
                return AnalysisResult(
                    ticker=metrics.ticker,
                    is_successful=False,
                    error_message="LLM İstemcisi başlatılamadı. API Key veya ayarları kontrol edin."
                )
            try:
                model = settings.LOCAL_LLM_MODEL if self.provider == "local" else "gpt-4o-mini"
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                data = json.loads(response.choices[0].message.content.strip())
                return AnalysisResult(
                    ticker=metrics.ticker,
                    signal=data.get("signal", "TUT"),
                    commentary=data.get("commentary", ""),
                    risk_score=risk_score,
                    is_successful=True
                )
            except Exception as e:
                logger.error(f"{metrics.ticker}: LLM Hatası ({self.provider}) - {e}")
                return AnalysisResult(
                    ticker=metrics.ticker,
                    is_successful=False,
                    error_message=f"LLM API Hatası: {e}"
                )

        elif self.provider == "gemini" and self.gemini_key and not self.gemini_key.startswith("your_"):
            
            # Rate Limiter: Gemini Free Tier 15 RPM sınırını aşmamak için istekleri 4.2 saniye aralıklarla sıraya diziyoruz.
            global LAST_GEMINI_CALL
            async with GEMINI_LOCK:
                now = time.time()
                elapsed = now - LAST_GEMINI_CALL
                if elapsed < 4.2:
                    delay = 4.2 - elapsed
                    LAST_GEMINI_CALL = now + delay
                else:
                    delay = 0
                    LAST_GEMINI_CALL = now
            
            if delay > 0:
                await asyncio.sleep(delay)

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={self.gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": {
                        "type": "OBJECT",
                        "properties": {
                            "signal": {"type": "STRING"},
                            "commentary": {"type": "STRING"}
                        },
                        "required": ["signal", "commentary"]
                    }
                }
            }
            
            # 3 kez tekrar deneme (retry) mekanizması
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Uzun promptlar ve yanıtlar için timeout artırıldı (120 saniye)
                    timeout = aiohttp.ClientTimeout(total=120)
                    async with session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout) as response:
                        if response.status == 200:
                            res_json = await response.json()
                            text = res_json['candidates'][0]['content']['parts'][0]['text']
                            data = json.loads(text.strip())
                            return AnalysisResult(
                                ticker=metrics.ticker,
                                signal=data.get("signal", "TUT"),
                                commentary=data.get("commentary", ""),
                                risk_score=risk_score,
                                is_successful=True
                            )
                        elif response.status == 429:
                            error_text = await response.text()
                            if attempt < max_retries - 1:
                                await asyncio.sleep(5 * (attempt + 1))
                                continue
                            
                            # Parse the exact error from Google if possible
                            exact_error = "Bilinmeyen Kota Hatası"
                            try:
                                err_json = json.loads(error_text)
                                exact_error = err_json.get("error", {}).get("message", error_text)
                            except:
                                exact_error = error_text

                            return AnalysisResult(
                                ticker=metrics.ticker,
                                is_successful=False,
                                error_message=f"Gemini API Kota/Ödeme Hatası (HTTP 429): {exact_error}"
                            )
                        else:
                            error_text = await response.text()
                            return AnalysisResult(
                                ticker=metrics.ticker,
                                is_successful=False,
                                error_message=f"Gemini API Hatası: HTTP {response.status} - {error_text}"
                            )
                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    return AnalysisResult(
                        ticker=metrics.ticker,
                        is_successful=False,
                        error_message="Gemini API Zaman Aşımı (120sn deneme başarısız)"
                    )
                except Exception as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)
                        continue
                    return AnalysisResult(
                        ticker=metrics.ticker,
                        is_successful=False,
                        error_message=f"Gemini Bağlantı Hatası: {e}"
                    )
        else:
            return AnalysisResult(
                ticker=metrics.ticker,
                is_successful=False,
                error_message="Geçerli bir LLM API anahtarı veya sağlayıcı bulunamadı. Fallback tamamen devre dışıdır."
            )
