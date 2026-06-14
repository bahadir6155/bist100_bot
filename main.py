import asyncio
import argparse
import random
import sys

# Windows'ta aiohttp EventLoopPolicy hatasını önlemek ve Türkçe karakter sorununu çözmek için
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from agents.orchestrator import OrchestratorAgent

def main():
    parser = argparse.ArgumentParser(description="BIST100 Otonom Temel Analiz Botu")
    parser.add_argument(
        '--mode', 
        choices=['test', 'live'], 
        default='test', 
        help="Çalışma modu. 'test' rastgele 5 hisse seçer, 'live' tüm BIST100 hisselerini analiz eder."
    )
    args = parser.parse_args()

    # List of BIST100 tickers to analyze
    all_tickers = [
        "AGHOL", "AGROT", "AKBNK", "AKFGY", "AKFYE", "AKSA", "AKSEN", "ALARK", "ALFAS", "AEFES", 
        "ARCLK", "ARDYZ", "ASELS", "ASTOR", "BTCIM", "BERA", "BIMAS", "BRSAN", "BRYAT", "BFREN", 
        "CCOLA", "CWENE", "CANTE", "CIMSA", "DOHOL", "DOAS", "ECZYT", "EGEEN", "ECILC", "EKGYO", 
        "ENJSA", "ENERY", "ENKAI", "EREGL", "EUREN", "EUPWR", "FROTO", "GESAN", "GOLTS", "GUBRF", 
        "SAHOL", "HEKTS", "ISGYO", "ISMEN", "IZENR", "KLSER", "KRDMD", "KTLEV", "KAYSE", "KCAER", 
        "KCHOL", "KONTR", "KONYA", "KOZAL", "KOZAA", "LMKDC", "MAVI", "MIATK", "MGROS", "OBAMS", 
        "ODAS", "OTKAR", "OYAKC", "PGSUS", "PEKGY", "PETKM", "QUAGR", "REEDR", "SASA", "SDTTR", 
        "SMRTG", "SKBNK", "SOKM", "TABGD", "TAVHL", "TKFEN", "TKNSA", "TOASO", "TUKAS", "TCELL", 
        "TMSN", "TUPRS", "THYAO", "TTKOM", "TTRAK", "GARAN", "HALKB", "ISCTR", "TSKB", "TURSG", 
        "SISE", "VAKBN", "ULKER", "VESBE", "VESTL", "YKBNK", "YYLGD", "YEOTK", "ZOREN", "BINHO"
    ]
    
    if args.mode == 'test':
        tickers = random.sample(all_tickers, 5)
        print(f"Mod: TEST. Sadece rastgele seçilen {len(tickers)} hisse analiz edilecek.")
    else:
        tickers = all_tickers
        print(f"Mod: LIVE. Tüm {len(tickers)} hisse analiz edilecek.")
        
    orchestrator = OrchestratorAgent()
    
    print("=" * 60)
    print("      BIST100 OTONOM TEMEL ANALİZ VE RAPORLAMA SİSTEMİ")
    print("=" * 60)
    
    results = asyncio.run(orchestrator.run_all(tickers))
    
    print("\n" + "=" * 60)
    print("                      GÜNLÜK BÜLTEN")
    print("=" * 60)
    
    for res in results:
        print(f"\n[Hisse]: {res.ticker}")
        if not res.is_successful:
            print(f"  [DURUM]: HATA - {res.error_message}")
        else:
            print(f"  [Sinyal]: {res.signal}")
            print(f"  [Risk Skoru]: {res.risk_score} / 100")
            print(f"  [Yorum]: {res.commentary}")
        print("-" * 60)
        
    print("\n[Yasal Uyarı] Burada yer alan yatırım bilgi, yorum ve tavsiyeleri yatırım danışmanlığı kapsamında değildir.")
    print("=" * 60)

if __name__ == "__main__":
    main()
