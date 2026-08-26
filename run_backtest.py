import csv
from core.market_structure import Candle
from backtest_smc import run_smc_backtest

with open("btcusdt_1h.csv", encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))

candles = [
    Candle(
        r["timestamp"],
        float(r["open"]),
        float(r["high"]),
        float(r["low"]),
        float(r["close"]),
    )
    for r in rows
]

result = run_smc_backtest(
    candles,
    min_score=70.0,
    min_rr=2.0,
    risk_pct=1.0,
    balance=10_000.0,
    analysis_window=300,
)
print(result)
