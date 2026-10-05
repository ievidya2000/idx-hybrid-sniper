"""
IDX Hybrid Sniper - Lightning Parallel Updater v5.0 (Hang-Proof)
- socket default timeout kills hung Yahoo connections early
- 8 workers, 6-min internal deadline
- hard_exit: flush + os._exit so hung threads can NEVER delay process exit
"""
import os
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

socket.setdefaulttimeout(15)

from src.data_engine import data_engine
from src.db_manager import db_manager

WORKERS = 8
DEADLINE_SECONDS = 6 * 60


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


def _hardwire_save(ticker, frame):
    if frame is None or frame.empty:
        return 0
    sym = ticker if ticker.endswith(".JK") else ticker + ".JK"
    saved = 0
    for idx, row in frame.iterrows():
        date_val = idx.date() if hasattr(idx, 'date') else idx
        try:
            q = ("INSERT INTO market_data (ticker, date, open, high, low, close, volume) "
                 "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                 "ON CONFLICT (ticker, date) DO UPDATE SET "
                 "open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low, "
                 "close = EXCLUDED.close, volume = EXCLUDED.volume")
            db_manager.execute_query(q, (
                sym, date_val,
                float(row['Open']), float(row['High']), float(row['Low']),
                float(row['Close']), int(row['Volume'])))
            saved += 1
        except Exception:
            pass
    return saved


def _fetch_one(job):
    ticker, start_str, end_str = job
    sym = ticker if ticker.endswith(".JK") else ticker + ".JK"
    try:
        df = yf.download(sym, start=start_str, end=end_str,
                         interval="1d", progress=False,
                         threads=False, timeout=15)
        return ticker, df
    except Exception:
        return ticker, None


def run_lightning_update(progress_cb=None, hard_exit=False):
    tickers = data_engine.get_tickers()
    last = _global_last_date()
    today = datetime.now().date()
    if last is None:
        start = today - timedelta(days=365)
    else:
        start = last - timedelta(days=3)
    start_str = start.strftime("%Y-%m-%d")
    end_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    stats = {"total": len(tickers), "saved_tickers": 0,
             "rows": 0, "errors": 0, "deadline_skipped": 0}
    jobs = [(t, start_str, end_str) for t in tickers]
    done = 0
    ex = ThreadPoolExecutor(max_workers=WORKERS)
    futs = [ex.submit(_fetch_one, j) for j in jobs]
    try:
        for f in as_completed(futs, timeout=DEADLINE_SECONDS):
            ticker, df = f.result()
            done += 1
            frame = _strip_frame(df)
            if frame is None:
                stats["errors"] += 1
            else:
                n = _hardwire_save(ticker, frame)
                if n > 0:
                    stats["saved_tickers"] += 1
                    stats["rows"] += n
                else:
                    stats["errors"] += 1
            if progress_cb:
                try:
                    progress_cb(done, len(jobs))
                except Exception:
                    pass
    except TimeoutError:
        stats["deadline_skipped"] = sum(1 for f in futs if not f.done())
    finally:
        ex.shutdown(wait=False, cancel_futures=True)

    if hard_exit:
        print('STATS:', stats)
        sys.stdout.flush()
        os._exit(0)
    return stats
