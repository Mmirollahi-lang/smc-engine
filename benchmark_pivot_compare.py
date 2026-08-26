import csv
from core.market_structure import Candle, MarketStructureEngine
rows=list(csv.DictReader(open("btcusdt_1h.csv",encoding="utf-8")))[-1000:]
candles=[Candle(r["timestamp"],float(r["open"]),float(r["high"]),float(r["low"]),float(r["close"])) for r in rows]
ms=MarketStructureEngine()
mismatches=0
checked=0
for i in range(20,len(candles)):
    history=candles[:i+1]
    pivots=ms.detect_pivots(history)
    pivot_index=i-ms.right
    if any(p.index>pivot_index for p in pivots):
        mismatches+=1
    checked+=1
print("CHECKED:",checked)
print("MISMATCHES:",mismatches)
print("STATUS:","PASS" if mismatches==0 else "FAIL")
