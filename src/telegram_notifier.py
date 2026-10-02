import os
import sys
import requests
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_engine import data_engine
from src.db_manager import db_manager
from src.strategy import strategy

LIMIT = 4096


def _send(token, chat_id, text):
    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": text,
                                 "parse_mode": "HTML"}, timeout=30)
    if not r.ok:
        r = requests.post(url, json={"chat_id": chat_id, "text": text},
                          timeout=30)
    return r.ok


def _chunk_send(token, chat_id, text):
    if len(text) <= LIMIT:
        return _send(token, chat_id, text)
    ok = True
    part = ""
    for line in text.split("\n"):
        if len(part) + len(line) + 1 > LIMIT:
            ok = _send(token, chat_id, part) and ok
            part = ""
        part += line + "\n"
    if part.strip():
        ok = _send(token, chat_id, part) and ok
    return ok


def _fmt(v, spec=".0f"):
    try:
        f = float(v)
        if f != f or f in (float('inf'), float('-inf')):
            return "-"
        return format(f, spec)
    except Exception:
        return "-"


def _last_date():
    try:
        row = db_manager.execute_query(
            "SELECT MAX(date) FROM market_data", fetch='one')
        val = row[0] if isinstance(row, (tuple, list)) else row['max']
        return str(val)[:10]
    except Exception:
        return "unknown"


def _ihsg_regime():
    try:
        df = data_engine.get_ihsg_data()
        if df is None or df.empty or len(df) < 60:
            return "UNKNOWN", 0.0
        close = df['close'] if 'close' in df.columns else df['Close']
        last = float(close.iloc[-1])
        ma60 = float(close.tail(60).mean())
        chg20 = 0.0
        if len(close) > 21:
            chg20 = (last / float(close.iloc[-21]) - 1) * 100
        if last > ma60 and chg20 > 0:
            return "BULLISH", chg20
        if last < ma60 and chg20 < 0:
            return "BEARISH", chg20
        return "SIDEWAYS", chg20
    except Exception:
        return "UNKNOWN", 0.0


def send_rich_report():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Missing Telegram secrets")
        return
    now = datetime.now()
    header = ("<b>🎯 IDX HYBRID SNIPER - REPORT</b>\n"
              "<i>📅 " + now.strftime('%Y-%m-%d %H:%M') + " WIB | Data as of: "
              + _last_date() + "</i>\n\n")
    try:
        tickers = data_engine.get_tickers()
        signals = strategy.scan_tickers(tickers, data_engine)
        real = [s for s in signals if s.signal_type != 'NO_SIGNAL']
        regime, chg = _ihsg_regime()

        if not real:
            msg = header
            msg += "<b>😴 NO ENTRY SIGNALS THIS RUN</b>\n\n"
            msg += "┣ Scanned: " + str(len(tickers)) + " stocks\n"
            msg += "┣ IHSG regime: <b>" + regime + "</b> (" + format(chg, '+.1f') + "% 20d)\n"
            msg += "┗ All stocks filtered out by SMC/Momentum rules.\n\n"
            if regime == "BEARISH":
                msg += "<i>📉 Bearish mode: strategy intentionally stays flat — no FVG discounts nor HMA bounces qualify right now. This is risk protection, not a bug.</i>\n"
            elif regime == "SIDEWAYS":
                msg += "<i>➡️ Sideways market: setups are rare until a trend resumes. Watch for IHSG reclaiming its HMA60.</i>\n"
            else:
                msg += "<i>📈 Bullish market but no pullback setups at this moment — wait for price to tag FVG/HMA zones.</i>\n"
            msg += "\n<i>Next auto-scans: 10:20 / 12:20 / 13:50 / 17:15 WIB.</i>"
            _chunk_send(token, chat_id, msg)
            print("Sent no-signal report")
            return

        n_ent = len([s for s in real if s.signal_type == 'SMC_ENTRY'])
        n_set = len([s for s in real if s.signal_type == 'SMC_SETUP'])
        n_mom = len([s for s in real if s.signal_type == 'MOMENTUM_ENTRY'])
        msg = header
        msg += "<b>📊 MARKET SUMMARY</b>\n"
        msg += "┣ Scanned: " + str(len(tickers)) + " | IHSG: <b>" + regime + "</b>\n"
        msg += "┣  SMC Confirmed: " + str(n_ent) + "\n"
        msg += "┣ 🟡 SMC Setup: " + str(n_set) + "\n"
        msg += "┗ ⚡ Momentum: " + str(n_mom) + "\n\n"
        msg += "<pre>\n"
        msg += "TICKER   | TYPE       | ENTRY   | SL      | R:R\n"
        msg += "-" * 45 + "\n"
        for s in real[:10]:
            tt = s.signal_type.replace('SMC_', '')
            tt = tt.replace('_ENTRY', ' ENT').replace('_SETUP', ' SET')
            msg += (s.ticker.ljust(9) + "| " + tt.ljust(11) + "| "
                    + _fmt(s.entry_price).ljust(8) + "| "
                    + _fmt(s.sl_price).ljust(8) + "| 1:"
                    + _fmt(s.risk_reward_ratio, '.1f') + "\n")
        msg += "</pre>\n\n"
        msg += "<b>🔍 TOP SETUPS DEEP-DIVE:</b>\n"
        for s in real[:3]:
            msg += "\n<b>🚀 " + s.ticker + "</b> (" + s.signal_type + ")\n"
            msg += ("┣ Entry: <code>" + _fmt(s.entry_price)
                    + "</code> | SL: <code>" + _fmt(s.sl_price)
                    + "</code> | TP1: <code>" + _fmt(s.tp1_price) + "</code>\n")
            msg += ("┣ RS: <b>" + _fmt(s.rs_score, '+.1f')
                    + "%</b> | Vol: " + str(s.volume_status) + "\n")
            msg += "┗ Zone: " + str(s.zone_type or 'N/A') + "\n"
            msg += "  <i>" + str(s.reason) + "</i>\n"
        msg += "\n<i>📊 CSV/HTML lengkap ada di dashboard Streamlit.</i>"
        _chunk_send(token, chat_id, msg)
        print("Rich report sent")
    except Exception as e:
        try:
            _send(token, chat_id, "❌ Report error: " + str(e)[:300])
        except Exception:
            pass
        print("Report error:", e)


if __name__ == "__main__":
    send_rich_report()
