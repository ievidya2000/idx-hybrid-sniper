"""
IDX Hybrid Sniper - Lightning Batch Updater v1.0
Adapted from the Swing Screener proven speed architecture:
batch parallel Yahoo download (60 tickers per call, threads=True),
incremental window, idempotent writes to Supabase.
962 tickers refreshed in ~2-4 minutes instead of ~40.
"""
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from src.data_engine import data_engine
from src.db_manager import db_manager

BATCH_SIZE = 60
SLEEP_BETWEEN_BATCHES = 1


def _global_last_date():
    try:
        row = db_manager.execute_query(
            "SELECT MAX(date) FROM market_data", fetch='one')
        val = row[0] if isinstance(row, (tuple, list)) else row['max']
        if val is None:
            return None
        return val.date() if hasattr(val, 'date') else val
    except Exception:
        return None


def _strip_frame(df):
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in ("Open", "High", "Low", "Close", "Volume")
            if c in df.columns]
    if len(keep) < 5:
        return None
    out = df[keep].dropna(how="all")
    return out if len(out) > 0 else None


def run_lightning_update(progress_cb=None):
    tickers = data_engine.get_tickers()
    symbols = [t if t.endswith(".JK") else t + ".JK" for t in tickers]

    last = _global_last_date()
    today = datetime.now().date()
    if last is None:
        start = today - timedelta(days=365)
    else:
        start = last - timedelta(days=3)
    start_str = start.strftime("%Y-%m-%d")
    end_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    stats = {"batches": 0, "saved": 0, "empty": 0, "errors": 0}
    total_batches = (len(symbols) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[i:i + BATCH_SIZE]
        stats["batches"] += 1
        raw = None
        try:
            raw = yf.download(
                tickers=batch,
                start=start_str,
                end=end_str,
                interval="1d",
                progress=False,
                threads=True,
                group_by="ticker",
                timeout=30,
            )
        except Exception:
            stats["errors"] += 1

        if raw is not None and len(raw) > 0:
            for sym in batch:
                ticker = sym[:-3] if sym.endswith(".JK") else sym
                try:
                    if isinstance(raw.columns, pd.MultiIndex):
                        frame = _strip_frame(raw[sym])
                    elif len(batch) == 1:
                        frame = _strip_frame(raw)
                    else:
                        frame = None
                    if frame is None:
                        stats["empty"] += 1
                        continue
                    data_engine._save_rows(ticker, frame)
                    stats["saved"] += 1
                except Exception:
                    stats["errors"] += 1

        if progress_cb:
            progress_cb(stats["batches"], total_batches)
        time.sleep(SLEEP_BETWEEN_BATCHES)

    return stats
