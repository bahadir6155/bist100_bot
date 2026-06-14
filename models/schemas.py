from pydantic import BaseModel, Field
from typing import List, Optional

class MacroData(BaseModel):
    inflation_rate: float = Field(default=0.0, description="TÜFE (Yıllık Enflasyon)")
    policy_rate: float = Field(default=0.0, description="TCMB Politika Faizi")

class RawStockData(BaseModel):
    ticker: str
    price: float
    net_profit: float
    total_assets: float
    total_liabilities: float
    ebitda: float
    outstanding_shares: float
    current_assets: float = 0.0
    short_term_liabilities: float = 0.0
    equity: float = 0.0
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    gross_profit: float = 0.0
    operating_profit: float = 0.0
    roe: float = 0.0
    recent_news: List[str] = []

class CalculatedMetrics(BaseModel):
    ticker: str
    pe_ratio: float
    pb_ratio: float
    debt_to_equity: float
    current_ratio: float

class AnalysisResult(BaseModel):
    ticker: str
    is_successful: bool = Field(default=True, description="Analiz başarılı oldu mu?")
    error_message: str = Field(default="", description="Başarısızsa hata detayı")
    signal: str = Field(default="", description="AL, TUT veya KAÇIN sinyali")
    commentary: str = Field(default="", description="Temel analize dayalı yorum")
    risk_score: int = Field(default=0)
