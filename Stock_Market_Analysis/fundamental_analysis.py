import numpy as np

def extract_fundamental_metrics(info: dict) -> dict:
    """
    Extracts key valuation, profitability, balance sheet, and growth metrics from ticker info.
    """
    def fmt_num(val, prefix="", suffix="", is_pct=False, multiplier=1):
        if val is None or val == 'N/A' or (isinstance(val, float) and np.isnan(val)):
            return "N/A"
        try:
            v = float(val) * multiplier
            if is_pct:
                return f"{v * 100:.2f}%"
            if abs(v) >= 1e12:
                return f"{prefix}{v / 1e12:.2f}T{suffix}"
            if abs(v) >= 1e9:
                return f"{prefix}{v / 1e9:.2f}B{suffix}"
            if abs(v) >= 1e6:
                return f"{prefix}{v / 1e6:.2f}M{suffix}"
            return f"{prefix}{v:.2f}{suffix}"
        except Exception:
            return "N/A"

    metrics = {
        "Company Name": info.get("longName", info.get("shortName", "N/A")),
        "Sector": info.get("sector", "N/A"),
        "Industry": info.get("industry", "N/A"),
        "Market Cap": fmt_num(info.get("marketCap"), prefix="$"),
        "Enterprise Value": fmt_num(info.get("enterpriseValue"), prefix="$"),
        "Trailing P/E": fmt_num(info.get("trailingPE")),
        "Forward P/E": fmt_num(info.get("forwardPE")),
        "PEG Ratio": fmt_num(info.get("pegRatio")),
        "Price to Sales (P/S)": fmt_num(info.get("priceToSalesTrailing12Months")),
        "Price to Book (P/B)": fmt_num(info.get("priceToBook")),
        "EV/EBITDA": fmt_num(info.get("enterpriseToEbitda")),
        "Profit Margin": fmt_num(info.get("profitMargins"), is_pct=True),
        "Operating Margin": fmt_num(info.get("operatingMargins"), is_pct=True),
        "Return on Equity (ROE)": fmt_num(info.get("returnOnEquity"), is_pct=True),
        "Return on Assets (ROA)": fmt_num(info.get("returnOnAssets"), is_pct=True),
        "Revenue Growth (YoY)": fmt_num(info.get("revenueGrowth"), is_pct=True),
        "Earnings Growth (YoY)": fmt_num(info.get("earningsGrowth"), is_pct=True),
        "Total Cash": fmt_num(info.get("totalCash"), prefix="$"),
        "Total Debt": fmt_num(info.get("totalDebt"), prefix="$"),
        "Current Ratio": fmt_num(info.get("currentRatio")),
        "Quick Ratio": fmt_num(info.get("quickRatio")),
        "Debt to Equity": fmt_num(info.get("debtToEquity")),
        "Free Cash Flow": fmt_num(info.get("freeCashflow"), prefix="$"),
        "52 Week High": fmt_num(info.get("fiftyTwoWeekHigh"), prefix="$"),
        "52 Week Low": fmt_num(info.get("fiftyTwoWeekLow"), prefix="$"),
        "Beta": fmt_num(info.get("beta")),
        "Dividend Yield": fmt_num(info.get("dividendYield"), is_pct=True)
    }
    return metrics

def analyze_fundamental_health(info: dict) -> dict:
    """
    Evaluates key ratios to score financial health (0-100) and generate key insights.
    """
    insights = []
    score_points = 0
    max_points = 0

    # 1. Profitability (Profit Margin > 10% is good, > 20% is excellent)
    profit_margin = info.get("profitMargins")
    max_points += 25
    if profit_margin is not None and isinstance(profit_margin, (int, float)):
        if profit_margin > 0.20:
            score_points += 25
            insights.append(f"Outstanding Profit Margin ({profit_margin*100:.1f}%)")
        elif profit_margin > 0.10:
            score_points += 18
            insights.append(f"Solid Profit Margin ({profit_margin*100:.1f}%)")
        elif profit_margin > 0:
            score_points += 10
            insights.append(f"Modest Profit Margin ({profit_margin*100:.1f}%)")
        else:
            insights.append(f"Negative Profit Margin ({profit_margin*100:.1f}%) - Unprofitable")

    # 2. Valuation (Forward P/E & PEG)
    fwd_pe = info.get("forwardPE")
    peg = info.get("pegRatio")
    max_points += 25
    if fwd_pe is not None and isinstance(fwd_pe, (int, float)) and fwd_pe > 0:
        if fwd_pe < 15:
            score_points += 15
            insights.append(f"Attractive Valuation: Low Forward P/E ({fwd_pe:.1f}x)")
        elif fwd_pe < 30:
            score_points += 10
            insights.append(f"Fair Valuation: Moderate Forward P/E ({fwd_pe:.1f}x)")
        else:
            score_points += 5
            insights.append(f"High Growth/Premium Valuation: Forward P/E ({fwd_pe:.1f}x)")
            
    if peg is not None and isinstance(peg, (int, float)) and peg > 0:
        if peg < 1.0:
            score_points += 10
            insights.append(f"PEG Ratio < 1.0 ({peg:.2f}) indicates potentially undervalued growth")
        elif peg <= 2.0:
            score_points += 5
            insights.append(f"Reasonable PEG Ratio ({peg:.2f})")

    # 3. Financial Health (Current Ratio & Debt to Equity)
    curr_ratio = info.get("currentRatio")
    d_e = info.get("debtToEquity")
    max_points += 25
    if curr_ratio is not None and isinstance(curr_ratio, (int, float)):
        if curr_ratio > 1.5:
            score_points += 12
            insights.append(f"Strong Liquidity: Current Ratio is {curr_ratio:.2f}")
        elif curr_ratio >= 1.0:
            score_points += 8
            insights.append(f"Adequate Liquidity: Current Ratio is {curr_ratio:.2f}")
        else:
            insights.append(f"Liquidity Risk: Current Ratio is below 1.0 ({curr_ratio:.2f})")

    if d_e is not None and isinstance(d_e, (int, float)):
        if d_e < 50:
            score_points += 13
            insights.append(f"Conservative Leverage: Low Debt/Equity ({d_e:.1f}%)")
        elif d_e < 150:
            score_points += 8
            insights.append(f"Moderate Debt/Equity ratio ({d_e:.1f}%)")
        else:
            insights.append(f"High Leverage: Debt/Equity ratio is elevated ({d_e:.1f}%)")

    # 4. Growth Trends (Revenue Growth)
    rev_growth = info.get("revenueGrowth")
    max_points += 25
    if rev_growth is not None and isinstance(rev_growth, (int, float)):
        if rev_growth > 0.15:
            score_points += 25
            insights.append(f"High YoY Revenue Growth ({rev_growth*100:.1f}%)")
        elif rev_growth > 0.05:
            score_points += 15
            insights.append(f"Moderate YoY Revenue Growth ({rev_growth*100:.1f}%)")
        elif rev_growth >= 0:
            score_points += 8
            insights.append(f"Flat YoY Revenue Growth ({rev_growth*100:.1f}%)")
        else:
            insights.append(f"Contracting YoY Revenue ({rev_growth*100:.1f}%)")

    score = int((score_points / max(max_points, 1)) * 100) if max_points > 0 else 50

    return {
        "score": score,
        "insights": insights,
        "rating": "Strong Fundamentals" if score >= 75 else "Healthy Fundamentals" if score >= 55 else "Moderate Fundamentals" if score >= 40 else "Weak Fundamentals"
    }
