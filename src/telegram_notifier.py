import os
import sys
import requests
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_engine import data_engine
from src.strategy import strategy


def send(token, chat_id, text):
    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": text,
                                 "parse_mode": "HTML"})
    return r.ok


def send_rich_report():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Missing Telegram secrets")
        return
    try:
        tickers = data_engine.get_tickers()
        signals = strategy.scan_tickers(tickers, data_engine)
        real = [s for s in signals if s.signal_type != 'NO_SIGNAL']
        now = datetime.now()
        if not real:
            msg = "<b>😴 IDX SNIPER REPORT</b>\n"
            msg += "<i>" + now.strftime('%Y-%m-%d %H:%M') + " WIB</i>\n\n"
            msg += "Tidak ada sinyal entry hari ini."
            send(token, chat_id, msg)
            print("Sent no-signal report")
            return
        n_ent = len([s for s in real if s.signal_type == 'SMC_ENTRY'])
        n_set = len([s for s in real if s.signal_type == 'SMC_SETUP'])
        n_mom = len([s for s in real if s.signal_type == 'MOMENTUM_ENTRY'])
        msg = "<b>🎯 IDX HYBRID SNIPER - DAILY REPORT</b>\n"
        msg += "<i>" + now.strftime('%Y-%m-%d %H:%M') + " WIB</i>\n\n"
        msg += "<b>📊 MARKET SUMMARY</b>\n"
        msg += "┣ Scanned: " + str(len(tickers)) + " tickers\n"
        msg += "┣ 🟢 SMC Confirmed: " + str(n_ent) + "\n"
        msg += "┣ 🟡 SMC Setup: " + str(n_set) + "\n"
        msg += "┗ ⚡ Momentum: " + str(n_mom) + "\n\n"
        msg += "<pre>\n"
        head = "TICKER   | TYPE       | ENTRY   | SL      | R:R"
        msg += head + "\n" + "-" * 45 + "\n"
        for s in real[:10]:
            tt = s.signal_type.replace('SMC_', '')
            tt = tt.replace('_ENTRY', ' ENT')
            tt = tt.replace('_SETUP', ' SET')
            line = s.ticker.ljust(9) + "| " + tt.ljust(11) + "| "
            line += str(int(s.entry_price)).ljust(8) + "| "
            line += str(int(s.sl_price)).ljust(8) + "| "
            line += "1:" + format(s.risk_reward_ratio, '.1f')
            msg += line + "\n"
        msg += "</pre>\n\n"
        msg += "<b>🔍 TOP SETUPS DEEP-DIVE:</b>\n"
        for s in real[:3]:
            msg += "\n<b>🚀 " + s.ticker + "</b> (" + s.signal_type + ")\n"
            msg += "┣ Entry: <code>" + format(s.entry_price, '.0f')
            msg += "</code> | SL: <code>" + format(s.sl_price, '.0f')
            msg += "</code> | TP1: <code>" + format(s.tp1_price, '.0f')
            msg += "</code>\n"
            msg += "┣ RS: <b>" + format(s.rs_score, '+.1f')
            msg += "%</b> | Vol: " + str(s.volume_status) + "\n"
            msg += "┗ Zone: " + str(s.zone_type or 'N/A') + "\n"
            msg += "  <i>" + str(s.reason) + "</i>\n"
        msg += "\n<i>📊 CSV/HTML lengkap ada di dashboard Streamlit.</i>"
        if send(token, chat_id, msg):
            print("Rich report sent")
        else:
            print("Telegram send failed")
    except Exception as e:
        try:
            send(token, chat_id,
                 "❌ Report error: " + str(e)[:300])
        except Exception:
            pass


if __name__ == "__main__":
    send_rich_report()
