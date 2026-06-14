import aiosqlite
import datetime
from models.schemas import AnalysisResult, CalculatedMetrics, MacroData, RawStockData

DB_PATH = "analyses.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                price REAL,
                net_profit REAL,
                total_assets REAL,
                total_liabilities REAL,
                ebitda REAL,
                outstanding_shares REAL,
                current_assets REAL,
                short_term_liabilities REAL,
                equity REAL,
                pe_ratio REAL,
                pb_ratio REAL,
                gross_profit REAL,
                operating_profit REAL,
                roe REAL,
                inflation_rate REAL,
                policy_rate REAL,
                risk_score INTEGER,
                signal TEXT,
                commentary TEXT,
                is_successful BOOLEAN,
                error_message TEXT
            )
        """)
        await db.commit()

async def save_analysis(
    ticker: str,
    raw_data: RawStockData,
    metrics: CalculatedMetrics,
    macro_data: MacroData,
    result: AnalysisResult
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO analyses (
                ticker, price, net_profit, total_assets, total_liabilities, ebitda,
                outstanding_shares, current_assets, short_term_liabilities, equity,
                pe_ratio, pb_ratio, gross_profit, operating_profit, roe,
                inflation_rate, policy_rate, risk_score, signal, commentary,
                is_successful, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker,
            raw_data.price if raw_data else 0.0,
            raw_data.net_profit if raw_data else 0.0,
            raw_data.total_assets if raw_data else 0.0,
            raw_data.total_liabilities if raw_data else 0.0,
            raw_data.ebitda if raw_data else 0.0,
            raw_data.outstanding_shares if raw_data else 0.0,
            raw_data.current_assets if raw_data else 0.0,
            raw_data.short_term_liabilities if raw_data else 0.0,
            raw_data.equity if raw_data else 0.0,
            metrics.pe_ratio if metrics else 0.0,
            metrics.pb_ratio if metrics else 0.0,
            raw_data.gross_profit if raw_data else 0.0,
            raw_data.operating_profit if raw_data else 0.0,
            raw_data.roe if raw_data else 0.0,
            macro_data.inflation_rate if macro_data else 0.0,
            macro_data.policy_rate if macro_data else 0.0,
            result.risk_score if result else 0,
            result.signal if result else "",
            result.commentary if result else "",
            result.is_successful if result else False,
            result.error_message if result else ""
        ))
        await db.commit()

async def get_tickers():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT DISTINCT ticker FROM analyses ORDER BY ticker ASC") as cursor:
            rows = await cursor.fetchall()
            return [row["ticker"] for row in rows]

async def get_history(ticker: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM analyses WHERE ticker = ? ORDER BY timestamp DESC", (ticker,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
