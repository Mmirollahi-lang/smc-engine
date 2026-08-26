import csv
import time
from core.market_structure import Candle, MarketStructureEngine
from core.displacement import DisplacementEngine, DisplacementEvent
from core.order_block import OrderBlockEngine
rows=list(csv.DictReader(open("btcusdt_1h.csv",encoding="utf-8")))[-1000:]
candles=[Candle(r["timestamp"],float(r["open"]),float(r["high"]),float(r["low"]),float(r["close"])) for r in rows]
ms=MarketStructureEngine()
de=DisplacementEngine()
ob=OrderBlockEngine()
start=time.perf_counter()
phase_start=time.perf_counter()
structure_time=0.0
pivot_time=0.0
classify_time=0.0
break_time=0.0
displacement_time=0.0
ob_time=0.0
total=0
for i in range(20,len(candles)):
    history=candles[:i+1]
    t0=time.perf_counter()
    t1=time.perf_counter()
    pivots=ms.detect_pivots(history)
    pivot_time+=time.perf_counter()-t1
    t1=time.perf_counter()
    structure_points=ms.classify_structure(pivots)
    classify_time+=time.perf_counter()-t1
    t1=time.perf_counter()
    bos,choch=ms.detect_breaks(history,pivots)
    break_time+=time.perf_counter()-t1
    structure_time+=time.perf_counter()-t0
    breaks=[]
    t0=time.perf_counter()
    displacement=de.analyze(history,breaks)
    displacement_time+=time.perf_counter()-t0
    events=[DisplacementEvent(**x) for x in displacement.events]
    t0=time.perf_counter()
    result=ob.analyze(history,events,breaks)
    ob_time+=time.perf_counter()-t0
    total+=len(result.candidates)
elapsed=time.perf_counter()-start
print("ANALYZED:",len(candles)-20)
print("SECONDS:",round(elapsed,2))
print("CANDIDATES:",total)
print("STRUCTURE_SECONDS:",round(structure_time,3))
print("DISPLACEMENT_SECONDS:",round(displacement_time,3))
print("ORDER_BLOCK_SECONDS:",round(ob_time,3))
print("PIVOT_SECONDS:",round(pivot_time,3))
print("CLASSIFY_SECONDS:",round(classify_time,3))
print("BREAK_SECONDS:",round(break_time,3))
