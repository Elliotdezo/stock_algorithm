# Multi-Ticker Backtesting Engine

A Python-based backtesting engine using **Backtrader**, **Yahoo Finance**, and **SQLite** to simulate moving average crossover strategies on multiple stocks at once.

---

## Features

-  Moving average crossover strategy
-  Multi-ticker support (e.g., AAPL, MSFT, GOOGL)
-  Position sizing based on available cash
-  Logs PnL, size, time held, cash balance per trade
-  Tracks and saves equity curve daily
-  Stores results in a local SQLite database (`stock_datas.db`)
-  Optional stop-loss / take-profit support (coming soon)
- More to come

---



```bash
pip install backtrader yfinance pandas matplotlib