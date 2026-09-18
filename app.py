from src.database import market_db
"""
IDX Hybrid Sniper - Streamlit Web Dashboard
Interactive trading dashboard with screener, analysis, and journal
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Configure page
st.set_page_config(
    page_title="IDX Hybrid Sniper",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import modules
from src.data_engine import data_engine
from src.strategy import strategy
from src.journal_mgr import journal_mgr
from src.visualizer import (
    create_candlestick_chart, create_signal_summary_chart,
    create_performance_chart, create_win_rate_chart
)
from config.settings import RISK_PERCENT, COLOR_BULLISH, COLOR_BEARISH


# Sidebar
st.sidebar.title("🎯 IDX Hybrid Sniper")
st.sidebar.markdown("*Swing Entry, Trend Exit*")
st.sidebar.markdown("---")

# Main navigation
page = st.sidebar.radio(
    "Navigation",
    ["📖 Tutorial & Guide", "📊 Market Screener", "📈 Chart Analysis", "📔 Trading Journal", "⚙️ Settings"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")

# Watchlist management
st.sidebar.subheader("⚙️ Watchlist")

# Add ticker manually
new_ticker = st.sidebar.text_input("Add Ticker", placeholder="BBCA").upper()
if st.sidebar.button("➕ Add"):
    if new_ticker:
        if data_engine.add_ticker(new_ticker):
            st.sidebar.success(f"✅ {new_ticker} added!")
            st.rerun()
        else:
            st.sidebar.info(f"ℹ️ {new_ticker} already in watchlist")

# Import from CSV
with st.sidebar.expander("📂 Import/Export CSV"):
    st.markdown("**Import Tickers**")

    uploaded_file = st.file_uploader("Upload CSV file", type=['csv'], key='csv_upload')
    col1, col2 = st.columns(2)

    with col1:
        replace_mode = st.checkbox("Replace existing", value=False, help="If checked, will replace all tickers. Otherwise, will add to existing.")

    with col2:
        if uploaded_file is not None:
            if st.button("Import", type="primary"):
                import tempfile
                import os

                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='wb') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name

                count, imported_tickers = data_engine.import_from_csv(tmp_path, replace=replace_mode)
                os.unlink(tmp_path)

                if count > 0:
                    st.success(f"✅ Imported {count} tickers!")
                    st.rerun()
                else:
                    st.error("❌ No tickers imported. Check CSV format.")

    st.markdown("**Export Watchlist**")
    if st.button("📥 Download CSV"):
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w') as tmp_file:
            tmp_path = tmp_file.name

        if data_engine.export_to_csv(tmp_path):
            with open(tmp_path, 'r') as f:
                csv_content = f.read()

            st.download_button(
                label="💾 Save watchlist.csv",
                data=csv_content,
                file_name="idx_watchlist.csv",
                mime="text/csv"
            )
            os.unlink(tmp_path)

    st.info("📝 CSV format: Single column with 'ticker' header\n\nExample:\nticker\nBBCA\nBBRI\nTLKM")

tickers = data_engine.get_tickers()
st.sidebar.markdown(f"**Total:** {len(tickers)} stocks")

if st.sidebar.button("🔄 Update All Data"):
    with st.spinner("Updating market data..."):
        results = data_engine.update_all_tickers()
        success_count = sum(1 for msg in results.values() if "Added" in msg or "up to date" in msg)
        st.sidebar.success(f"✅ Updated {success_count}/{len(tickers)} tickers")

st.sidebar.markdown("---")
st.sidebar.caption("IDX Hybrid Sniper v2.0")

# ===================================================================
# PAGE 0: TUTORIAL & GUIDE
# ===================================================================

if page == "📖 Tutorial & Guide":
    st.title("📖 Tutorial & User Guide")
    st.markdown("*Learn how to use IDX Hybrid Sniper effectively*")
    st.header("🚀 Quick Start (5 Minutes)")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1️⃣ Setup")
        st.code('''python main.py import-csv --file watchlist_template.csv
python main.py update --full
python main.py scan''', language="bash")
        st.subheader("2️⃣ Daily Workflow")
        st.markdown('''
1. ✅ Morning: `python main.py scan`
2. ✅ Review **Market Screener**
3. ✅ Analyze **Chart Analysis**
4. ✅ Execute trades
5. ✅ Update **Trading Journal**
        ''')
    with col2:
        st.subheader("3️⃣ Strategy")
        st.info('''**SMC Entry** (Priority #1)
- Low-volume pullback
- Entry at FVG zones
- SuperTrend green

**Momentum Entry** (#2)
- HMA60 support bounce
- Stochastic turning up''')
        st.success('''**Risk Management**
- 2% risk per trade
- ATR-based SL/TP
- R:R 1:3 target''')
    st.markdown("---")
    st.header("📚 How to Use Each Tab")
    tab1, tab2, tab3 = st.tabs(["📊 Market Screener", "📈 Chart Analysis", "📔 Trading Journal"])
    with tab1:
        st.markdown('''**Purpose:** Scan 900+ stocks for entry setups
**Steps:**
1. Click `🔄 Update All Data` (sidebar)
2. Click `🚀 Scan Market` button
3. Review SMC & Momentum signals
4. Sort by RS Score or R:R''')
    with tab2:
        st.markdown('''**Purpose:** Technical analysis per stock
**Chart Elements:**
- 🟢 Green Line = HMA60
- 🔴🟢 Dots = SuperTrend
- 🟦 Blue Box = Bullish FVG (entry)''')
    with tab3:
        st.markdown('''**Purpose:** Track performance
**Add Trade:**
1. Fill form (ticker, date, price, size)
2. Select strategy type
3. Click `Add Trade`''')
    st.success("💪 Ready? Go to **Market Screener**!")

# ===================================================================
# PAGE 1: MARKET SCREENER
# ===================================================================

elif page == "📊 Market Screener":
    st.title("📊 Market Screener")
    st.markdown("Scan pasar untuk mencari setup SMC dan Momentum Entry")

    from src.scan_cache import load_scan_results, get_cache_info

    if 'signals' not in st.session_state:
        cached_signals, cached_time = load_scan_results()
        if cached_signals is not None:
            st.session_state['signals'] = cached_signals
            st.session_state['scan_time'] = cached_time
            cache_age = datetime.now() - cached_time
            hours_old = cache_age.total_seconds() / 3600
            if hours_old < 1:
                st.info(f"📂 Loaded last scan from **{cached_time.strftime('%H:%M')}** ({int(cache_age.total_seconds() / 60)} minutes ago)")
            elif hours_old < 24:
                st.info(f"📂 Loaded last scan from **{cached_time.strftime('%H:%M')}** ({int(hours_old)} hours ago)")
            else:
                st.warning(f"⚠️ Loaded last scan from **{cached_time.strftime('%Y-%m-%d %H:%M')}** ({int(hours_old / 24)} days ago) - Consider running fresh scan!")

    with st.expander("ℹ️ How to Use Market Screener"):
        st.markdown('''
        **Steps:**
        1. Click `🔍 Scan Market Now` button
        2. Wait for scan to complete (progress bar)
        3. Review SMC & Momentum signals in summary table
        ''')

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        scan_button = st.button("🔍 Scan Market Now", type="primary")
        # NEW: Checkbox for live update control
        live_update = st.checkbox("🔄 Refresh Yahoo Data first (Slow ~30-45 mins)", value=False)

    with col2:
        if st.button("🗑️ Clear Cache"):
            from src.scan_cache import clear_scan_cache
            if clear_scan_cache():
                if 'signals' in st.session_state:
                    del st.session_state['signals']
                if 'scan_time' in st.session_state:
                    del st.session_state['scan_time']
                st.success("✅ Cache cleared!")
                st.rerun()

    with col3:
        filter_type = st.selectbox(
            "Filter Signal",
            ["All Signals", "SMC Setup Only", "SMC Confirmed Only", "Momentum Entry Only", "Strong RS Only"],
            label_visibility="collapsed"
        )

    if scan_button:
        if live_update:
            with st.spinner("🔄 Downloading latest Yahoo Finance data (Keep tab open! ~30 mins)..."):
                data_engine.update_all_tickers()
        else:
            st.info("📡 Fast Scan: Using existing database. Check 'Refresh' box to update from Yahoo.")
        
        with st.spinner(f"Scanning {len(tickers)} stocks..."):
            signals = strategy.scan_tickers(tickers, data_engine)
            scan_time = datetime.now()
            st.session_state['signals'] = signals
            st.session_state['scan_time'] = scan_time
            from src.scan_cache import save_scan_results
            if save_scan_results(signals, scan_time):
                st.success("✅ Scan complete! Results saved and will persist until next scan.")
            else:
                st.warning("✅ Scan complete! (Cache save failed, but results still available this session)")

    if 'signals' in st.session_state:
        signals = st.session_state['signals']
        scan_time = st.session_state.get('scan_time', datetime.now())

        if filter_type == "SMC Setup Only":
            filtered_signals = strategy.filter_signals(signals, signal_types=['SMC_SETUP'])
        elif filter_type == "SMC Confirmed Only":
            filtered_signals = strategy.filter_signals(signals, signal_types=['SMC_ENTRY'])
        elif filter_type == "Momentum Entry Only":
            filtered_signals = strategy.filter_signals(signals, signal_types=['MOMENTUM_ENTRY'])
        elif filter_type == "Strong RS Only":
            filtered_signals = strategy.filter_signals(signals, min_rs=5.0)
        else:
            filtered_signals = [s for s in signals if s.signal_type != 'NO_SIGNAL']

        st.markdown(f"**Last Scan:** {scan_time.strftime('%Y-%m-%d %H:%M:%S')}")

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Scanned", len(signals))
        col2.metric("📢 SMC Setup", len([s for s in signals if s.signal_type == 'SMC_SETUP']))
        col3.metric("✅ SMC Confirmed", len([s for s in signals if s.signal_type == 'SMC_ENTRY']))
        col4.metric("⚡ Momentum", len([s for s in signals if s.signal_type == 'MOMENTUM_ENTRY']))
        col5.metric("Filtered", len(filtered_signals))

        if filtered_signals:
            df_signals = pd.DataFrame([s.to_dict() for s in filtered_signals])
            display_df = df_signals[[
                'ticker', 'signal_type', 'current_price', 'entry_price',
                'sl_price', 'tp1_price', 'zone_type', 'rejection_quality',
                'volume_status', 'rs_score', 'risk_reward_ratio', 'reason'
            ]].copy()
            display_df.columns = [
                'Ticker', 'Signal', 'Current', 'Entry', 'SL',
                'TP1', 'Zone', 'Rejection', 'Volume', 'RS Score', 'R:R', 'Reason'
            ]
            for col in ['Current', 'Entry', 'SL', 'TP1']:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) and x > 0 else "-")
            display_df['RS Score'] = display_df['RS Score'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "-")
            display_df['R:R'] = display_df['R:R'].apply(lambda x: f"1:{x:.2f}" if pd.notna(x) and x > 0 else "-")
            display_df['Zone'] = display_df['Zone'].apply(lambda x: x if pd.notna(x) and x else "-")
            display_df['Rejection'] = display_df['Rejection'].apply(lambda x: x if pd.notna(x) and x else "-")

            st.dataframe(display_df, use_container_width=True, height=400, hide_index=True)

            # === PROFESSIONAL EXPORT BUTTONS (CSV + HTML) ===
            stamp = scan_time.strftime('%Y%m%d_%H%M')
            csv_out = display_df.to_csv(index=False)
            csv_bytes = csv_out.encode('utf-8-sig')
            h = "<html><head><meta charset='utf-8'>"
            h += "<title>IDX Sniper Signals</title>"
            h += "<style>"
            h += "body{font-family:Arial,sans-serif;margin:24px;}"
            h += "h1{color:#0f4c81;}"
            h += "h2{color:#666666;}"
            h += "table{border-collapse:collapse;width:100%;}"
            h += "th{background:#0f4c81;color:#ffffff;padding:8px;}"
            h += "td{border:1px solid #dddddd;padding:6px;}"
            h += "tr:nth-child(even){background:#f4f8fc;}"
            h += "</style></head><body>"
            h += "<h1>IDX Hybrid Sniper - Signals</h1>"
            h += "<h2>Scan: "
            h += scan_time.strftime('%Y-%m-%d %H:%M')
            h += " WIB</h2>"
            h += display_df.to_html(index=False, border=0)
            h += "</body></html>"
            html_bytes = h.encode('utf-8')
            col_csv, col_html = st.columns(2)
            with col_csv:
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_bytes,
                    file_name="idx_signals_" + stamp + ".csv",
                    mime="text/csv",
                )
            with col_html:
                st.download_button(
                    label="🌐 Download HTML report",
                    data=html_bytes,
                    file_name="idx_signals_" + stamp + ".html",
                    mime="text/html",
                )
            # ====================================================

            st.markdown("### 🔍 Signal Details Inspector")
            signal_options = [f"{s.ticker} - {s.signal_type}" for s in filtered_signals]
            if signal_options:
                selected_option = st.selectbox("Select Stock to Analyze", options=signal_options)
                selected_index = signal_options.index(selected_option)
                signal = filtered_signals[selected_index]
                st.markdown(f"#### 🎯 Analysis: {signal.ticker}")
                st.caption(f"Strategy: {signal.signal_type}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Price", f"Rp {signal.current_price:,.0f}")
                    st.metric("Entry Price", f"Rp {signal.entry_price:,.0f}")
                with col2:
                    st.metric("Stop Loss", f"Rp {signal.sl_price:,.0f}")
                    st.metric("Take Profit 1", f"Rp {signal.tp1_price:,.0f}")
                with col3:
                    st.metric("Volume Status", signal.volume_status)
                    st.metric("RS Score", f"{signal.rs_score:+.2f}%")
                st.markdown(f"**Strategy Logic:** {signal.reason}")
                if signal.signal_type == 'SMC_SETUP':
                    st.warning("📢 **ACTION:** Pasang BUY LIMIT order di Entry Price, tunggu konfirmasi rejection!")
                elif signal.signal_type == 'SMC_ENTRY':
                    st.success("✅ **ACTION:** BUY MARKET ORDER SEKARANG! Rejection sudah terkonfirmasi!")
                if signal.fvg_level:
                    st.info(f"📊 FVG Zone: {signal.fvg_level}")
                if signal.signal_type in ['SMC_SETUP', 'SMC_ENTRY'] and signal.zone_type:
                    st.markdown("### 🎯 Advanced Filter Analysis")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        zone_emoji = "🟢" if signal.zone_type == "SWEET_SPOT" else "🟡"
                        zone_pct = signal.zone_position * 100 if signal.zone_position else 0
                        st.success(f"{zone_emoji} **Discount Zone:** {signal.zone_type}")
                        st.caption(f"FVG Position: {zone_pct:.1f}% of swing range")
                        vol_emoji = "✅" if signal.volume_anomaly == "NORMAL" else "⚠️"
                        vol_text = f"{signal.volume_ratio:.2f}x" if signal.volume_ratio else "N/A"
                        st.info(f"{vol_emoji} **Volume Check:** {signal.volume_anomaly}")
                        st.caption(f"Volume Ratio: {vol_text} of MA(20)")
                    with col_b:
                        rej_emoji = "🟢" if signal.rejection_quality == "STRONG" else "🟡"
                        st.success(f"{rej_emoji} **Rejection:** {signal.rejection_quality}")
                        if signal.tp_adjustment:
                            st.info(f"📊 **TP Strategy:** {signal.tp_adjustment}")
                            if signal.nearest_resistance:
                                st.caption(f"Resistance @ Rp {signal.nearest_resistance:,.0f}")
                    if signal.weekly_trend:
                        st.markdown("### 📅 Multi-Timeframe Analysis (Phase 2)")
                        weeks = signal.weekly_bars_in_trend if signal.weekly_bars_in_trend else 0
                        st.success(f"✅ **Weekly-Daily Aligned** ({weeks} weeks bullish)")
                    st.markdown("---")
                st.markdown("### 💰 Position Sizing")
                capital = st.number_input("Your Capital (IDR)", min_value=0, value=100_000_000, step=10_000_000, key=f"capital_inspector")
                lot_size = journal_mgr.calculate_lot_size(capital, RISK_PERCENT, signal.entry_price, signal.sl_price)
                st.success(f"💰 Suggested Lot Size: {lot_size} lot ({lot_size * 100} shares)")
            else:
                st.info("ℹ️ No signals available to inspect.")
        else:
            st.info("😴 No entry signals found. Market in consolidation or all stocks filtered out.")

elif page == "📈 Chart Analysis":
    st.title("📈 Chart Analysis")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_ticker = st.selectbox("Select Ticker", options=tickers, index=0 if tickers else None)
    with col2:
        show_volume = st.checkbox("Show Volume", value=True)
    with col3:
        if st.button("🔄 Refresh Data"):
            data_engine.update_ticker_data(selected_ticker)
            st.success("Data updated!")
    if selected_ticker:
        with st.spinner(f"Loading data for {selected_ticker}..."):
            stock_df = data_engine.get_ticker_data(selected_ticker)
            ihsg_df = data_engine.get_ihsg_data()
        if stock_df is not None and not stock_df.empty:
            signal = strategy.analyze_ticker(selected_ticker, stock_df, ihsg_df)
            if signal.signal_type == 'SMC_SETUP':
                st.warning(f"📢 **SMC SETUP (Prepare Limit Order)** - {signal.reason}")
            elif signal.signal_type in ['SMC_ENTRY', 'MOMENTUM_ENTRY']:
                st.success(f"✅ **{signal.signal_type}** - {signal.reason}")
            else:
                st.info(f"ℹ️ {signal.reason}")
            st.markdown("---")
            fig = create_candlestick_chart(stock_df, selected_ticker, ihsg_df, show_volume)
            st.plotly_chart(fig, use_container_width=True)

elif page == "📔 Trading Journal":
    st.title("📔 Trading Journal")
    tab1, tab2, tab3 = st.tabs(["Open Positions", "Add Trade", "Closed Trades"])
    with tab1:
        st.subheader("📂 Open Positions")
        with st.spinner("Loading open positions..."):
            open_df = journal_mgr.get_open_positions(with_current_prices=True)
        if not open_df.empty:
            for _, trade in open_df.iterrows():
                with st.expander(f"{trade['ticker']} - Entry: Rp {trade['entry_price']:,.0f}"):
                    st.metric("Entry Date", trade['entry_date'])
                    st.metric("Entry Price", f"Rp {trade['entry_price']:,.0f}")
        else:
            st.info("No open positions. Start trading!")
    with tab2:
        st.subheader("➕ Add New Trade")
        with st.form("add_trade_form"):
            trade_ticker = st.selectbox("Ticker", options=tickers)
            entry_price = st.number_input("Entry Price (IDR)", min_value=0.0, step=10.0)
            lot_size = st.number_input("Lot Size", min_value=1, value=1)
            sl_price = st.number_input("Stop Loss (IDR)", min_value=0.0, step=10.0)
            tp1_price = st.number_input("TP1 (IDR)", min_value=0.0, step=10.0)
            submit_trade = st.form_submit_button("💾 Save Trade", type="primary")
            if submit_trade:
                trade_id = journal_mgr.record_entry(ticker=trade_ticker, entry_price=entry_price, lot_size=lot_size, sl_price=sl_price, tp1_price=tp1_price)
                st.success(f"✅ Trade #{trade_id} recorded!")
    with tab3:
        st.subheader("📚 Closed Trades & Performance")
        stats = journal_mgr.get_statistics()
        st.metric("Total Trades", stats['total_trades'])
        st.metric("Win Rate", f"{stats['win_rate']:.1f}%")

elif page == "⚙️ Settings":
    st.title("⚙️ Configuration Settings")
    st.info("Settings panel placeholder")

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>IDX Hybrid Sniper v2.0</div>", unsafe_allow_html=True)
