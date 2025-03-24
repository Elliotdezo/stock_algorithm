import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# === CONFIGURATION === #
DB_PATH = "stock_datas.db"
EQUITY_TABLE = "equity_curve"
TICKER = "AAPL"  # Change this if you're using multiple tickers

# === LOAD EQUITY CURVE FROM DATABASE === #
def load_equity_curve():
    conn = sqlite3.connect(DB_PATH)
    query = f"""
        SELECT date, equity FROM {EQUITY_TABLE}
        WHERE ticker = ?
        ORDER BY date ASC
    """
    df = pd.read_sql_query(query, conn, params=(TICKER,))
    conn.close()

    df['date'] = pd.to_datetime(df['date'])
    return df

# === PLOT EQUITY CURVE === #
def plot_equity(df):
    plt.figure(figsize=(12, 6))
    plt.plot(df['date'], df['equity'], linewidth=2, label="Equity")
    plt.title(f"Equity Curve for {TICKER}", fontsize=16)
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value ($)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

# === MAIN === #
if __name__ == "__main__":
    equity_df = load_equity_curve()
    if equity_df.empty:
        print("❌ No equity data found. Did you run the backtest?")
    else:
        plot_equity(equity_df)