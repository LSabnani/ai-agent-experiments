import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from market_agent import MarketAnalyzerAgent
from sector_analysis import fetch_sector_performance, fetch_top_stocks_performance, TOP_STOCKS_BY_SECTOR

# 1. Page Configuration
st.set_page_config(
    page_title="Stock Market Analyzer Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Custom Modern Styling (Glassmorphism & Rich Dark Palette)
st.markdown("""
<style>
    /* Dark theme overrides */
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38BDF8 0%, #818CF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #94A3B8;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        backdrop-filter: blur(10px);
        margin-bottom: 12px;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-val {
        font-size: 1.5rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-top: 4px;
    }
    .signal-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1.1rem;
        color: #0F172A;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .thesis-box {
        background: rgba(30, 41, 59, 0.8);
        border-left: 4px solid #38BDF8;
        border-radius: 8px;
        padding: 16px;
        margin-top: 10px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #1E293B;
        border-radius: 8px;
        color: #94A3B8;
        padding: 0px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #38BDF8 !important;
        color: #0F172A !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Control Inputs
st.sidebar.markdown("## ⚙️ Agent Parameters")
ticker = st.sidebar.text_input("Stock Ticker", value="NVDA").upper().strip()
period = st.sidebar.selectbox("History Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Chart Overlay Options")
show_sma20 = st.sidebar.checkbox("SMA 20", value=True)
show_sma50 = st.sidebar.checkbox("SMA 50", value=True)
show_sma200 = st.sidebar.checkbox("SMA 200", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands", value=True)

st.sidebar.markdown("---")
st.sidebar.caption("Powered by MarketAnalyzerAgent • Python & Streamlit")

# Main Header
st.markdown("<div class='main-header'>📈 Stock Market Analyzer Agent</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Multi-factor technical, fundamental, and sentiment intelligence engine</div>", unsafe_allow_html=True)

if not ticker:
    st.info("Please enter a stock ticker in the sidebar (e.g. AAPL, NVDA, TSLA, MSFT).")
    st.stop()

# Run Agent
with st.spinner(f"Analyzing {ticker} across Technicals, Fundamentals & News Sentiment..."):
    try:
        agent = MarketAnalyzerAgent(ticker, period=period)
        res = agent.run_full_analysis()
    except Exception as e:
        st.error(f"Error fetching data or running analysis for '{ticker}': {str(e)}")
        st.stop()

# Top Summary Header Bar
c1, c2, c3, c4 = st.columns([2, 1, 1, 1])

with c1:
    st.markdown(f"### {res['company_name']} ({res['ticker_symbol']})")
    st.markdown(
        f"<span class='signal-badge' style='background-color: {res['signal_color']};'>{res['overall_signal']} ({res['composite_score']}/100)</span>",
        unsafe_allow_html=True
    )

info = res['info']
current_price = res['technical']['latest_metrics']['close']

with c2:
    st.metric("Current Price", f"${current_price:.2f}" if current_price else "N/A")
with c3:
    market_cap = res['fundamental_metrics'].get("Market Cap", "N/A")
    st.metric("Market Cap", market_cap)
with c4:
    pe_ratio = res['fundamental_metrics'].get("Trailing P/E", "N/A")
    st.metric("Trailing P/E", pe_ratio)

st.markdown("---")

# Main Multi-Tab Interface
tab_overview, tab_sectors, tab_tech, tab_fund, tab_sent, tab_agent = st.tabs([
    "📊 Overview & Charts",
    "🏆 Sector Winners & Losers",
    "📈 Technical Analysis",
    "🏢 Fundamentals & Valuation",
    "📰 News & Sentiment",
    "🤖 Agent Synthesis Report"
])

# ---------------------------------------------------------
# TAB 1: OVERVIEW & INTERACTIVE PRICE CHART
# ---------------------------------------------------------
with tab_overview:
    df = res['raw_df']
    
    # Create Subplot: Top = Candlestick/Line, Bottom = Volume
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    
    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df['date'] if 'date' in df.columns else df.index,
            open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            name="Price"
        ),
        row=1, col=1
    )
    
    # Moving Averages Overlays
    if show_sma20 and 'sma_20' in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df['sma_20'], line=dict(color='#FBBF24', width=1.5), name="SMA 20"), row=1, col=1)
    if show_sma50 and 'sma_50' in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df['sma_50'], line=dict(color='#38BDF8', width=1.5), name="SMA 50"), row=1, col=1)
    if show_sma200 and 'sma_200' in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df['sma_200'], line=dict(color='#A855F7', width=1.5), name="SMA 200"), row=1, col=1)
        
    if show_bb and 'bb_upper' in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df['bb_upper'], line=dict(color='rgba(255,255,255,0.3)', dash='dot'), name="BB Upper"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['bb_lower'], line=dict(color='rgba(255,255,255,0.3)', dash='dot'), name="BB Lower"), row=1, col=1)

    # Volume Bar Chart
    colors = ['#10B981' if close >= open_p else '#EF4444' for close, open_p in zip(df['close'], df['open'])]
    fig.add_trace(
        go.Bar(x=df['date'], y=df['volume'], marker_color=colors, name="Volume"),
        row=2, col=1
    )

    fig.update_layout(
        template="plotly_dark",
        height=550,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_rangeslider_visible=False,
        paper_bgcolor='rgba(15, 23, 42, 0)',
        plot_bgcolor='rgba(15, 23, 42, 0)'
    )
    st.plotly_chart(fig, use_container_width=True)

    # Quick Stats Grid
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown("<div class='metric-card'><div class='metric-label'>52-Wk Range</div>"
                    f"<div class='metric-val'>{res['fundamental_metrics'].get('52 Week Low', 'N/A')} - {res['fundamental_metrics'].get('52 Week High', 'N/A')}</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown("<div class='metric-card'><div class='metric-label'>Beta</div>"
                    f"<div class='metric-val'>{res['fundamental_metrics'].get('Beta', 'N/A')}</div></div>", unsafe_allow_html=True)
    with m3:
        st.markdown("<div class='metric-card'><div class='metric-label'>Forward P/E</div>"
                    f"<div class='metric-val'>{res['fundamental_metrics'].get('Forward P/E', 'N/A')}</div></div>", unsafe_allow_html=True)
    with m4:
        st.markdown("<div class='metric-card'><div class='metric-label'>Profit Margin</div>"
                    f"<div class='metric-val'>{res['fundamental_metrics'].get('Profit Margin', 'N/A')}</div></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 2: SECTOR WINNERS & LOSERS
# ---------------------------------------------------------
with tab_sectors:
    st.markdown("### 🏆 Sector Performance (Daily Winners & Losers)")
    st.markdown("Real-time benchmark analysis across all 11 major S&P 500 sectors via Sector SPDR ETFs.")
    
    with st.spinner("Fetching live sector ETF data..."):
        df_sec = fetch_sector_performance()
        
    if not df_sec.empty:
        col_sec1, col_sec2 = st.columns([1.5, 1])
        
        with col_sec1:
            colors = ['#10B981' if c >= 0 else '#EF4444' for c in df_sec['Change %']]
            fig_sec = go.Figure(data=[
                go.Bar(
                    x=df_sec['Change %'],
                    y=df_sec['Sector'],
                    orientation='h',
                    marker_color=colors,
                    text=[f"{c:+.2f}%" for c in df_sec['Change %']],
                    textposition='outside'
                )
            ])
            fig_sec.update_layout(
                template="plotly_dark",
                height=450,
                xaxis_title="Daily Change %",
                yaxis=dict(autorange="reversed"),
                margin=dict(l=20, r=40, t=20, b=20),
                paper_bgcolor='rgba(15, 23, 42, 0)',
                plot_bgcolor='rgba(15, 23, 42, 0)'
            )
            st.plotly_chart(fig_sec, use_container_width=True)
            
        with col_sec2:
            st.markdown("#### 🥇 Sector Leaderboard")
            formatted_df = df_sec.copy()
            formatted_df['Change %'] = formatted_df['Change %'].apply(lambda x: f"{x:+.2f}%")
            formatted_df['Price'] = formatted_df['Price'].apply(lambda x: f"${x:.2f}")
            st.dataframe(formatted_df, use_container_width=True, hide_index=True)
            
        st.markdown("---")
        st.markdown("### 🏆 Top 3 Market Leaders by Sector")
        top_perf = fetch_top_stocks_performance()
        
        sec_cols = st.columns(3)
        sectors_list = list(TOP_STOCKS_BY_SECTOR.keys())
        for idx, sec_name in enumerate(sectors_list):
            col_target = sec_cols[idx % 3]
            with col_target:
                st.markdown(f"<div class='metric-card'><strong>{sec_name}</strong><br><small>Top 3 Stocks:</small><br>", unsafe_allow_html=True)
                if sec_name in top_perf:
                    for item in top_perf[sec_name]:
                        color = "#10B981" if item['Change %'] >= 0 else "#EF4444"
                        st.markdown(
                            f"• <strong>{item['Symbol']}</strong>: ${item['Price']:.2f} "
                            f"<span style='color:{color}; font-weight:bold;'>({item['Change %']:+.2f}%)</span>",
                            unsafe_allow_html=True
                        )
                else:
                    st.write(", ".join(TOP_STOCKS_BY_SECTOR[sec_name]))
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("Sector performance data currently unavailable.")

# ---------------------------------------------------------
# TAB 3: TECHNICAL ANALYSIS
# ---------------------------------------------------------
with tab_tech:
    st.markdown(f"### Technical Signal Rating: **{res['technical']['recommendation']}** ({res['technical']['score']}/100)")
    
    col_t1, col_t2 = st.columns([2, 1])
    
    with col_t1:
        # RSI & MACD Subplots
        fig_tech = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.5, 0.5])
        
        # RSI
        fig_tech.add_trace(go.Scatter(x=df['date'], y=df['rsi'], line=dict(color='#38BDF8', width=2), name="RSI (14)"), row=1, col=1)
        fig_tech.add_hline(y=70, line_dash="dash", line_color="#EF4444", row=1, col=1)
        fig_tech.add_hline(y=30, line_dash="dash", line_color="#10B981", row=1, col=1)
        
        # MACD
        fig_tech.add_trace(go.Scatter(x=df['date'], y=df['macd'], line=dict(color='#FBBF24', width=1.5), name="MACD"), row=2, col=1)
        fig_tech.add_trace(go.Scatter(x=df['date'], y=df['macd_signal'], line=dict(color='#A855F7', width=1.5), name="Signal"), row=2, col=1)
        fig_tech.add_trace(go.Bar(x=df['date'], y=df['macd_hist'], name="Hist"), row=2, col=1)
        
        fig_tech.update_layout(
            template="plotly_dark",
            height=400,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor='rgba(15, 23, 42, 0)',
            plot_bgcolor='rgba(15, 23, 42, 0)'
        )
        st.plotly_chart(fig_tech, use_container_width=True)

    with col_t2:
        st.markdown("#### 🎯 Support & Resistance Pivot Levels")
        piv = res['technical'].get('pivots', {})
        if piv:
            curr = res['technical']['latest_metrics']['close']
            st.markdown(f"**Current Price**: `${curr:.2f}` | **Pivot Point (P)**: `${piv['pivot']:.2f}`")
            
            s_r_df = pd.DataFrame([
                {"Level": "Resistance 3 (R3)", "Price": f"${piv['r3']:.2f}", "Distance": f"{((piv['r3']-curr)/curr)*100:+.2f}%"},
                {"Level": "Resistance 2 (R2)", "Price": f"${piv['r2']:.2f}", "Distance": f"{((piv['r2']-curr)/curr)*100:+.2f}%"},
                {"Level": "Resistance 1 (R1)", "Price": f"${piv['r1']:.2f}", "Distance": f"{((piv['r1']-curr)/curr)*100:+.2f}%"},
                {"Level": "Pivot Point (P)", "Price": f"${piv['pivot']:.2f}", "Distance": f"{((piv['pivot']-curr)/curr)*100:+.2f}%"},
                {"Level": "Support 1 (S1)", "Price": f"${piv['s1']:.2f}", "Distance": f"{((piv['s1']-curr)/curr)*100:+.2f}%"},
                {"Level": "Support 2 (S2)", "Price": f"${piv['s2']:.2f}", "Distance": f"{((piv['s2']-curr)/curr)*100:+.2f}%"},
                {"Level": "Support 3 (S3)", "Price": f"${piv['s3']:.2f}", "Distance": f"{((piv['s3']-curr)/curr)*100:+.2f}%"},
            ])
            st.dataframe(s_r_df, use_container_width=True, hide_index=True)
            
        st.markdown("---")
        st.markdown("#### Technical Signal Signals Identified:")
        for sig in res['technical']['signals']:
            if "Bullish" in sig or "Golden Cross" in sig or "above" in sig or "Oversold" in sig:
                st.success(f"✔️ {sig}")
            else:
                st.warning(f"⚠️ {sig}")

# ---------------------------------------------------------
# TAB 3: FUNDAMENTALS & VALUATION
# ---------------------------------------------------------
with tab_fund:
    st.markdown(f"### Fundamental Health: **{res['fundamental_summary']['rating']}** ({res['fundamental_summary']['score']}/100)")
    
    col_f1, col_f2 = st.columns([1, 1])
    
    with col_f1:
        st.markdown("#### Key Valuation & Health Ratios")
        metrics_df = pd.DataFrame(
            list(res['fundamental_metrics'].items()),
            columns=["Metric", "Value"]
        )
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)

    with col_f2:
        st.markdown("#### Key Fundamental Insights")
        for ins in res['fundamental_summary']['insights']:
            st.info(f"💡 {ins}")
            
        # Display Quarterly Financial Chart if available
        q_fin = res['quarterly_financials']
        if not q_fin.empty and "Total Revenue" in q_fin.index:
            st.markdown("#### Recent Quarterly Revenue Trend")
            rev_series = q_fin.loc["Total Revenue"].dropna() / 1e9
            fig_rev = go.Figure(data=[go.Bar(x=[str(d)[:10] for d in rev_series.index], y=rev_series.values, marker_color="#38BDF8")])
            fig_rev.update_layout(
                template="plotly_dark",
                height=250,
                title="Revenue ($ Billions)",
                paper_bgcolor='rgba(15, 23, 42, 0)',
                plot_bgcolor='rgba(15, 23, 42, 0)'
            )
            st.plotly_chart(fig_rev, use_container_width=True)

# ---------------------------------------------------------
# TAB 4: NEWS & SENTIMENT
# ---------------------------------------------------------
with tab_sent:
    sent = res['sentiment']
    st.markdown(f"### News Sentiment Rating: **{sent['label']}** ({sent['score']}/100)")
    
    s1, s2, s3 = st.columns(3)
    s1.metric("Bullish Headlines", sent['bullish_count'])
    s2.metric("Neutral Headlines", sent['neutral_count'])
    s3.metric("Bearish Headlines", sent['bearish_count'])
    
    st.markdown("---")
    st.markdown("### 📰 EE Times Industry Cross-Validation")
    ee = res.get('eetimes', {})
    if ee:
        st.info(f"**Source**: {ee.get('source', 'EE Times')}")
        st.markdown(f"**Editorial Stance / Trend**: `{ee.get('sentiment', 'Neutral')}`")
        st.markdown(f"**Summary**: {ee.get('summary', '')}")
        st.markdown("**Key Topics Covered in EE Times:**")
        for top in ee.get('topics', []):
            st.markdown(f"- 🔌 {top}")
            
    st.markdown("---")
    st.markdown("#### Recent Headlines & Agent Sentiment Score")
    
    if sent['processed_news']:
        for item in sent['processed_news']:
            badge_color = "#10B981" if item['sentiment'] == "Bullish" else "#EF4444" if item['sentiment'] == "Bearish" else "#94A3B8"
            st.markdown(
                f"<div style='background: rgba(30,41,59,0.5); padding:10px; border-radius:8px; margin-bottom:8px;'>"
                f"<span style='background-color:{badge_color}; color:#0F172A; font-weight:bold; padding:2px 8px; border-radius:4px;'>{item['sentiment']}</span> "
                f"<strong><a href='{item['link']}' target='_blank' style='color:#F8FAFC; text-decoration:none;'>{item['title']}</a></strong> "
                f"<span style='color:#64748B; font-size:0.85rem;'>— {item['publisher']}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.write("No recent news headlines available for this symbol.")

# ---------------------------------------------------------
# TAB 5: AGENT INTELLIGENCE SYNTHESIS REPORT
# ---------------------------------------------------------
with tab_agent:
    st.markdown("### 🤖 Agent Executive Synthesis & Thesis")
    
    st.markdown(f"<div class='thesis-box'>{res['agent_thesis']['summary']}</div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_b, col_r = st.columns(2)
    
    with col_b:
        st.markdown("#### 🟢 Bullish Drivers & Catalysts")
        for bull in res['agent_thesis']['bull_drivers']:
            st.markdown(f"- {bull}")
            
    with col_r:
        st.markdown("#### 🔴 Key Bear Risks & Headwinds")
        for bear in res['agent_thesis']['bear_risks']:
            st.markdown(f"- {bear}")
