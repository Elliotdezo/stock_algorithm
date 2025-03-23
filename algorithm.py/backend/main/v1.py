import numpy as np
import pandas as pd
import yfinance as yf

# List of stock tickers to analyze
TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]  

# Parameters for backtesting
START_DATE = "2010-06-29"
END_DATE = "2020-01-01"
VOLUME_FILTER = 1_000_000  # Minimum average daily volume
MARKET_CAP_FILTER = 5000_000_000  # Minimum market cap ($50B)


def fetch_stock_data(ticker):
    """Fetch historical stock data and fundamental info from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=START_DATE, end=END_DATE, auto_adjust=False)

        if df.empty:
            print(f"No data for {ticker}")
            return None, None

        df["Adj Close"] = df.get("Adj Close", df["Close"])  # Ensure 'Adj Close' exists
        df.dropna(inplace=True)

        return df, stock
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None, None


def apply_filters(df, stock):
    """Apply stock filters based on volume and market cap."""
    if df is None or df.empty or stock is None:
        return False

    info = stock.info

    # Get market cap and ensure it's available
    market_cap = info.get("marketCap", 0)
    if market_cap < MARKET_CAP_FILTER:
        return False  # Exclude low market cap stocks

    # Check average trading volume over the last 50 days
    avg_volume = np.mean(df["Volume"][-50:])
    if avg_volume < VOLUME_FILTER:
        return False  # Exclude low-volume stocks

    return True


if __name__ == "__main__":
    screened_stocks = []

    for ticker in TICKERS:
        print(f"Processing {ticker}...")
        stock_data, stock_info = fetch_stock_data(ticker)

        if stock_data is not None and stock_info is not None:
            if apply_filters(stock_data, stock_info):
                screened_stocks.append(ticker)

    print("\nScreened Stocks:", screened_stocks)