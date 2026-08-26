import csv
import time
from core.market_structure import Candle, MarketStructureEngine
rows=list(csv.DictReader(open("btcusdt_1h.csv",encoding="utf-8")))[-1000:]
candles=[Candle(r["timestamp"],float(r["open"]),float(r["high"]),float(r["low"]),float(r["close"])) for r in rows]
ms=MarketStructureEngine()
start=time.perf_counter()
raw_total=0
filtered_total=0
for i in range(20,len(candles)):
    pivots=ms.detect_pivots(candles[:i+1])
    raw_total+=len(pivots)
    filtered_total+=len(pivots)
elapsed=time.perf_counter()-start
print("PASSES:",len(candles)-20)
print("SECONDS:",round(elapsed,3))
print("TOTAL_PIVOTS:",raw_total)
print("FINAL_PIVOTS:",filtered_total)
