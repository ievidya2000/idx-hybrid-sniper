import json
import os
import sys
from datetime import datetime

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db_manager import db_manager


def send(token, chat_id, text):
    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": text,
                                 "parse_mode": "HTML"}, timeout=30)
    return r.ok


def get_ihsg_trend():
    try:
        q = ("SELECT close FROM market_data WHERE ticker = '^JKSE' "
             "ORDER BY date DESC LIMIT 2")
        rows = db_manager.execute_query(q, fetch='all')
        if rows and len(rows) >= 2:
            a = rows[0][0] if isinstance(rows[0], (tuple, list)) else rows[0]['close']
            b = rows[1][0] if isinstance(rows[1], (tuple, list)) else rows[1]['close']
            pct = ((float(a) - float(b)) / float(b)) * 100
            return float(a), pct
    except Exception:
        pass
    return None, None


def send_rich_report():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Missing Telegram secrets")
        return

    payload = None
    try:
        with open("scan_out.json") as f:
            payload = json.load(f)
    except Exception:
        payload = None

    now = datetime.now()
    ihsg_price, ihsg_pct = get_ihsg_trend()
    ihsg_str = ""
    if ihsg_price:
        emoji = "🟢" if ihsg_pct >= 0 else "🔴"
        ihsg_str = f"\n<b>IHSG:</b> {emoji} {ihsg_price:,.2f} ({ihsg_pct:+.2f}%)\n"

    if payload is None:
        msg = "<b>❌ IDX SNIPER: SCAN DID NOT COMPLETE</b>\n"
        msg += f"<i>📅 {now.strftime('%Y-%m-%d %H:%M')} WIB</i>\n"
        msg += ihsg_str
        msg += "\nScan output missing. Check GitHub Actions logs."
        send(token, chat_id, msg)
        print("Sent failure report (no scan_out.json)")
        return

    signals = payload.get("signals", [])
    real = [s for s in signals if s.get("signal_type") != "NO_SIGNAL"]
    scanned = payload.get("scanned", len(signals))

    if not real:
        msg = "<b>🛡️ IDX SNIPER: CASH IS A POSITION</b>\n"
        msg += f"<i>📅 {payload.get('scan_time', '')} WIB</i>\n"
        msg += ihsg_str
        msg += "\n<b>📊 MARKET SUMMARY</b>\n"
        msg += f"┣ Scanned: {scanned} tickers\n"
        msg += "┣ Valid Setups: <b>0</b>\n"
        msg += "┗ All rejected by strict SMC/Momentum filters\n\n"
        msg += "<b>🧠 REASONING:</b> Market bearish / consolidating. No high-probability setup. Do not force trades.\n\n"
        msg += "<i>✅ Engine healthy. Next auto-scan on schedule.</i>"
        send(token, chat_id, msg)
        print("Sent 'CASH IS A POSITION' report")
        return

    n_ent = len([s for s in real if s.get("signal_type") == "SMC_ENTRY"])
    n_set = len([s for s in real if s.get("signal_type") == "SMC_SETUP"])
    n_mom = len([s for s in real if s.get("signal_type") == "MOMENTUM_ENTRY"])

    msg = "<b>🎯 IDX HYBRID SNIPER - DAILY REPORT</b>\n"
    msg += f"<i>📅 {payload.get('scan_time', '')} WIB</i>\n"
    msg += ihsg_str
    msg += "\n<b>📊 MARKET SUMMARY</b>\n"
    msg += f"┣ Scanned: {scanned} tickers\n"
    msg += f"┣ 🟢 SMC Confirmed: {n_ent}\n"
    msg += f"┣ 🟡 SMC Setup: {n_set}\n"
    msg += f"┗ ⚡ Momentum: {n_mom}\n\n"
    msg += "<pre>\nTICKER   | TYPE  | ENTRY   | SL      | R:R\n" + "-" * 45 + "\n"
    for s in real[:10]:
        tt = str(s.get("signal_type", "")).replace("SMC_", "").replace("_ENTRY", " ENT").replace("_SETUP", " SET").replace("MOMENTUM", "MOM")
        ep = s.get("entry_price") or 0
        sp = s.get("sl_price") or 0
        rr = s.get("risk_reward_ratio") or 0
        msg += (str(s.get("ticker", "?")).ljust(9) + "| " + tt.ljust(6) + "| " +
                f"{ep:<8,.0f}| {sp:<8,.0f}| 1:{rr:.1f}\n")
    msg += "</pre>\n\n<b>🔍 TOP SETUPS DEEP-DIVE:</b>\n"
    for s in real[:3]:
        msg += f"\n<b>🚀 {s.get('ticker')}</b> ({s.get('signal_type')})\n"
        msg += f"┣ Entry: <code>{(s.get('entry_price') or 0):,.0f}</code> | SL: <code>{(s.get('sl_price') or 0):,.0f}</code> | TP1: <code>{(s.get('tp1_price') or 0):,.0f}</code>\n"
        msg += f"┣ RS: <b>{(s.get('rs_score') or 0):+.1f}%</b> | Vol: {s.get('volume_status')}\n"
        msg += f"┗ Zone: {s.get('zone_type') or 'N/A'}\n  <i>{s.get('reason', '')}</i>\n"
    msg += "\n<i>📊 CSV/HTML lengkap ada di dashboard Streamlit.</i>"
    if send(token, chat_id, msg):
        print("Rich report sent")
    else:
        print("Telegram send failed")


if __name__ == "__main__":
    send_rich_report()
