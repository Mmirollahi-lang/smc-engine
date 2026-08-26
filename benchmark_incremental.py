import csv
import time
from core.market_structure import Candle, MarketStructureEngine
rows=list(csv.DictReader(open("btcusdt_1h.csv",encoding="utf-8")))[-1000:]
candles=[Candle(r["timestamp"],float(r["open"]),float(r["high"]),float(r["low"]),float(r["close"])) for r in rows]
ms=MarketStructureEngine()
start=time.perf_counter()
previous_pivots=[]
for i in range(20,len(candles)):
    history=candles[:i+1]
    previous_pivots=ms.detect_pivots(history)
elapsed=time.perf_counter()-start
print("ANALYZED:",len(candles)-20)
print("SECONDS:",round(elapsed,3))
print("FINAL_PIVOTS:",len(previous_pivots))
