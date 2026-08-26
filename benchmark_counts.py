import csv
from core.market_structure import Candle, MarketStructureEngine, BreakEvent
from core.displacement import DisplacementEngine
rows=list(csv.DictReader(open("btcusdt_1h.csv",encoding="utf-8")))[-1000:]
candles=[Candle(r["timestamp"],float(r["open"]),float(r["high"]),float(r["low"]),float(r["close"])) for r in rows]
ms=MarketStructureEngine()
de=DisplacementEngine()
total_d=0
max_d=0
total_b=0
for i in range(20,len(candles)):
    history=candles[:i+1]
    structure=ms.analyze(history)
    break_dicts=structure.bos+structure.choch
    breaks=[BreakEvent(**x) if isinstance(x,dict) else x for x in break_dicts]
    displacement=de.analyze(history,breaks)
    total_d+=len(displacement.events)
    max_d=max(max_d,len(displacement.events))
    total_b+=len(breaks)
print("TOTAL_DISPLACEMENTS:",total_d)
print("MAX_PER_PASS:",max_d)
print("TOTAL_BREAKS:",total_b)
