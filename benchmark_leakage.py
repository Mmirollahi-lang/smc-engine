import csv
from core.market_structure import Candle, MarketStructureEngine, BreakEvent
from core.displacement import DisplacementEngine, DisplacementEvent
from core.order_block import OrderBlockEngine
from core.fvg import FVGEngine
rows=list(csv.DictReader(open("btcusdt_1h.csv",encoding="utf-8")))[-1000:]
candles=[Candle(r["timestamp"],float(r["open"]),float(r["high"]),float(r["low"]),float(r["close"])) for r in rows]
ms=MarketStructureEngine()
de=DisplacementEngine()
ob=OrderBlockEngine()
fvg=FVGEngine()
violations=0
checks=0
for i in range(20,len(candles)):
    history=candles[:i+1]
    structure=ms.analyze(history)
    break_dicts=[*structure.bos,*structure.choch]
    breaks=[BreakEvent(**x) if isinstance(x,dict) else x for x in break_dicts]
    displacement=de.analyze(history,breaks)
    events=[DisplacementEvent(**x) for x in displacement.events]
    for event in events:
        if event.index>i:
            violations+=1
    ob_result=ob.analyze(history,events,breaks)
    if ob_result.selected is not None:
        if ob_result.selected["index"]>i:
            violations+=1
    fvg_result=fvg.analyze(history,ob_result.selected)
    if fvg_result.selected is not None:
        if fvg_result.selected["index"]>i:
            violations+=1
    checks+=1
print("CHECKS:",checks)
print("LEAKAGE_VIOLATIONS:",violations)
print("STATUS:","PASS" if violations==0 else "FAIL")
