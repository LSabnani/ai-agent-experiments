from data_fetcher import fetch_stock_data
from technical_analysis import compute_technical_indicators, analyze_technical_signals
from fundamental_analysis import extract_fundamental_metrics, analyze_fundamental_health
from sentiment_analysis import analyze_news_sentiment
from eetimes_validation import fetch_eetimes_validation

class MarketAnalyzerAgent:
    """
    Core AI Agent that orchestrates data fetchers, indicator engines, 
    and synthesizes multi-factor market analysis.
    """
    def __init__(self, ticker_symbol: str, period: str = "1y"):
        self.ticker_symbol = ticker_symbol.upper()
        self.period = period

    def run_full_analysis(self) -> dict:
        # 1. Fetch raw data
        raw_data = fetch_stock_data(self.ticker_symbol, period=self.period)
        
        # 2. Compute Technical Analysis
        df_tech = compute_technical_indicators(raw_data['df'])
        tech_summary = analyze_technical_signals(df_tech)
        
        # 3. Compute Fundamental Analysis
        fund_metrics = extract_fundamental_metrics(raw_data['info'])
        fund_summary = analyze_fundamental_health(raw_data['info'])
        
        # 4. Compute News Sentiment Analysis
        sentiment_summary = analyze_news_sentiment(raw_data['news'])
        
        # 5. EE Times Cross Validation
        eetimes_data = fetch_eetimes_validation(self.ticker_symbol)
        
        # 5. Composite Agent Score Calculation
        # Weights: Technical 40%, Fundamental 40%, Sentiment 20%
        tech_weight = 0.40
        fund_weight = 0.40
        sent_weight = 0.20
        
        composite_score = int(
            (tech_summary['score'] * tech_weight) +
            (fund_summary['score'] * fund_weight) +
            (sentiment_summary['score'] * sent_weight)
        )
        
        if composite_score >= 75:
            overall_signal = "Strong Bullish"
            signal_color = "#10B981" # Emerald Green
        elif composite_score >= 60:
            overall_signal = "Bullish"
            signal_color = "#34D399" # Light Green
        elif composite_score >= 45:
            overall_signal = "Neutral"
            signal_color = "#FBBF24" # Amber / Yellow
        elif composite_score >= 30:
            overall_signal = "Bearish"
            signal_color = "#F87171" # Coral Red
        else:
            overall_signal = "Strong Bearish"
            signal_color = "#EF4444" # Deep Red

        # 6. Generate Agent Synthesis Thesis
        thesis = self._generate_synthesis_thesis(
            raw_data['info'], tech_summary, fund_summary, sentiment_summary, composite_score, overall_signal
        )

        return {
            "ticker_symbol": self.ticker_symbol,
            "company_name": fund_metrics.get("Company Name", self.ticker_symbol),
            "raw_df": df_tech,
            "info": raw_data['info'],
            "financials": raw_data['financials'],
            "quarterly_financials": raw_data['quarterly_financials'],
            "technical": tech_summary,
            "fundamental_metrics": fund_metrics,
            "fundamental_summary": fund_summary,
            "sentiment": sentiment_summary,
            "eetimes": eetimes_data,
            "composite_score": composite_score,
            "overall_signal": overall_signal,
            "signal_color": signal_color,
            "agent_thesis": thesis
        }

    def _generate_synthesis_thesis(self, info, tech, fund, sent, score, signal) -> dict:
        name = info.get("longName", self.ticker_symbol)
        
        bull_drivers = []
        bear_risks = []

        # Gather Bull Drivers
        if tech['score'] >= 55:
            bull_drivers.append(f"Positive momentum with technical score of {tech['score']}/100 ({tech['recommendation']}).")
        if fund['score'] >= 55:
            bull_drivers.append(f"Healthy financial balance sheet and valuation profile (Score: {fund['score']}/100).")
        if sent['score'] >= 55:
            bull_drivers.append(f"Favorable news sentiment flow with high bullish headline ratio.")

        # Add specific insights
        for sig in tech['signals']:
            if "Bullish" in sig or "Golden Cross" in sig or "Oversold" in sig or "above" in sig:
                bull_drivers.append(sig)

        for ins in fund['insights']:
            if "Outstanding" in ins or "Solid" in ins or "Attractive" in ins or "Strong" in ins or "Growth" in ins:
                bull_drivers.append(ins)

        # Gather Bear Risks
        if tech['score'] < 45:
            bear_risks.append(f"Weak technical trend structure (Score: {tech['score']}/100).")
        if fund['score'] < 45:
            bear_risks.append(f"Fundamental headwinds or valuation stretch (Score: {fund['score']}/100).")
        if sent['score'] < 45:
            bear_risks.append(f"Negative news sentiment pressure.")

        for sig in tech['signals']:
            if "Bearish" in sig or "Death Cross" in sig or "Overbought" in sig or "below" in sig:
                bear_risks.append(sig)

        for ins in fund['insights']:
            if "Unprofitable" in ins or "High Valuation" in ins or "Risk" in ins or "Elevated" in ins or "Contracting" in ins:
                bear_risks.append(ins)

        # Executive Summary
        summary = (
            f"The Market Analyzer Agent assigns **{name} ({self.ticker_symbol})** an overall rating of **{signal}** "
            f"with a composite score of **{score}/100**.\n\n"
            f"This composite evaluation weights Technical Indicators ({tech['score']}/100), Fundamental Health ({fund['score']}/100), "
            f"and News Sentiment ({sent['score']}/100)."
        )

        return {
            "summary": summary,
            "bull_drivers": bull_drivers[:5] if bull_drivers else ["No major bullish drivers identified."],
            "bear_risks": bear_risks[:5] if bear_risks else ["No immediate critical risks flagged by technical/fundamental rules."]
        }
