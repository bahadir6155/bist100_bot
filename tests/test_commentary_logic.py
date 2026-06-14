import pytest
import asyncio
import aiohttp
from models.schemas import CalculatedMetrics, MacroData, RawStockData
from agents.commentary_generator import CommentaryGeneratorAgent

def test_commentary_generator_missing_api_fails():
    commentator = CommentaryGeneratorAgent()
    # Zorla hata almak için ayarları bozuyoruz
    commentator.provider = "openai"
    commentator.client = None
    
    metrics = CalculatedMetrics(
        ticker="THYAO",
        pe_ratio=7.2,
        pb_ratio=1.1,
        debt_to_equity=1.5,
        current_ratio=1.6
    )
    macro = MacroData(inflation_rate=50.0, policy_rate=45.0)
    raw = RawStockData(
        ticker="THYAO", price=100.0, net_profit=100.0,
        total_assets=1000.0, total_liabilities=500.0, ebitda=50.0,
        outstanding_shares=100.0, gross_profit=200.0, operating_profit=150.0,
        roe=0.2, recent_news=[]
    )
    
    async def run_gen():
        async with aiohttp.ClientSession() as session:
            return await commentator.generate_commentary(session, raw, metrics, macro, risk_score=35)
            
    result = asyncio.run(run_gen())
    
    # Fallback kaldırıldığı için API olmadan is_successful False dönmelidir
    assert result.is_successful is False
    assert "LLM İstemcisi başlatılamadı" in result.error_message or "bulunamadı" in result.error_message
