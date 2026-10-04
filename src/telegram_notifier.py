import os
import sys
import requests
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_engine import data_engine
from src.strategy import strategy
from src.db_manager import db_manager

def send(token, chat_id, text):
    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    return r.ok

def get_ihsg_trend():
    try:
        q = "SELECT close FROM market_data WHERE ticker IN ('^JKSE', 'IHSG.JK', 'IHSG') ORDER BY date DESC LIMIT 2"
        rows = db_manager.execute_query(q, fetch='all')
        if rows and len(rows) >= 2:
            today = rows[0][0] if isinstance(rows[0], (tuple, list)) else rows[0].get('close')
            yest = rows[1][0] if isinstance(rows[1], (tuple, list)) else rows[1].get('close')
            if today and yest:
                pct = ((float(today) - float(yest)) / float(yest)) * 100
                return float(today), pct
    except Exception:
        pass
    return None, None

def send_rich_report():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Missing Telegram secrets")
        return

    try:
        print("Running scan for Telegram report...")
        tickers = data_engine.get_tickers()
        signals = strategy.scan_tickers(tickers, data_engine)
        real = [s for s in signals if s.signal_type != 'NO_SIGNAL']
        now = datetime.now()
        
        ihsg_price, ihsg_pct = get_ihsg_trend()
        ihsg_str = ""
        if ihsg_price:
            emoji = "🟢" if ihsg_pct >= 0 else "🔴"
            ihsg_str = f"\n<b>IHSG Status:</b> {emoji} {ihsg_price:,.2f} ({ihsg_pct:+.2f}%)\n"

        if not real:
            # ZERO SIGNALS - BEARISH / CONSOLIDATION REPORT
            msg = "<b>🛡️ IDX SNIPER: CASH IS A POSITION</b>\n"
            msg += f"<i>📅 {now.strftime('%Y-%m-%d %H:%M')} WIB</i>\n"
            msg += ihsg_str
            msg += "\n<b>📊 MARKET SUMMARY</b>\n"
            msg += f"┣ Scanned: {len(tickers)} tickers\n"
            msg += f"┣ Valid Setups: <b>0</b>\n"
            msg += f"┗ Rejected: {len(tickers)} (Failed strict SMC/Momentum filters)\n\n"
            msg += "<b>🧠 STRATEGY REASONING:</b>\n"
            msg += "The market is currently bearish, highly volatile, or in deep consolidation.\n"
            msg += "No stocks passed the FVG + Low Volume or HMA60 Bounce criteria.\n\n"
            msg += "<b>⚡ ACTION:</b>\n"
            msg += "DO NOT FORCE TRADES. Protect your capital. Wait for the market to reveal a high-probability setup.\n\n"
            msg += "<i>✅ Engine ran successfully. Next auto-scan at next cron schedule.</i>"
            
            send(token, chat_id, msg)
            print("Sent 'No Signals / Bearish Market' report")
            return

        n_ent = len([s for s in real if s.signal_type == 'SMC_ENTRY'])
        n_set = len([s for s in real if s.signal_type == 'SMC_SETUP'])
        n_mom = len([s for s in real if s.signal_type == 'MOMENTUM_ENTRY'])
        
        msg = "<b>🎯 IDX HYBRID SNIPER - DAILY REPORT</b>\n"
        msg += f"<i>📅 {now.strftime('%Y-%m-%d %H:%M')} WIB</i>\n"
        msg += ihsg_str
        msg += "\n<b>📊 MARKET SUMMARY</b>\n"
        msg += f"┣ Scanned: {len(tickers)} tickers\n"
        msg += f"┣ 🟢 SMC Confirmed: {n_ent}\n"
        msg += f"┣ 🟡 SMC Setup: {n_set}\n"
        msg += f"┗ ⚡ Momentum: {n_mom}\n\n"
        
        msg += "<pre>\n"
        head = "TICKER   | TYPE       | ENTRY   | SL      | R:R"
        msg += head + "\n" + "-" * 45 + "\n"
        for s in real[:10]:
            tt = s.signal_type.replace('SMC_', '').replace('_ENTRY', ' ENT').replace('_SETUP', ' SET')
            line = s.ticker.ljust(9) + "| " + tt.ljust(11) + "| "
            line += str(int(s.entry_price)).ljust(8) + "| "
            line += str(int(s.sl_price)).ljust(8) + "| "
            line += "1:" + format(s.risk_reward_ratio, '.1f')
            msg += line + "\n"
        msg += "</pre>\n\n"
        
        msg += "<b>🔍 TOP SETUPS DEEP-DIVE:</b>\n"
        for s in real[:3]:
            msg += f"\n<b>🚀 {s.ticker}</b> ({s.signal_type})\n"
            msg += f"┣ Entry: <code>{s.entry_price:.0f}</code> | SL: <code>{s.sl_price:.0f}</code> | TP1: <code>{s.tp1_price:.0f}</code>\n"
            msg += f"┣ RS: <b>{s.rs_score:+.1f}%</b> | Vol: {s.volume_status}\n"
            msg += f"┗ Zone: {s.zone_type or 'N/A'}\n"
            msg += f"  <i>{s.reason}</i>\n"
            
        msg += "\n<i>📊 CSV/HTML lengkap ada di dashboard Streamlit.</i>"
        if send(token, chat_id, msg):
            print("Rich report sent")
        else:
            print("Telegram send failed")
    except Exception as e:
        try:
            send(token, chat_id, f"❌ Report error: {str(e)[:300]}")
        except Exception:
            pass

if __name__ == "__main__":
    send_rich_report()
