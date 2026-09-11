# Stock Market Analyzer Agent - Technical Specification (`Spec.md`)

## 1. Overview
The **Stock Market Analyzer Agent** is an intelligent, multi-dimensional equity analysis platform designed to analyze stocks, ETFs, and market indices. It leverages real-time and historical financial data, statistical technical indicators, fundamental valuation models, and automated analytical reasoning to produce actionable insights and risk-adjusted market signals.

---

## 2. Agent Architecture & Capabilities

```
+-----------------------------------------------------------------------+
|                     Stock Market Analyzer Agent                       |
+-----------------------------------------------------------------------+
                                   |
        +--------------------------+--------------------------+
        |                          |                          |
        v                          v                          v
+------------------+     +------------------+     +------------------+
| Technical Engine |     | Fundamental Engine|    | Sentiment Engine |
+------------------+     +------------------+     +------------------+
| - SMA / EMA      |     | - Key Ratios     |     | - News Parser    |
| - RSI & MACD     |     | - Financials     |     | - Headline NLP   |
| - Bollinger Bands|     | - FCF & Margins  |     | - Sentiment Score|
| - Volume & VWAP  |     | - Growth Rates   |     | - Impact Summary |
+------------------+     +------------------+     +------------------+
        |                          |                          |
        +--------------------------+--------------------------+
                                   |
                                   v
                      +-------------------------+
                      | Reasoning & Synthesis   |
                      | - Bull/Bear Thesis      |
                      | - Risk Matrix           |
                      | - Signal Generation     |
                      +-------------------------+
                                   |
                                   v
                      +-------------------------+
                      | Streamlit Interactive UI|
                      +-------------------------+
```

---

## 3. Detailed Agent Skills & Tools

### Skill 1: Data Ingestion (`data_fetcher.py`)
- **Real-time & Historical Data**: Fetch daily/weekly price histories, volume metrics, split/dividend adjustments via `yfinance`.
- **Financial Statements**: Parse Balance Sheet, Income Statement, and Cash Flow Statement (quarterly & annual).
- **Company Profile & Metrics**: Key stats including Market Cap, Enterprise Value, Beta, 52-week High/Low, Float, Short Interest.

### Skill 2: Technical Analysis Engine (`technical_analysis.py`)
- **Trend Indicators**:
  - Simple Moving Averages (SMA 20, 50, 200).
  - Exponential Moving Averages (EMA 12, 26).
  - Golden Cross & Death Cross Detection.
- **Momentum & Oscillators**:
  - Relative Strength Index (RSI - 14 period) with Overbought (>70) and Oversold (<30) detection.
  - Moving Average Convergence Divergence (MACD, Signal Line, Histogram).
- **Volatility & Bands**:
  - Bollinger Bands (20-day SMA, ±2 Std Dev).
  - Average True Range (ATR).
- **Volume Metrics**:
  - Volume SMA (20-day).
  - On-Balance Volume (OBV) trend direction.

### Skill 3: Fundamental Analysis Engine (`fundamental_analysis.py`)
- **Valuation Ratios**: Trailing P/E, Forward P/E, PEG Ratio, Price-to-Sales (P/S), Price-to-Book (P/B), EV/EBITDA.
- **Profitability & Efficiency**: Gross Margin, Operating Margin, Profit Margin, Return on Equity (ROE), Return on Assets (ROA).
- **Balance Sheet Health**: Current Ratio, Quick Ratio, Debt-to-Equity (D/E), Total Cash vs Total Debt.
- **Growth Dynamics**: YoY Revenue Growth, YoY Earnings Growth, Free Cash Flow trend.

### Skill 4: News & Sentiment Scoring Engine (`sentiment_analysis.py`)
- **Headline Aggregation**: Parse top financial news headlines and publisher timestamps for the given symbol.
- **Rule-based NLP Sentiment**: Score sentiment polarity (-1.0 Bearish to +1.0 Bullish) across key financial keywords.
- **Impact Assessment**: Classify catalyst types (Earnings, Analyst Upgrade/Downgrade, Product Launch, Macro/Regulatory).

### Skill 5: Agent Reasoning & Synthesis (`market_agent.py`)
- **Signal Aggregation**: Synthesize technical scores, fundamental health, and news sentiment into a overall composite rating (Bullish, Moderately Bullish, Neutral, Moderately Bearish, Bearish).
- **Investment Thesis Generator**: Construct explicit Bullish Case, Bearish Case, and Key Risks.
- **Score Matrix**: Provide normalized scores (0-100) for Technical Health, Fundamental Valuation, Financial Strength, and Sentiment.

---

## 4. User Interface Specification (`app.py`)
- **Theme**: Premium modern dark mode with custom CSS styles, vibrant glassmorphism cards, and high contrast data tables.
- **Control Sidebar**: Ticker input, date range selector (1M, 3M, 6M, 1Y, 2Y, 5Y, Max), benchmark comparison (S&P 500 / NASDAQ), indicator toggles.
- **Interactive Tabs**:
  1. **Overview**: Key metrics ticker grid, overall Agent Signal badge, interactive price/volume chart.
  2. **Technical Analysis**: Dedicated price chart with SMA/EMA overlays, RSI subplot, MACD subplot, Bollinger Bands, signal breakdown table.
  3. **Fundamental Analysis**: Financial ratio breakdown, quarterly revenue/earnings chart, Balance Sheet & Cash Flow highlights.
  4. **News & Sentiment**: Recent headlines list with sentiment badges, sentiment score breakdown dial.
  5. **Agent Intelligence Report**: Detailed synthesis, Bull/Bear thesis, risk radar, and executive summary.

---

## 5. Technology Stack
- **Language**: Python 3.10+
- **Data Source**: `yfinance`
- **Data Processing**: `pandas`, `numpy`
- **Visualization**: `plotly`
- **UI Framework**: `streamlit`