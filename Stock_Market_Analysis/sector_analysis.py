import yfinance as yf
import pandas as pd

# Standard US Sector ETF Mapping
SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Cyclical": "XLY",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB"
}

# Top 3 Mega-Cap Market Leaders per Sector
TOP_STOCKS_BY_SECTOR = {
    "Technology": ["AAPL", "NVDA", "MSFT"],
    "Healthcare": ["LLY", "UNH", "JNJ"],
    "Financials": ["JPM", "BAC", "V"],
    "Consumer Cyclical": ["AMZN", "TSLA", "HD"],
    "Communication Services": ["GOOGL", "META", "NFLX"],
    "Industrials": ["CAT", "GE", "HON"],
    "Consumer Staples": ["PG", "KO", "PEP"],
    "Energy": ["XOM", "CVX", "COP"],
    "Utilities": ["NEE", "SO", "DUK"],
    "Real Estate": ["PLD", "AMT", "EQIX"],
    "Basic Materials": ["LIN", "APD", "SHW"]
}

def fetch_sector_performance() -> pd.DataFrame:
    """
    Fetches daily performance (% change) across major sector ETFs to identify sector winners and losers.
    """
    tickers = list(SECTOR_ETFS.values())
    try:
        data = yf.download(tickers, period="5d", interval="1d", progress=False)['Close']
        if data.empty or len(data) < 2:
            return pd.DataFrame()
        
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        pct_change = ((latest - prev) / prev) * 100
        
        records = []
        for sector, symbol in SECTOR_ETFS.items():
            if symbol in pct_change:
                chg = pct_change[symbol]
                price = latest[symbol]
                top_3 = ", ".join(TOP_STOCKS_BY_SECTOR.get(sector, []))
                records.append({
                    "Sector": sector,
                    "ETF": symbol,
                    "Price": float(price),
                    "Change %": float(chg),
                    "Top 3 Market Leaders": top_3
                })
        
        df_sectors = pd.DataFrame(records)
        df_sectors = df_sectors.sort_values(by="Change %", ascending=False).reset_index(drop=True)
        return df_sectors
    except Exception as e:
        return pd.DataFrame()

def fetch_top_stocks_performance() -> dict:
    """
    Fetches daily performance for top 3 stocks per sector.
    """
    all_symbols = [symbol for stocks in TOP_STOCKS_BY_SECTOR.values() for symbol in stocks]
    try:
        data = yf.download(all_symbols, period="5d", interval="1d", progress=False)['Close']
        if data.empty or len(data) < 2:
            return {}
            
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        pct_change = ((latest - prev) / prev) * 100
        
        result = {}
        for sector, stocks in TOP_STOCKS_BY_SECTOR.items():
            sector_list = []
            for s in stocks:
                if s in pct_change:
                    sector_list.append({
                        "Symbol": s,
                        "Price": float(latest[s]),
                        "Change %": float(pct_change[s])
                    })
            result[sector] = sector_list
        return result
    except Exception:
        return {}
