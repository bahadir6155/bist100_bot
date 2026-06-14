import os
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from database import init_db, get_tickers, get_history
from agents.orchestrator import OrchestratorAgent, SCAN_PROGRESS
from config.bist100_symbols import BIST100_SYMBOLS

app = FastAPI(title="BIST100 AI Bot API")

@app.on_event("startup")
async def startup_event():
    await init_db()

# Monting static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

class AnalyzeRequest(BaseModel):
    tickers: list[str]

@app.get("/api/tickers")
async def api_get_tickers():
    tickers = await get_tickers()
    return {"tickers": tickers}

@app.get("/api/history/{ticker}")
async def api_get_history(ticker: str):
    history = await get_history(ticker.upper())
    if not history:
        return {"history": []}
    return {"history": history}

@app.get("/api/progress")
async def api_get_progress():
    return SCAN_PROGRESS

@app.get("/api/chart/{ticker}")
async def api_get_chart(ticker: str):
    import yfinance as yf
    try:
        # Yahoo Finance uses .IS suffix for Borsa Istanbul
        stock = yf.Ticker(f"{ticker.upper()}.IS")
        hist = stock.history(period="6mo")
        if hist.empty:
            return {"dates": [], "prices": []}
        
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        prices = hist['Close'].tolist()
        return {"dates": dates, "prices": prices}
    except Exception as e:
        return {"dates": [], "prices": [], "error": str(e)}

@app.post("/api/analyze")
async def api_analyze(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    orchestrator = OrchestratorAgent()
    tickers_to_analyze = req.tickers if req.tickers else BIST100_SYMBOLS
    background_tasks.add_task(orchestrator.run_all, tickers_to_analyze)
    return {"message": f"Analysis started for {len(tickers_to_analyze)} tickers."}
