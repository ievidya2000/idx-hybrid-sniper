"""
IDX Hybrid Sniper - Lightning Batch Updater v3.0 (Supergod Edition)
Batch-parallel Yahoo download. Hardwired to write directly to Supabase
bypassing any missing data_engine methods.
"""
import time
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from src.data_engine import data_engine
from src.db_manager import db_manager

BATCH_SIZE = 40
MAX_THREADS = 8
SLEEP_BETWEEN_BATCHES = 1

def _global_last_date():
    try:
        row = db_manager.execute_query("SELECT MAX(date) FROM market_data", fetch='one')
        val = row[0] if isinstance(row, (tuple, list)) else row.get('max')
        if val is None: return None
        return val.date() if hasattr(val, 'date') else val
    except Exception:
        return None

def _strip_frame(df):
    if df is None or len(df) == 0: return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]
    if len(keep) < 5: return None
    out = df[keep].dropna(how="all")
    return out if len(out) > 0 else None

def _hardwire_save(ticker, frame):
    """Direct SQL upsert to Supabase. Bypasses data_engine completely."""
    if frame is None or frame.empty: return 0
    saved = 0
    for idx, row in frame.iterrows():
        date_val = idx.date() if hasattr(idx, 'date') else idx
        try:
            q = """
                INSERT INTO market_data (ticker, date, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, date) DO UPDATE SET
                open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                close = EXCLUDED.close, volume = EXCLUDED.volume
            """
            db_manager.execute_query(q, (
                ticker, date_val, 
                float(row['Open']), float(row['High']), float(row['Low']), 
                float(row['Close']), int(row['Volume'])
            ))
            saved += 1
        except Exception:
            pass
    return saved

def run_lightning_update(progress_cb=None):
    tickers = data_engine.get_tickers()
    symbols = [t if t.endswith(".JK") else t + ".JK" for t in tickers]
    last = _global_last_date()
    today = datetime.now().date()
    start = today - timedelta(days=365) if last is None else last - timedelta(days=3)
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
                tickers=batch, start=start_str, end=end_str, interval="1d",
                progress=False, threads=True, max_threads=MAX_THREADS,
                group_by="ticker", timeout=30,
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
                    stats["saved"] += _hardwire_save(ticker, frame)
                except Exception:
                    stats["errors"] += 1

        if progress_cb:
            try: progress_cb(stats["batches"], total_batches)
            except Exception: pass
        time.sleep(SLEEP_BETWEEN_BATCHES)
    return stats
