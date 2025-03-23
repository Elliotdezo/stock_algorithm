import backtrader as bt
import yfinance as yf
import pandas as pd
import sqlite3
from datetime import datetime

# === CONFIGURATION === #
INITIAL_CASH = 100000
TICKERS = ['AAPL', 'MSFT', 'GOOGL']
START_DATE = '2020-01-01'
END_DATE = '2025-01-01'
MAX_POSITION_WEIGHT = 0.5

# === DATABASE === #
DB_PATH = "stock_datas.db"
TRADE_TABLE = "backtestv1"
EQUITY_TABLE = "equity_curve"

# === STRATEGY PARAMETERS === #
STRATEGY_PARAMS = {
    'short_period': 20,
    'long_period': 50,
}

# === HELPER: POSITION SIZING FUNCTION === #
def calculate_order_size(price, cash, max_weight=MAX_POSITION_WEIGHT):
    max_position_value = cash * max_weight
    size = int(max_position_value // price)
    return size if size > 0 else 0

# === STRATEGY === #
class MovingAverageCrossoverStrategy(bt.Strategy):
    params = (
        ('short_period', 20),
        ('long_period', 50),
        ('ticker', None),
    )

    def __init__(self):
        self.ticker = self.params.ticker
        self.sma_short = bt.ind.SMA(self.data.close, period=self.params.short_period)
        self.sma_long = bt.ind.SMA(self.data.close, period=self.params.long_period)
        self.order = None
        self.buy_price = None
        self.buy_size = None
        self.buy_datetime = None
        self.equity_curve = []

    def next(self):
        if self.order:
            return

        current_price = round(self.data.close[0], 2)
        current_cash = self.broker.get_cash()
        size = calculate_order_size(current_price, current_cash)

        if size == 0:
            return

        if not self.position:
            if self.sma_short[0] > self.sma_long[0] and self.sma_short[-1] <= self.sma_long[-1]:
                self.order = self.buy(size=size)
        elif self.sma_short[0] < self.sma_long[0] and self.sma_short[-1] >= self.sma_long[-1]:
            self.order = self.sell(size=self.buy_size)

        date = self.data.datetime.date(0).strftime('%Y-%m-%d')
        equity = round(self.broker.getvalue(), 2)
        self.equity_curve.append((date, self.ticker, equity))

    def notify_order(self, order):
        if order.status == order.Completed:
            if order.isbuy():
                self.buy_price = round(order.executed.price, 2)
                self.buy_size = abs(round(order.executed.size))
                self.buy_datetime = self.data.datetime.datetime(0)

            elif order.issell():
                sell_price = round(order.executed.price, 2)
                size = abs(round(order.executed.size))
                buy_price = round(self.buy_price, 2)
                pnl = round((sell_price - buy_price) * size, 2)
                cash_balance = round(self.broker.get_cash(), 2)
                sell_datetime = self.data.datetime.datetime(0)
                time_held = str(sell_datetime - self.buy_datetime)
                exit_time = sell_datetime.strftime('%Y-%m-%d')

                print(f"\n💰 TRADE CLOSED ({self.ticker}):")
                print(f"  Bought at:     ${buy_price:.2f}")
                print(f"  Sold at:       ${sell_price:.2f}")
                print(f"  Size:          {size} shares")
                print(f"  PnL:           ${pnl:.2f}")
                print(f"  Time Held:     {time_held}")
                print(f"  Cash Balance:  ${cash_balance:.2f}")

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {TRADE_TABLE} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        datetime TEXT,
                        ticker TEXT,
                        buy_price REAL,
                        sell_price REAL,
                        size INTEGER,
                        pnl REAL,
                        cash_after_trade REAL,
                        time_held TEXT
                    )
                """)
                cursor.execute(f"""
                    INSERT INTO {TRADE_TABLE} (datetime, ticker, buy_price, sell_price, size, pnl, cash_after_trade, time_held)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (exit_time, self.ticker, buy_price, sell_price, size, pnl, cash_balance, time_held))
                conn.commit()
                conn.close()

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f"⚠️ Order failed for {self.ticker}")
        self.order = None

    def stop(self):
        if self.position:
            self.close()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {EQUITY_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                ticker TEXT,
                equity REAL
            )
        """)
        cursor.executemany(f"""
            INSERT INTO {EQUITY_TABLE} (date, ticker, equity)
            VALUES (?, ?, ?)
        """, self.equity_curve)
        conn.commit()
        conn.close()
        print(f"📊 Equity curve saved for {self.ticker}")

# === BACKTRADER DATA WRAPPER === #
class PandasYahooData(bt.feeds.PandasData):
    params = (
        ('datetime', None),
        ('open', 'Open'),
        ('high', 'High'),
        ('low', 'Low'),
        ('close', 'Close'),
        ('volume', 'Volume'),
        ('openinterest', -1),
    )

# === FETCH AND CLEAN YFINANCE DATA === #
def fetch_data(ticker, start, end):
    df = yf.download(
        ticker,
        start=start,
        end=end,
        progress=False,
        auto_adjust=False,
        group_by='ticker'
    )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    df.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
    df.index = pd.to_datetime(df.index)
    df.dropna(inplace=True)
    return df

# === RUN BACKTEST === #
def run_backtest(ticker):
    df = fetch_data(ticker, START_DATE, END_DATE)
    if df.empty:
        print(f"❌ No data for {ticker}. Skipping.")
        return

    cerebro = bt.Cerebro()
    cerebro.addstrategy(MovingAverageCrossoverStrategy, ticker=ticker, **STRATEGY_PARAMS)

    data_feed = PandasYahooData(dataname=df)
    cerebro.adddata(data_feed)
    cerebro.broker.set_cash(INITIAL_CASH)

    print(f"\n📈 Backtesting {ticker}...")
    print(f"Starting Portfolio Value: ${cerebro.broker.getvalue():.2f}")
    cerebro.run()
    print(f"Final Portfolio Value: ${cerebro.broker.getvalue():.2f}")
    cerebro.plot()

# === MAIN === #
if __name__ == '__main__':
    for ticker in TICKERS:
        run_backtest(ticker)
