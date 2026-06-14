import logging
import re
import unicodedata
import xml.etree.ElementTree as ET
import urllib.parse
import asyncio
import aiohttp
from bs4 import BeautifulSoup

from models.schemas import RawStockData, MacroData

logger = logging.getLogger("DataCollector")

class DataCollectorAgent:
    def __init__(self):
        pass

    async def fetch_macro_indicators(self, session: aiohttp.ClientSession) -> MacroData:
        url = "https://www.tcmb.gov.tr/wps/wcm/connect/tr/tcmb+tr"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        policy_rate = 50.0  # Safe defaults
        inflation_rate = 69.8 # Safe defaults
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    text = await response.text()
                    soup = BeautifulSoup(text, 'html.parser')
                    
                    text_content = soup.get_text(separator=' ', strip=True).lower()
                    match_faiz = re.search(r'politika faizi.*?%?\s*(\d+[,.]\d+)', text_content)
                    if match_faiz:
                        val = match_faiz.group(1).replace(',', '.')
                        policy_rate = float(val)
                        
                    match_enflasyon = re.search(r'enflasyon.*?%?\s*(\d+[,.]\d+)', text_content)
                    if match_enflasyon:
                        val = match_enflasyon.group(1).replace(',', '.')
                        inflation_rate = float(val)
        except Exception as e:
            logger.warning(f"Macro veri çekilirken hata: {e}")

        return MacroData(inflation_rate=inflation_rate, policy_rate=policy_rate)

    async def fetch_stock_data(self, session: aiohttp.ClientSession, ticker: str) -> RawStockData:
        ticker_upper = ticker.upper()
        
        task_bp = self._fetch_bigpara_metrics(session, ticker_upper)
        task_card = self._fetch_company_card_metrics(session, ticker_upper)
        task_news = self._fetch_recent_news(session, ticker_upper)
        
        bp_data, card_data, recent_news = await asyncio.gather(task_bp, task_card, task_news, return_exceptions=True)
        
        if isinstance(bp_data, Exception) or bp_data is None:
            raise ValueError(f"{ticker_upper}: Bigpara'dan veri çekilemedi. Hata: {bp_data}")
            
        if isinstance(card_data, Exception) or not card_data:
            card_data = None
            
        if isinstance(recent_news, Exception):
            recent_news = []

        total_assets = card_data["total_assets"] if (card_data and card_data["total_assets"] > 0) else bp_data["total_assets"]
        total_liabilities = card_data["total_liabilities"] if (card_data and card_data["total_liabilities"] > 0) else bp_data["total_liabilities"]
        current_assets = card_data["current_assets"] if card_data else 0.0
        short_term_liabilities = card_data["short_term_liabilities"] if card_data else 0.0
        equity = card_data["equity"] if (card_data and card_data["equity"] > 0) else (total_assets - total_liabilities)
        
        gross_profit = card_data["gross_profit"] if card_data else 0.0
        operating_profit = card_data["operating_profit"] if card_data else 0.0
        roe = card_data["roe"] if card_data else 0.0
        
        return RawStockData(
            ticker=ticker_upper,
            price=bp_data["price"],
            net_profit=bp_data["net_profit"],
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            current_assets=current_assets,
            short_term_liabilities=short_term_liabilities,
            equity=equity,
            ebitda=0.0,
            outstanding_shares=bp_data["outstanding_shares"],
            pe_ratio=bp_data["pe_ratio"],
            pb_ratio=bp_data["pb_ratio"],
            gross_profit=gross_profit,
            operating_profit=operating_profit,
            roe=roe,
            recent_news=recent_news
        )

    async def _fetch_bigpara_metrics(self, session: aiohttp.ClientSession, ticker: str) -> dict:
        url = f"https://bigpara.hurriyet.com.tr/borsa/hisse-fiyatlari/{ticker.lower()}-detay/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    text = await response.text()
                    soup = BeautifulSoup(text, 'html.parser')
                    metrics = {}
                    for row in soup.find_all('li'):
                        n = row.find('span', class_='name')
                        v = row.find('span', class_='value')
                        if n and v:
                            metrics[n.text.strip()] = v.text.strip()
                            
                    price = self._parse_turkish_float(metrics.get("Son \u0130\u015flem Fiyat\u0131"))
                    pe_ratio = self._parse_turkish_float(metrics.get("F/K"))
                    pb_ratio = self._parse_turkish_float(metrics.get("PD/DD"))
                    net_profit = self._parse_turkish_float(metrics.get("Net K\u00e2r (TL)"))
                    outstanding_shares = self._parse_turkish_float(metrics.get("Sermaye (TL)"))
                    market_cap = self._parse_turkish_float(metrics.get("Piyasa De\u011feri"))
                    
                    equity = market_cap / pb_ratio if pb_ratio > 0 else 0.0
                    total_assets = equity * 2.0
                    total_liabilities = equity
                    
                    if price > 0:
                        return {
                            "price": price,
                            "pe_ratio": pe_ratio,
                            "pb_ratio": pb_ratio,
                            "net_profit": net_profit if net_profit != 0.0 else (market_cap / pe_ratio if pe_ratio > 0 else 0.0),
                            "outstanding_shares": outstanding_shares if outstanding_shares > 0 else 100000000.0,
                            "total_assets": total_assets if total_assets > 0 else 100000000.0,
                            "total_liabilities": total_liabilities if total_liabilities > 0 else 50000000.0,
                        }
        except Exception as e:
            logger.error(f"{ticker}: Bigpara fetch failed: {e}")
        return None

    async def _fetch_company_card_metrics(self, session: aiohttp.ClientSession, ticker: str) -> dict:
        url = f"https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx?hisse={ticker.upper()}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        try:
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status != 200:
                    return None
                    
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                
                table = None
                for tbl in soup.find_all('table'):
                    tbl_text = tbl.text
                    if any(kw in tbl_text for kw in ["Dönen Varlıklar", "Bilanço", "AKTİF TOPLAMI", "NAKİT DEĞERLER VE MERKEZ BANKASI", "Cari Varlıklar Toplamı"]):
                        table = tbl
                        break
                        
                if not table:
                    return None
                    
                rows = table.find_all('tr')
                
                metrics = {
                    "current_assets": 0.0,
                    "short_term_liabilities": 0.0,
                    "long_term_liabilities": 0.0,
                    "total_assets": 0.0,
                    "total_sources": 0.0,
                    "equity": 0.0,
                    "net_profit": 0.0,
                    "gross_profit": 0.0,
                    "operating_profit": 0.0
                }
                
                def clean_label(l):
                    l = l.strip().lower()
                    l = unicodedata.normalize('NFKD', l)
                    l = "".join([c for c in l if not unicodedata.combining(c)])
                    l = l.replace("ı", "i").replace("ş", "s").replace("ç", "c").replace("ğ", "g")
                    
                    l = l.replace("dnen varlklar", "donen varliklar")
                    l = l.replace("ozkaynaklar", "ozkaynaklar")
                    l = l.replace("denmis sermaye", "odenmis sermaye")
                    l = l.replace("net kar", "net kar")
                    return re.sub(r'\s+', ' ', l)
                    
                for r in rows:
                    cells = r.find_all(['td', 'th'])
                    if not cells:
                        continue
                    label = clean_label(cells[0].text)
                    
                    val = 0.0
                    if len(cells) > 1:
                        val = self._parse_turkish_float(cells[1].text)
                        
                    if label in ["donen varliklar", "cari varliklar toplami", "donen varliklar toplami"]:
                        metrics["current_assets"] = val
                    elif label in ["kisa vadeli yukumlulukler", "kisa vadeli yukumlulukler toplami"]:
                        metrics["short_term_liabilities"] = val
                    elif label in ["uzun vadeli yukumlulukler", "uzun vadeli yukumlulukler toplami"]:
                        metrics["long_term_liabilities"] = val
                    elif label in ["toplam varliklar", "aktif toplami", "toplam aktifler", "toplam aktif"]:
                        metrics["total_assets"] = val
                    elif label in ["toplam kaynaklar", "pasif toplami", "toplam pasifler", "toplam pasif"]:
                        metrics["total_sources"] = val
                    elif label in ["ozkaynaklar", "ozsermaye toplami", "xvi. ozkaynaklar", "ana ortakliga ait ozkaynaklar", "ozkaynaklar toplami"]:
                        if metrics["equity"] == 0.0 or label in ["ana ortakliga ait ozkaynaklar", "ozkaynaklar", "ozsermaye toplami", "xvi. ozkaynaklar"]:
                            metrics["equity"] = val
                    elif label in ["donem net kar/zarari", "donem net kar/zarar", "donem net kar", "ana ortaklik paylari", "donem net kari/zarari", "donem net kari veya zarari", "donem net kari (zarari)", "donem net kar veya zarari"]:
                        if metrics["net_profit"] == 0.0 or label == "ana ortaklik paylari":
                            metrics["net_profit"] = val
                    elif label in ["brut kar (zarar)", "brut kar/zarar", "brut kar"]:
                        metrics["gross_profit"] = val
                    elif label in ["esas faaliyet kari (zarari)", "esas faaliyet kar/zarar", "faaliyet kari"]:
                        metrics["operating_profit"] = val

                summary_tbody = soup.find('tbody', id='malitabloShortTbody')
                if summary_tbody:
                    s_rows = summary_tbody.find_all('tr')
                    for sr in s_rows:
                        s_cells = sr.find_all(['td', 'th'])
                        if len(s_cells) >= 2:
                            s_label = clean_label(s_cells[0].text)
                            s_val = self._parse_turkish_float(s_cells[1].text) * 1000000.0
                            if "ozkaynaklar" in s_label:
                                if metrics["equity"] == 0.0:
                                    metrics["equity"] = s_val
                            elif "net kar" in s_label:
                                if metrics["net_profit"] == 0.0:
                                    metrics["net_profit"] = s_val

                roe_val = 0.0
                if metrics["equity"] > 0 and metrics["net_profit"] != 0:
                    roe_val = metrics["net_profit"] / metrics["equity"]
                    
                if metrics["total_assets"] == 0.0 and metrics["total_sources"] > 0.0:
                    metrics["total_assets"] = metrics["total_sources"]
                elif metrics["total_sources"] == 0.0 and metrics["total_assets"] > 0.0:
                    metrics["total_sources"] = metrics["total_assets"]
                    
                total_liab = 0.0
                if metrics["total_sources"] > 0.0 and metrics["equity"] > 0.0:
                    total_liab = metrics["total_sources"] - metrics["equity"]
                else:
                    total_liab = metrics["short_term_liabilities"] + metrics["long_term_liabilities"]
                    
                return {
                    "current_assets": metrics["current_assets"],
                    "short_term_liabilities": metrics["short_term_liabilities"],
                    "long_term_liabilities": metrics["long_term_liabilities"],
                    "total_assets": metrics["total_assets"],
                    "total_liabilities": total_liab,
                    "equity": metrics["equity"],
                    "net_profit": metrics["net_profit"],
                    "gross_profit": metrics["gross_profit"],
                    "operating_profit": metrics["operating_profit"],
                    "roe": roe_val
                }
        except Exception as e:
            logger.error(f"{ticker}: Company card fetch failed: {e}")
        return None

    def _parse_turkish_float(self, val_str) -> float:
        if not val_str or val_str.strip() in ["-", "0", ""]:
            return 0.0
        val_str = val_str.strip()
        is_negative = False
        if val_str.startswith("(") and val_str.endswith(")"):
            is_negative = True
            val_str = val_str[1:-1]
        clean = val_str.replace(".", "").replace(",", ".")
        try:
            clean = re.sub(r'[^\d\.\-]', '', clean)
            val = float(clean)
            return -val if is_negative else val
        except ValueError:
            return 0.0

    async def _fetch_recent_news(self, session: aiohttp.ClientSession, ticker: str) -> list:
        query = f"KAP {ticker}"
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=tr&gl=TR&ceid=TR:tr"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    text = await response.text()
                    root = ET.fromstring(text)
                    items = root.findall(".//item")
                    headlines = []
                    for item in items[:5]:
                        title = item.find("title").text
                        headlines.append(title)
                    return headlines
        except Exception as e:
            logger.error(f"{ticker}: News fetch failed: {e}")
        return []
