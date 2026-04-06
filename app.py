import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import anthropic

st.set_page_config(page_title="Finance Dashboard", layout="wide")

st.title("Finance Dashboard")
st.markdown("Built by Ryan Donsky")

tab1, tab2, tab3 = st.tabs(["Stock Screener", "Portfolio Tracker", "AI Earnings Analyser"])

with tab1:
    st.header("Stock Screener")
    tickers_input = st.text_input("Enter tickers separated by commas", "AAPL, MSFT, TSLA, NVDA, GS, JPM")
    
    if st.button("Run Screener"):
        tickers = [t.strip() for t in tickers_input.split(",")]
        data = []
        progress = st.progress(0)
        
        for i, stock in enumerate(tickers):
            try:
                info = yf.Ticker(stock).info
                history = yf.Ticker(stock).history(period="1y")
                annual_return = ((history["Close"].iloc[-1] - history["Close"].iloc[0]) / history["Close"].iloc[0]) * 100
                volatility = history["Close"].pct_change().std() * 100
                data.append({
                    "Ticker": stock,
                    "Price": round(info.get("currentPrice", 0), 2),
                    "P/E Ratio": round(info.get("trailingPE", 0), 1),
                    "1Y Return (%)": round(annual_return, 1),
                    "Volatility (%)": round(volatility, 2),
                    "Market Cap ($B)": round(info.get("marketCap", 0) / 1e9, 1)
                })
            except Exception as e:
                st.write(f"Error with {stock}: {e}")
            progress.progress((i + 1) / len(tickers))
        
        df = pd.DataFrame(data)

        if df.empty or "1Y Return (%)" not in df.columns:
            st.warning("No valid data found. Try different tickers.")
            st.stop()

        df = df.sort_values("1Y Return (%)", ascending=False).reset_index(drop=True)    
        st.dataframe(df, use_container_width=True)
        
        fig, ax = plt.subplots(figsize=(10, 5))
        colors = ["#1D9E75" if x > 0 else "#E24B4A" for x in df["1Y Return (%)"]]
        ax.barh(df["Ticker"], df["1Y Return (%)"], color=colors)
        ax.set_title("1 Year Return (%)")
        ax.axvline(x=0, color="black", linewidth=0.5)
        st.pyplot(fig)

with tab2:
    st.header("Portfolio Tracker")
    st.markdown("Enter your portfolio below — one stock per line in the format `TICKER, SHARES`")
    
    portfolio_input = st.text_area("Portfolio", "AAPL, 10\nNVDA, 5\nGS, 8\nDPZ, 6\nMSFT, 7")
    
    if st.button("Track Portfolio"):
        portfolio = {}
        for line in portfolio_input.strip().split("\n"):
            parts = line.split(",")
            if len(parts) == 2:
                portfolio[parts[0].strip()] = int(parts[1].strip())
        
        data = {}
        for stock in portfolio:
            history = yf.Ticker(stock).history(period="1y")
            data[stock] = history["Close"]
        
        df = pd.DataFrame(data).dropna()
        start_prices = df.iloc[0]
        current_prices = df.iloc[-1]
        
        rows = []
        total_invested = 0
        total_current = 0
        
        for stock, shares in portfolio.items():
            invested = round(start_prices[stock] * shares, 2)
            current = round(current_prices[stock] * shares, 2)
            gain = round(current - invested, 2)
            pct = round((gain / invested) * 100, 1)
            total_invested += invested
            total_current += current
            rows.append({"Ticker": stock, "Shares": shares, "Invested ($)": invested, "Current ($)": current, "Gain/Loss ($)": gain, "Return (%)": pct})
        
        summary_df = pd.DataFrame(rows)
        
        total_gain = round(total_current - total_invested, 2)
        total_pct = round((total_gain / total_invested) * 100, 1)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Invested", f"${round(total_invested, 2):,}")
        col2.metric("Current Value", f"${round(total_current, 2):,}")
        col3.metric("Total Return", f"{total_pct}%", f"${total_gain:,}")
        
        st.dataframe(summary_df, use_container_width=True)
        
        normalized = df / df.iloc[0] * 100
        fig, ax = plt.subplots(figsize=(12, 5))
        for stock in portfolio:
            ax.plot(normalized.index, normalized[stock], label=stock, linewidth=2)
        ax.axhline(y=100, color="black", linewidth=0.5, linestyle="--")
        ax.set_title("Portfolio Performance — 1 Year (Normalised to 100)")
        ax.legend()
        st.pyplot(fig)

with tab3:
    st.header("AI Earnings Analyser")
    api_key = st.text_input("Your Anthropic API key", type="password")
    transcript = st.text_area("Paste earnings call transcript here", height=250)
    
    if st.button("Analyse"):
        if not api_key:
            st.error("Please enter your API key")
        elif not transcript:
            st.error("Please paste a transcript")
        else:
            with st.spinner("Analysing..."):
                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1000,
                    messages=[{
                        "role": "user",
                        "content": f"""You are a senior equity research analyst. Analyse this earnings call transcript and provide a structured summary covering:

1. KEY FINANCIALS — revenue, margins, any key metrics mentioned
2. POSITIVES — what went well, beats, strong segments
3. RISKS & HEADWINDS — concerns, misses, challenges flagged
4. GUIDANCE — what management said about the future
5. ANALYST TAKE — one paragraph overall assessment

Transcript:
{transcript}"""
                    }]
                )
                st.markdown(response.content[0].text)
