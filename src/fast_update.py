"""
IDX Hybrid Sniper - Lightning Parallel Updater v7.0 (Bulk-Save Edition)
Phase 1: parallel fetch (8 workers, chrome session, 6-min deadline) -> frames in MEMORY
Phase 2: chunked multi-row INSERTs (<=400 rows/statement) -> seconds
Phase 3: hard_exit so hung threads can never delay the job
"""
import os
import socket
import sys
import threading
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
INSERT_CHUNK = 400

_local = threading.local()


def _session():
    s = getattr(_local, "sess", None)
    if s is None:
        try:
            from curl_cffi import requests as cffi
            s = cffi.Session(impersonate="chrome")
        except Exception:
            s = None
        _local.sess = s
    return s


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


def _fetch_one(job):
    ticker, start_str, end_str = job
    sym = ticker if ticker.endswith(".JK") else ticker + ".JK"
    for attempt in (1, 2):
        try:
            kw = dict(start=start_str, end=end_str, interval="1d",
                      progress=False, threads=False, timeout=15)
            sess = _session()
            if sess is not None:
                kw["session"] = sess
            df = yf.download(sym, **kw)
            if df is not None and len(df) > 0:
                return ticker, df
        except Exception:
            pass
        time.sleep(1)
    return ticker, None


def _bulk_save(frames):
    rows = []
    for ticker, frame in frames.items():
        sym = ticker if ticker.endswith(".JK") else ticker + ".JK"
        for idx, r in frame.iterrows():
            d = idx.date() if hasattr(idx, 'date') else idx
            rows.append((sym, d.isoformat(), float(r['Open']), float(r['High']),
                         float(r['Low']), float(r['Close']), int(r['Volume'])))
    saved = 0
    for i in range(0, len(rows), INSERT_CHUNK):
        chunk = rows[i:i + INSERT_CHUNK]
        vals = ", ".join(
            "('%s','%s',%r,%r,%r,%r,%d)" % c
            for c in chunk)
        q = ("INSERT INTO market_data (ticker, date, open, high, low, close, volume) "
             "VALUES " + vals + " "
             "ON CONFLICT (ticker, date) DO UPDATE SET "
             "open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low, "
             "close = EXCLUDED.close, volume = EXCLUDED.volume")
        try:
            db_manager.execute_query(q)
            saved += len(chunk)
        except Exception as e:
            print("chunk save failed:", str(e)[:120])
    return saved


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

    stats = {"total": len(tickers), "fetched": 0, "errors": 0,
             "deadline_skipped": 0, "rows_saved": 0}
    jobs = [(t, start_str, end_str) for t in tickers]
    frames = {}
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
                frames[ticker] = frame
                stats["fetched"] += 1
            if progress_cb:
                try:
                    progress_cb(done, len(jobs))
                except Exception:
                    pass
    except TimeoutError:
        stats["deadline_skipped"] = sum(1 for f in futs if not f.done())
    finally:
        ex.shutdown(wait=False, cancel_futures=True)

    print("FETCH PHASE DONE:", stats)
    sys.stdout.flush()
    stats["rows_saved"] = _bulk_save(frames)
    print("SAVE PHASE DONE rows:", stats["rows_saved"])
    sys.stdout.flush()

    if hard_exit:
        print('STATS:', stats)
        sys.stdout.flush()
        os._exit(0)
    return stats
