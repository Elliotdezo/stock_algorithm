import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

# Define parameters
tickers = ["RGC", "JYD", "WGRX", "TOI","NVDA", "PLTR", "CRWD","MSTR", "MU"]  # Add more tickers as needed
start_date = pd.to_datetime("today") - pd.DateOffset(days=2000)
end_date = pd.to_datetime("today")

# Download stock data with auto_adjust=False
df = yf.download(tickers, start=start_date, end=end_date, auto_adjust=False)

# Use "Adj Close" if available, otherwise use "Close"
if "Adj Close" in df:
    df = df["Adj Close"]
else:
    df = df["Close"]

# Convert prices to daily percentage change
df = df.pct_change() * 100  # Convert to daily percentage change

# Remove the first NaN row (since `pct_change()` creates NaN for the first row)
df = df.iloc[1:]

# Convert daily percentage change to cumulative percentage change
df = (1 + df / 100).cumprod() * 100 - 100  # Convert to cumulative %

# Convert date index to years for x-axis labels
df["Year"] = df.index.year  # Extract years from index

# Change the style of plot
plt.style.use("dark_background")

# Create a color palette
palette = plt.get_cmap("Set1")

# Plot multiple stock tickers (cumulative percentage change)
num = 0
for column in df.drop("Year", axis=1):
    num += 1
    plt.plot(df.index, df[column], marker="", color=palette(num), linewidth=1, alpha=0.9, label=column)

# Format x-axis to show only distinct years
plt.xticks(ticks=pd.date_range(start=df.index.min(), end=df.index.max(), freq="YS"), 
           labels=pd.date_range(start=df.index.min(), end=df.index.max(), freq="YS").year)

# Add horizontal grid lines
plt.grid(axis='y', linestyle='--', alpha=0.5)  # Horizontal grille

# Add legend
plt.legend(loc=2, ncol=2)

# Add titles
plt.title("Bubble Backtesting Model v1.1.3", loc="left", fontsize=18, fontweight=0, color="orange")
plt.xlabel("Years")
plt.ylabel("Cumulative % Change")

# Dynamically adjust y-axis limits
y_min = df.iloc[:, :-1].min().min()  # Find lowest y-value
y_max = df.iloc[:, :-1].max().max()  # Find highest y-value
padding = (y_max - y_min) * 0.1  # Add 10% extra space above and below

plt.ylim(y_min - padding, y_max + padding)  # Automatically adjust y-axis limits

# Show the graph
plt.show()