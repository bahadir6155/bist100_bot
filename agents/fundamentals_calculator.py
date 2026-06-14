from models.schemas import RawStockData, CalculatedMetrics

class FundamentalsCalculatorAgent:
    def calculate_metrics(self, raw_data: RawStockData) -> CalculatedMetrics:
        # Prioritize exact equity from scraping; fallback to assets - liabilities
        equity = raw_data.equity if raw_data.equity > 0 else (raw_data.total_assets - raw_data.total_liabilities)
        shares = raw_data.outstanding_shares if raw_data.outstanding_shares > 0 else 1.0
        
        # Prioritize pre-calculated values from scraping
        pe_ratio = raw_data.pe_ratio
        pb_ratio = raw_data.pb_ratio
        
        # Fallback to manual calculations if not pre-fetched (or if pe_ratio is 0 because of negative net profit/loss)
        if pe_ratio == 0.0 or pe_ratio == float('inf'):
            eps = raw_data.net_profit / shares
            pe_ratio = raw_data.price / eps if eps != 0 else float('inf')
            
        if pb_ratio == 0.0 or pb_ratio == float('inf'):
            bvps = equity / shares
            pb_ratio = raw_data.price / bvps if bvps != 0 else float('inf')
            
        debt_to_equity = raw_data.total_liabilities / equity if equity > 0 else float('inf')
        
        if raw_data.short_term_liabilities > 0:
            current_ratio = raw_data.current_assets / raw_data.short_term_liabilities
        else:
            current_ratio = 0.0
            
        return CalculatedMetrics(
            ticker=raw_data.ticker,
            pe_ratio=round(pe_ratio, 2) if pe_ratio != float('inf') else 999.9,
            pb_ratio=round(pb_ratio, 2) if pb_ratio != float('inf') else 999.9,
            debt_to_equity=round(debt_to_equity, 2) if debt_to_equity != float('inf') else 999.9,
            current_ratio=round(current_ratio, 2) if current_ratio != float('inf') else 0.0
        )
