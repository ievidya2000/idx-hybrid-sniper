"""
IDX Hybrid Sniper - RAM Scanner v1.0
ONE bulk SELECT loads ALL candles into RAM, then scans purely in CPU.
Writes scan_out.json for the notifier (no re-scan anywhere).
"""
import json
from datetime import datetime

import pandas as pd

from src.db_manager import db_manager
from src.strategy import strategy

COLUMNS = ["ticker", "date", "open", "high", "low", "close", "volume"]


def _load_all_frames():
    q = ("SELECT ticker, date, open, high, low, close, volume "
         "FROM market_data ORDER BY ticker, date")
    rows = db_manager.execute_query(q, fetch='all')
    frames = {}
    if not rows:
        return frames
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    for sym, g in df.groupby("ticker", sort=False):
        g = g.set_index("date")
        frames[sym] = g[["open", "high", "low", "close", "volume"]]
    return frames


def run_ram_scan(out_path="scan_out.json"):
    from src.data_engine import data_engine
    tickers = data_engine.get_tickers()
    frames = _load_all_frames()
    ihsg = frames.get("^JKSE")
    if ihsg is None:
        try:
            ihsg = data_engine.get_ihsg_data()
        except Exception:
            ihsg = None
    signals = []
    scanned = 0
    for t in tickers:
        sym = t if t.endswith(".JK") else t + ".JK"
        df = frames.get(sym)
        if df is None or len(df) < 60:
            continue
        try:
            sig = strategy.analyze_ticker(t, df, ihsg)
            signals.append(sig.to_dict())
            scanned += 1
        except Exception:
            pass
    payload = {
        "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scanned": scanned,
        "signals": signals,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f)
    n = len([s for s in signals if s.get("signal_type") != "NO_SIGNAL"])
    print("SCAN_DONE scanned=", scanned, "signals=", n)
    return payload
