import backtrader as bt
import yfinance as yf
import pandas as pd
import sqlite3
import logging
import time
from datetime import datetime
import numpy as np

# === CONFIGURATION === #
INITIAL_CASH = 100000
TICKERS = ['MSFT', 'AAPL', 'META', 'NVDA']
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

# === LOGGING === #
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.FileHandler("backtest_log.txt"), logging.StreamHandler()]
)

# === HELPER: POSITION SIZING FUNCTION === #
def calculate_order_size(price, cash, max_weight=MAX_POSITION_WEIGHT):
    try:
        max_position_value = cash * max_weight
        size = int(max_position_value // price)
        return size if size > 0 else 0
    except ZeroDivisionError:
        logging.error("Price is zero during position sizing!")
        return 0

# === STRATEGY === #
class MovingAverageCrossoverStrategy(bt.Strategy):
    params = (
        ('short_period', 20),
        ('long_period', 50),
    )

    def __init__(self):
        self.smas = {}
        self.orders = {}
        self.buy_price = {}
        self.buy_size = {}
        self.buy_datetime = {}
        self.equity_curve = []
        self.trades = []

        for i, d in enumerate(self.datas):
            self.smas[d._name] = {
                'short': bt.ind.SMA(d.close, period=self.params.short_period),
                'long': bt.ind.SMA(d.close, period=self.params.long_period),
            }
            self.orders[d._name] = None

    def next(self):
        date = self.datas[0].datetime.date(0).strftime('%Y-%m-%d')
        equity = round(self.broker.getvalue(), 2)
        self.equity_curve.append((date, 'PORTFOLIO', equity))

        for d in self.datas:
            name = d._name
            if self.orders[name]:
                continue

            sma_short = self.smas[name]['short']
            sma_long = self.smas[name]['long']

            current_price = round(d.close[0], 2)
            current_cash = self.broker.get_cash()
            size = calculate_order_size(current_price, current_cash)

            if not self.getposition(d).size:
                if sma_short[0] > sma_long[0] and sma_short[-1] <= sma_long[-1]:
                    self.orders[name] = self.buy(data=d, size=size)
            elif sma_short[0] < sma_long[0] and sma_short[-1] >= sma_long[-1]:
                self.orders[name] = self.sell(data=d, size=self.buy_size.get(name, 0))

    def notify_order(self, order):
        data = order.data
        name = data._name

        if order.status == order.Completed:
            if order.isbuy():
                self.buy_price[name] = order.executed.price
                self.buy_size[name] = order.executed.size
                self.buy_datetime[name] = data.datetime.datetime(0)

            elif order.issell():
                sell_price = order.executed.price
                size = order.executed.size
                buy_price = self.buy_price.get(name, 0)
                pnl = round((sell_price - buy_price) * size, 2)
                self.trades.append(pnl)

                portfolio_value = self.broker.getvalue()
                trade_impact_pct = round((pnl / portfolio_value) * 100, 4) if portfolio_value else 0.0
                cash_balance = round(self.broker.get_cash(), 2)

                sell_datetime = data.datetime.datetime(0)
                buy_datetime = self.buy_datetime[name]
                time_held = str(sell_datetime - buy_datetime)
                trade_time_str = sell_datetime.strftime('%Y-%m-%d')
                buy_time_str = buy_datetime.strftime('%Y-%m-%d')

                logging.info(
                    f"{trade_time_str} | 💰 TRADE CLOSED ({name}) | Buy: {buy_time_str} | "
                    f"Sell: {trade_time_str} | PnL: ${pnl:.2f} | "
                    f"Impact: {trade_impact_pct:.4f}% | Held: {time_held}"
                )

                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(f"""
                        INSERT INTO {TRADE_TABLE} (datetime, ticker, buy_price, sell_price, size, pnl, cash_after_trade, time_held)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (trade_time_str, name, buy_price, sell_price, size, pnl, cash_balance, time_held))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logging.error(f"DB error on trade insert: {e}")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logging.warning(f"⚠️ Order failed for {name}")

        self.orders[name] = None

    def stop(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.executemany(f"""
                INSERT INTO {EQUITY_TABLE} (date, ticker, equity)
                VALUES (?, ?, ?)
            """, self.equity_curve)
            conn.commit()
            conn.close()
            logging.info(f"📊 Equity curve saved for portfolio")
        except Exception as e:
            logging.error(f"Equity curve DB error: {e}")

        try:
            if len(self.equity_curve) > 1:
                values = [e[2] for e in self.equity_curve]
                returns = np.diff(values) / values[:-1]

                avg_return = np.mean(returns)
                std_dev = np.std(returns)
                downside_dev = np.std([r for r in returns if r < 0])
                max_drawdown = np.max(1 - np.array(values) / np.maximum.accumulate(values))

                sharpe = (avg_return / std_dev) * np.sqrt(252) if std_dev > 0 else 0
                sortino = (avg_return / downside_dev) * np.sqrt(252) if downside_dev > 0 else 0
                calmar = (values[-1] - values[0]) / values[0] / max_drawdown if max_drawdown > 0 else 0

                logging.info(f"📈 Portfolio Sharpe Ratio: {sharpe:.2f}")
                logging.info(f"📉 Portfolio Sortino Ratio: {sortino:.2f}")
                logging.info(f"🔥 Portfolio Calmar Ratio: {calmar:.2f}")
        except Exception as e:
            logging.error(f"Error calculating performance ratios: {e}")

        # === TRADE METRICS === #
        try:
            if self.trades:
                wins = [p for p in self.trades if p > 0]
                losses = [p for p in self.trades if p <= 0]
                win_rate = len(wins) / len(self.trades)
                loss_rate = 1 - win_rate
                avg_win = np.mean(wins) if wins else 0
                avg_loss = abs(np.mean(losses)) if losses else 0
                reward_risk = (avg_win / avg_loss) if avg_loss else 0
                expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
                kelly = win_rate - (loss_rate / reward_risk) if reward_risk != 0 else 0

                logging.info(f"🎯 Win Rate: {win_rate:.2%} | Loss Rate: {loss_rate:.2%}")
                logging.info(f"📊 Avg Win: ${avg_win:.2f} | Avg Loss: -${avg_loss:.2f}")
                logging.info(f"⚖️ Reward:Risk: {reward_risk:.2f} | Expectancy: ${expectancy:.2f} | Kelly %: {kelly:.2%}")
        except Exception as e:
            logging.error(f"Error calculating trade stats: {e}")

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

# === FETCH DATA === #
def fetch_data(ticker, start, end):
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    df.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
    df.index = pd.to_datetime(df.index)
    df.dropna(inplace=True)
    return df

# === RUN BACKTEST === #
def run_backtest():
    start_time = time.time()
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MovingAverageCrossoverStrategy, **STRATEGY_PARAMS)
    cerebro.broker.set_cash(INITIAL_CASH)

    for ticker in TICKERS:
        df = fetch_data(ticker, START_DATE, END_DATE)
        if df.empty:
            logging.warning(f"No data for {ticker}, skipping.")
            continue
        data_feed = PandasYahooData(dataname=df)
        data_feed._name = ticker
        cerebro.adddata(data_feed)

    logging.info(f"\n📈 Running portfolio backtest with ${INITIAL_CASH} starting capital.")
    cerebro.run()
    final_val = cerebro.broker.getvalue()
    elapsed = time.time() - start_time
    logging.info(f"✅ Final Portfolio Value: ${final_val:.2f} | Time: {elapsed:.2f}s")
    cerebro.plot()

# === MAIN === #
if __name__ == '__main__':
    run_backtest()
