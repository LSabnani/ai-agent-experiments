import yfinance as yf
import pandas as pd
import numpy as np

def fetch_stock_data(ticker_symbol: str, period: str = "1y", interval: str = "1d"):
    """
    Fetches historical price data, ticker metadata, and financial statements.
    """
    ticker = yf.Ticker(ticker_symbol)
    
    # Fetch historical prices
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        raise ValueError(f"No price data found for ticker '{ticker_symbol}'. Please verify the symbol.")
        
    # Clean index and column names
    df = df.reset_index()
    df.columns = [col.lower().replace(" ", "_") for col in df.columns]
    
    # Fetch info dictionary safely
    try:
        info = ticker.info
    except Exception:
        info = {}
        
    # Fetch financials safely
    try:
        financials = ticker.financials
    except Exception:
        financials = pd.DataFrame()
        
    try:
        quarterly_financials = ticker.quarterly_financials
    except Exception:
        quarterly_financials = pd.DataFrame()

    try:
        news = ticker.news
    except Exception:
        news = []
        
    return {
        "ticker_symbol": ticker_symbol.upper(),
        "df": df,
        "info": info,
        "financials": financials,
        "quarterly_financials": quarterly_financials,
        "news": news
    }
