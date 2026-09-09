import pandas as pd
import numpy as np

def compute_pivot_points(high: float, low: float, close: float) -> dict:
    """
    Computes Standard Pivot Point and Support (S1, S2, S3) / Resistance (R1, R2, R3) levels.
    Formula:
      Pivot (P) = (High + Low + Close) / 3
      Resistance 1 (R1) = (2 * P) - Low
      Support 1 (S1)    = (2 * P) - High
      Resistance 2 (R2) = P + (High - Low)
      Support 2 (S2)    = P - (High - Low)
      Resistance 3 (R3) = High + 2 * (P - Low)
      Support 3 (S3)    = Low - 2 * (High - P)
    """
    p = (high + low + close) / 3.0
    r1 = (2.0 * p) - low
    s1 = (2.0 * p) - high
    r2 = p + (high - low)
    s2 = p - (high - low)
    r3 = high + (2.0 * (p - low))
    s3 = low - (2.0 * (high - p))
    
    return {
        "pivot": p,
        "r1": r1, "r2": r2, "r3": r3,
        "s1": s1, "s2": s2, "s3": s3
    }

def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes technical indicators: SMA (20, 50, 200), EMA (12, 26), RSI, MACD, Bollinger Bands, Volume SMA.
    """
    data = df.copy()
    
    # Ensure correct sorting by date
    if 'date' in data.columns:
        data['date'] = pd.to_datetime(data['date'])
        data = data.sort_values('date').reset_index(drop=True)
        
    close = data['close']
    
    # Simple Moving Averages
    data['sma_20'] = close.rolling(window=20).mean()
    data['sma_50'] = close.rolling(window=50).mean()
    data['sma_200'] = close.rolling(window=200).mean()
    
    # Exponential Moving Averages
    data['ema_12'] = close.ewm(span=12, adjust=False).mean()
    data['ema_26'] = close.ewm(span=26, adjust=False).mean()
    
    # MACD & Signal Line
    data['macd'] = data['ema_12'] - data['ema_26']
    data['macd_signal'] = data['macd'].ewm(span=9, adjust=False).mean()
    data['macd_hist'] = data['macd'] - data['macd_signal']
    
    # Relative Strength Index (RSI - 14)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss.replace(0, np.nan))
    data['rsi'] = 100 - (100 / (1 + rs))
    data['rsi'] = data['rsi'].fillna(50)
    
    # Bollinger Bands (20-day SMA, 2 std dev)
    data['bb_middle'] = data['sma_20']
    std_20 = close.rolling(window=20).std()
    data['bb_upper'] = data['bb_middle'] + (std_20 * 2)
    data['bb_lower'] = data['bb_middle'] - (std_20 * 2)
    
    # Volume Indicators
    if 'volume' in data.columns:
        data['vol_sma_20'] = data['volume'].rolling(window=20).mean()
        
    return data

def analyze_technical_signals(df: pd.DataFrame) -> dict:
    """
    Evaluates latest indicators to generate technical signal score, pivot points, and commentary.
    """
    if df.empty or len(df) < 20:
        return {"score": 50, "signals": ["Insufficient data for full technical analysis"], "recommendation": "Neutral"}
        
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Calculate Pivot Points from previous bar / session
    pivots = compute_pivot_points(high=prev['high'], low=prev['low'], close=prev['close'])
    
    signals = []
    bullish_points = 0
    total_points = 0
    
    # Price vs Moving Averages
    total_points += 3
    if latest['close'] > latest['sma_20']:
        bullish_points += 1
        signals.append("Price is above 20-day SMA (Short-term Bullish)")
    else:
        signals.append("Price is below 20-day SMA (Short-term Bearish)")
        
    if not np.isnan(latest['sma_50']):
        if latest['close'] > latest['sma_50']:
            bullish_points += 1
            signals.append("Price is above 50-day SMA (Medium-term Bullish)")
        else:
            signals.append("Price is below 50-day SMA (Medium-term Bearish)")
            
    if not np.isnan(latest['sma_200']):
        if latest['close'] > latest['sma_200']:
            bullish_points += 1
            signals.append("Price is above 200-day SMA (Long-term Bullish)")
        else:
            signals.append("Price is below 200-day SMA (Long-term Bearish)")

    # Golden / Death Cross
    if not np.isnan(latest['sma_50']) and not np.isnan(latest['sma_200']):
        total_points += 2
        if latest['sma_50'] > latest['sma_200']:
            bullish_points += 2
            signals.append("Golden Cross active (50 SMA > 200 SMA)")
        else:
            signals.append("Death Cross active (50 SMA < 200 SMA)")

    # RSI Analysis
    total_points += 2
    rsi_val = latest['rsi']
    if rsi_val > 70:
        signals.append(f"RSI is Overbought ({rsi_val:.1f}) - Potential pull-back risk")
    elif rsi_val < 30:
        bullish_points += 2
        signals.append(f"RSI is Oversold ({rsi_val:.1f}) - Potential bounce opportunity")
    elif 45 <= rsi_val <= 65:
        bullish_points += 1
        signals.append(f"RSI is neutral to constructive ({rsi_val:.1f})")
    else:
        signals.append(f"RSI is neutral ({rsi_val:.1f})")

    # MACD Crossover
    total_points += 2
    if latest['macd'] > latest['macd_signal']:
        bullish_points += 2
        if prev['macd'] <= prev['macd_signal']:
            signals.append("Fresh Bullish MACD Crossover")
        else:
            signals.append("MACD is above Signal Line (Positive Momentum)")
    else:
        if prev['macd'] >= prev['macd_signal']:
            signals.append("Fresh Bearish MACD Crossover")
        else:
            signals.append("MACD is below Signal Line (Negative Momentum)")

    # Bollinger Bands Position
    if not np.isnan(latest['bb_upper']):
        total_points += 1
        if latest['close'] >= latest['bb_upper']:
            signals.append("Price testing Upper Bollinger Band (High Volatility / Overbought)")
        elif latest['close'] <= latest['bb_lower']:
            bullish_points += 1
            signals.append("Price testing Lower Bollinger Band (Potential Support)")

    score = int((bullish_points / max(total_points, 1)) * 100)
    
    if score >= 70:
        recommendation = "Strong Bullish"
    elif score >= 55:
        recommendation = "Moderately Bullish"
    elif score >= 45:
        recommendation = "Neutral"
    elif score >= 30:
        recommendation = "Moderately Bearish"
    else:
        recommendation = "Strong Bearish"
        
    return {
        "score": score,
        "signals": signals,
        "recommendation": recommendation,
        "pivots": pivots,
        "latest_metrics": {
            "close": latest['close'],
            "high": latest['high'],
            "low": latest['low'],
            "rsi": latest['rsi'],
            "macd": latest['macd'],
            "macd_signal": latest['macd_signal'],
            "sma_20": latest['sma_20'],
            "sma_50": latest['sma_50'],
            "sma_200": latest['sma_200']
        }
    }
