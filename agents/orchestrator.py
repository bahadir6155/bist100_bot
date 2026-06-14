import logging
import asyncio
import aiohttp
from agents.data_collector import DataCollectorAgent
from agents.fundamentals_calculator import FundamentalsCalculatorAgent
from agents.commentary_generator import CommentaryGeneratorAgent
from models.schemas import AnalysisResult
from database import save_analysis

logger = logging.getLogger("Orchestrator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

SCAN_PROGRESS = {
    "is_running": False,
    "total": 0,
    "completed": 0,
    "current_ticker": "",
    "successful": 0,
    "failed": 0
}

class OrchestratorAgent:
    def __init__(self):
        self.collector = DataCollectorAgent()
        self.calculator = FundamentalsCalculatorAgent()
        self.commentator = CommentaryGeneratorAgent()

    async def run_pipeline_for_stock(self, session: aiohttp.ClientSession, ticker: str, macro_data, sem: asyncio.Semaphore) -> AnalysisResult:
        async with sem:
            global SCAN_PROGRESS
            SCAN_PROGRESS["current_ticker"] = ticker
            logger.info(f"{ticker} işleniyor...")
            # 1. Fetch Data
            try:
                raw_data = await self.collector.fetch_stock_data(session, ticker)
            except Exception as e:
                logger.error(f"{ticker}: Veri toplama hatası: {e}")
                return AnalysisResult(
                    ticker=ticker,
                    is_successful=False,
                    error_message=f"Veri Çekilemedi: {e}"
                )

            # 2. Calculate metrics
            try:
                metrics = self.calculator.calculate_metrics(raw_data)
            except Exception as e:
                logger.error(f"{ticker}: Metrik hesaplama hatası: {e}")
                return AnalysisResult(
                    ticker=ticker,
                    is_successful=False,
                    error_message=f"Hesaplama Hatası: {e}"
                )

            # 3. Assess risk score
            try:
                de_factor = min(metrics.debt_to_equity * 25, 50) if metrics.debt_to_equity != 999.9 else 50
                cr_factor = max((2.0 - metrics.current_ratio) * 25, 0) if metrics.current_ratio != 0.0 else 25
                risk_score = int(10 + de_factor + cr_factor)
                risk_score = min(max(risk_score, 1), 100)
            except Exception as e:
                logger.error(f"{ticker}: Risk skoru hatası: {e}")
                risk_score = 50

            # 4. Generate commentary
            try:
                result = await self.commentator.generate_commentary(session, raw_data, metrics, macro_data, risk_score)
                await save_analysis(ticker, raw_data, metrics, macro_data, result)
                SCAN_PROGRESS["completed"] += 1
                SCAN_PROGRESS["successful"] += 1
                return result
            except Exception as e:
                logger.error(f"{ticker}: Yorum üretimi hatası: {e}")
                error_result = AnalysisResult(
                    ticker=ticker,
                    is_successful=False,
                    error_message=f"Yorum Üretimi Hatası: {e}"
                )
                await save_analysis(ticker, raw_data, metrics, macro_data, error_result)
                SCAN_PROGRESS["completed"] += 1
                SCAN_PROGRESS["failed"] += 1
                return error_result

    async def run_all(self, tickers: list):
        global SCAN_PROGRESS
        SCAN_PROGRESS["is_running"] = True
        SCAN_PROGRESS["total"] = len(tickers)
        SCAN_PROGRESS["completed"] = 0
        SCAN_PROGRESS["successful"] = 0
        SCAN_PROGRESS["failed"] = 0
        
        logger.info(f"Toplam {len(tickers)} hisse için asenkron işlem başlatılıyor...")
        
        async with aiohttp.ClientSession() as session:
            # Fetch macro data once
            logger.info("Makro veriler çekiliyor (TCMB)...")
            macro_data = await self.collector.fetch_macro_indicators(session)
            logger.info(f"Makro Veriler - Enflasyon: %{macro_data.inflation_rate}, Politika Faizi: %{macro_data.policy_rate}")
            
            # API rate limitlere takılmamak için eşzamanlı istek sınırlandırıldı
            # Gemini Free tier dakikada 15 istek sınırı olduğu için Semaphore 3'e düşürüldü.
            sem = asyncio.Semaphore(3)
            
            tasks = [self.run_pipeline_for_stock(session, ticker, macro_data, sem) for ticker in tickers]
            results = await asyncio.gather(*tasks)
            
        results = sorted(results, key=lambda x: x.ticker)
        logger.info(f"Analiz tamamlandı. Başarılı: {sum(1 for r in results if r.is_successful)}/{len(results)}")
        SCAN_PROGRESS["is_running"] = False
        return results
