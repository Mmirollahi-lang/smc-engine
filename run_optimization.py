import csv
import json
from pathlib import Path

from core.market_structure import Candle
from optimize import optimize_and_validate


def load_candles(path: str) -> list[Candle]:
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    return [
        Candle(r["timestamp"], float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
        for r in rows[-1000:]
    ]


candles = load_candles("btcusdt_1h.csv")
report = optimize_and_validate(candles)
print(json.dumps(report.to_dict(), indent=2))
Path("optimization_report.json").write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
