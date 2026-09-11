import re
import numpy as np

BULLISH_KEYWORDS = [
    "growth", "surge", "record", "beat", "profit", "bullish", "upgrade", "outperform",
    "rally", "expansion", "dividend", "revenue up", "gain", "breakthrough", "acquisition",
    "all-time high", "momentum", "strong", "lead", "soar", "innovation"
]

BEARISH_KEYWORDS = [
    "drop", "fall", "decline", "miss", "loss", "bearish", "downgrade", "underperform",
    "slump", "investigation", "lawsuit", "penalty", "cut", "recession", "debt", "risk",
    "layoffs", "plunge", "weak", "warning", "deficit", "inflation", "headwinds"
]

def analyze_news_sentiment(news_list: list) -> dict:
    """
    Analyzes list of news items returned by yfinance to compute overall sentiment score & top insights.
    """
    if not news_list:
        return {
            "score": 50,
            "label": "Neutral / No News",
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "processed_news": []
        }

    processed = []
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0

    for item in news_list[:15]:
        title = ""
        link = "#"
        publisher = "Unknown"
        
        # Handle dict formats from yfinance
        if isinstance(item, dict):
            title = item.get("title", "")
            publisher = item.get("publisher", item.get("providerPublishTime", "Unknown"))
            link = item.get("link", item.get("url", "#"))
        elif hasattr(item, "title"):
            title = getattr(item, "title", "")
            publisher = getattr(item, "publisher", "Unknown")
            link = getattr(item, "link", "#")

        title_lower = title.lower()
        
        bull_score = sum(1 for kw in BULLISH_KEYWORDS if kw in title_lower)
        bear_score = sum(1 for kw in BEARISH_KEYWORDS if kw in title_lower)

        if bull_score > bear_score:
            sentiment = "Bullish"
            bullish_count += 1
        elif bear_score > bull_score:
            sentiment = "Bearish"
            bearish_count += 1
        else:
            sentiment = "Neutral"
            neutral_count += 1

        processed.append({
            "title": title,
            "publisher": publisher,
            "link": link,
            "sentiment": sentiment
        })

    total = max(bullish_count + bearish_count + neutral_count, 1)
    # Score calculation: base 50, modified by ratio of bullish vs bearish
    sentiment_ratio = (bullish_count - bearish_count) / total
    score = int(np.clip(50 + (sentiment_ratio * 40), 0, 100))

    if score >= 65:
        label = "Bullish News Sentiment"
    elif score >= 55:
        label = "Slightly Bullish"
    elif score >= 45:
        label = "Neutral News Sentiment"
    elif score >= 35:
        label = "Slightly Bearish"
    else:
        label = "Bearish News Sentiment"

    return {
        "score": score,
        "label": label,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "neutral_count": neutral_count,
        "processed_news": processed
    }
