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
from src.fast_update import run_lightning_update
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

# Show current tickers
tickers = data_engine.get_tickers()
st.sidebar.markdown(f"**Total:** {len(tickers)} stocks")

# Update data button (LIGHTNING batch)
if st.sidebar.button("🔄 Update All Data"):
    with st.spinner("⚡ Lightning batch update from Yahoo (~2-4 min)..."):
        stats = run_lightning_update()
    st.sidebar.success(f"✅ Lightning update: {stats['saved']} tickers refreshed")

st.sidebar.markdown("---")
st.sidebar.caption("IDX Hybrid Sniper v2.0")

# Main content based on selected page

# ===================================================================
# PAGE 0: TUTORIAL & GUIDE
# ===================================================================

if page == "📖 Tutorial & Guide":
    st.title("📖 Tutorial & User Guide")
    st.markdown("*Learn how to use IDX Hybrid Sniper effectively*")

    # Quick Start
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

    # Tab Guide
    st.header("📚 How to Use Each Tab")

    tab1, tab2, tab3 = st.tabs(["📊 Market Screener", "📈 Chart Analysis", "📔 Trading Journal"])

    with tab1:
        st.markdown('''**Purpose:** Scan 900+ stocks for entry setups

**Steps:**
1. Click `🔄 Update All Data` (sidebar)
2. Click `🚀 Scan Market` button
3. Review SMC & Momentum signals
4. Sort by RS Score or R:R

**Signal Quality:**
- 🟢 Best: SMC + LOW vol + RS >+10%
- 🟡 Good: SMC + NORMAL vol + RS >0%
- 🔴 Watch: Negative RS or HIGH vol''')

    with tab2:
        st.markdown('''**Purpose:** Technical analysis per stock

**Chart Elements:**
- 🟢 Green Line = HMA60
- 🔴🟢 Dots = SuperTrend
- 🟦 Blue Box = Bullish FVG (entry)
- 📊 Volume bars + MA
- 🔵🟠 Stochastic K & D

**Entry Checklist (SMC):**

    ✅ Price in FVG zone
    ✅ SuperTrend green
    ✅ Volume LOW
    ✅ RS > 0%
''')

    with tab3:
        st.markdown('''**Purpose:** Track performance

**Add Trade:**
1. Fill form (ticker, date, price, size)
2. Select strategy type
3. Click `Add Trade`

**Close Trade:**
1. Select from Active Positions
2. Enter exit date & price
3. Click `Close Trade`

**Position Sizing:**

    Risk = Capital × 2%
    Size = Risk / (Entry - SL)
''')

    st.markdown("---")

    # Strategy
    st.header("🎯 Strategy Explained")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💎 SMC Entry")
        st.markdown('''**Philosophy:** "Buy on Weakness"

**What is FVG?**
Price gap that gets filled.

**Criteria:**
- Trend: SuperTrend bullish
- FVG: Price in zone (±10%)
- Volume: < Average
- RS: > -5%''')

    with col2:
        st.subheader("⚡ Momentum Entry")
        st.markdown('''**Philosophy:** "Ride the Trend"

**What is HMA?**
Dynamic support line.

**Criteria:**
- Trend: Price > HMA
- Distance: < 5% from HMA
- Stoch: < 60 & K > D
- RS: > -10%''')

    st.markdown("---")

    # Risk Management
    st.header("🛡️ Risk Management")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Risk/Trade", "2%")
        st.metric("Stop Loss", "Entry - 2×ATR")

    with col2:
        st.metric("Take Profit", "Entry + 3×ATR")
        st.metric("Exit", "50% at TP1")

    with col3:
        st.metric("Win Rate", "45-55%")
        st.metric("Drawdown", "10-15%")

    st.markdown("---")

    # Resources
    st.header("📚 Resources")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📖 Docs")
        st.markdown('''- USER_GUIDE.md
- QUICK_START.md
- TICKER_MANAGEMENT.md''')

        st.code('''python main.py help
python main.py guide''', language="bash")

    with col2:
        st.subheader("💡 Pro Tips")
        st.markdown('''1. Paper trade 1 week
2. Always use SL
3. Log every trade
4. 2% risk max
5. Don't chase
6. Process > Outcome''')

        st.info('''**Expected:**
Win Rate: 45-55%
Return: 30-60%/year''')

    st.success("💪 Ready? Go to **Market Screener**!")

# ===================================================================
# PAGE 1: MARKET SCREENER
# ===================================================================

elif page == "📊 Market Screener":
    st.title("📊 Market Screener")
    st.markdown("Scan pasar untuk mencari setup SMC dan Momentum Entry")

    # Auto-load cached scan results on first load
    from src.scan_cache import load_scan_results, get_cache_info

    if 'signals' not in st.session_state:
        cached_signals, cached_time = load_scan_results()
        if cached_signals is not None:
            st.session_state['signals'] = cached_signals
            st.session_state['scan_time'] = cached_time

            # Show info about cached data
            cache_age = datetime.now() - cached_time
            hours_old = cache_age.total_seconds() / 3600

            if hours_old < 1:
                st.info(f"📂 Loaded last scan from **{cached_time.strftime('%H:%M')}** ({int(cache_age.total_seconds() / 60)} minutes ago)")
            elif hours_old < 24:
                st.info(f"📂 Loaded last scan from **{cached_time.strftime('%H:%M')}** ({int(hours_old)} hours ago)")
            else:
                st.warning(f"⚠️ Loaded last scan from **{cached_time.strftime('%Y-%m-%d %H:%M')}** ({int(hours_old / 24)} days ago) - Consider running fresh scan!")

    # Help section
    with st.expander("ℹ️ How to Use Market Screener"):
        st.markdown('''
        **Steps:**
        1. Tick ⚡ box ONLY when you need LIVE Yahoo data (adds ~2-4 min).
        2. Click `🔍 Scan Market Now` button.
        3. Review SMC & Momentum signals in summary table.
        4. Use 📥 CSV / 🌐 HTML buttons to export the results.
        5. Use Signal Details Inspector for in-depth analysis.

        **Signal Quality Guide:**
        - 🟢 **Best**: SMC Confirmed + STRONG rejection + RS > +10%
        - 🟡 **Good**: SMC Setup + DISCOUNT zone + LOW volume
        - 🔵 **Watch**: Momentum Entry + Stochastic < 40
        - 🔴 **Caution**: Negative RS or HIGH volume
        ''')

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        scan_button = st.button("🔍 Scan Market Now", type="primary")
        live_update = st.checkbox("⚡ Refresh LIVE Yahoo data first (~2-4 min batch)", value=False)

    with col2:
        # Clear cache button
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
            bar = st.progress(0.0, text="⚡ Lightning batch download starting...")

            def _cb(done, total):
                bar.progress(min(done / max(total, 1), 1.0),
                             text=f"⚡ Yahoo batch {done}/{total}...")

            stats = run_lightning_update(progress_cb=_cb)
            bar.progress(1.0, text="⚡ Live update complete!")
            st.success(f"⚡ {stats['saved']} tickers refreshed from live Yahoo.")
        else:
            st.info("📡 Fast Scan: using database. Tick ⚡ box for LIVE Yahoo batch update (~2-4 min).")

        with st.spinner(f"Scanning {len(tickers)} stocks..."):
            # Scan all tickers
            signals = strategy.scan_tickers(tickers, data_engine)
            scan_time = datetime.now()

            # Store in session state
            st.session_state['signals'] = signals
            st.session_state['scan_time'] = scan_time

            # Save to persistent cache
            from src.scan_cache import save_scan_results
            if save_scan_results(signals, scan_time):
                st.success("✅ Scan complete! Results saved and will persist until next scan.")
            else:
                st.warning("✅ Scan complete! (Cache save failed, but results still available this session)")

    # Display results if available
    if 'signals' in st.session_state:
        signals = st.session_state['signals']
        scan_time = st.session_state.get('scan_time', datetime.now())

        # Filter signals (HYBRID MODE)
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

        # Summary metrics
        st.markdown(f"**Last Scan:** {scan_time.strftime('%Y-%m-%d %H:%M:%S')}")

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Scanned", len(signals))
        col2.metric("📢 SMC Setup", len([s for s in signals if s.signal_type == 'SMC_SETUP']))
        col3.metric("✅ SMC Confirmed", len([s for s in signals if s.signal_type == 'SMC_ENTRY']))
        col4.metric("⚡ Momentum", len([s for s in signals if s.signal_type == 'MOMENTUM_ENTRY']))
        col5.metric("Filtered", len(filtered_signals))

        # Convert to DataFrame
        if filtered_signals:
            df_signals = pd.DataFrame([s.to_dict() for s in filtered_signals])

            # Format columns for display (with advanced filter info)
            display_df = df_signals[[
                'ticker', 'signal_type', 'current_price', 'entry_price',
                'sl_price', 'tp1_price', 'zone_type', 'rejection_quality',
                'volume_status', 'rs_score', 'risk_reward_ratio', 'reason'
            ]].copy()

            # Rename columns
            display_df.columns = [
                'Ticker', 'Signal', 'Current', 'Entry', 'SL',
                'TP1', 'Zone', 'Rejection', 'Volume', 'RS Score', 'R:R', 'Reason'
            ]

            # Format numbers
            for col in ['Current', 'Entry', 'SL', 'TP1']:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) and x > 0 else "-")

            display_df['RS Score'] = display_df['RS Score'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "-")
            display_df['R:R'] = display_df['R:R'].apply(lambda x: f"1:{x:.2f}" if pd.notna(x) and x > 0 else "-")

            # Format advanced filter columns
            display_df['Zone'] = display_df['Zone'].apply(lambda x: x if pd.notna(x) and x else "-")
            display_df['Rejection'] = display_df['Rejection'].apply(lambda x: x if pd.notna(x) and x else "-")

            # Display table
            st.dataframe(
                display_df,
                use_container_width=True,
                height=400,
                hide_index=True
            )

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

            # Expandable details for each signal
            st.markdown("### 🔍 Signal Details Inspector")

            # Create options for dropdown
            signal_options = [f"{s.ticker} - {s.signal_type}" for s in filtered_signals]

            if signal_options:
                selected_option = st.selectbox("Select Stock to Analyze", options=signal_options)

                # Find the selected signal object
                selected_index = signal_options.index(selected_option)
                signal = filtered_signals[selected_index]

                # Display details for this signal in a container
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

                # Action Banner based on signal type
                if signal.signal_type == 'SMC_SETUP':
                    st.warning("📢 **ACTION:** Pasang BUY LIMIT order di Entry Price, tunggu konfirmasi rejection!")
                elif signal.signal_type == 'SMC_ENTRY':
                    st.success("✅ **ACTION:** BUY MARKET ORDER SEKARANG! Rejection sudah terkonfirmasi!")

                if signal.fvg_level:
                    st.info(f"📊 FVG Zone: {signal.fvg_level}")

                # Advanced Filter Details (Phase 1) - Show for both SETUP and ENTRY
                if signal.signal_type in ['SMC_SETUP', 'SMC_ENTRY'] and signal.zone_type:
                    st.markdown("### 🎯 Advanced Filter Analysis")

                    col_a, col_b = st.columns(2)

                    with col_a:
                        # Discount Zone Info
                        zone_emoji = "🟢" if signal.zone_type == "SWEET_SPOT" else "🟡"
                        zone_pct = signal.zone_position * 100 if signal.zone_position else 0
                        st.success(f"{zone_emoji} **Discount Zone:** {signal.zone_type}")
                        st.caption(f"FVG Position: {zone_pct:.1f}% of swing range")

                        # Volume Anomaly Info
                        vol_emoji = "✅" if signal.volume_anomaly == "NORMAL" else "⚠️"
                        vol_text = f"{signal.volume_ratio:.2f}x" if signal.volume_ratio else "N/A"
                        st.info(f"{vol_emoji} **Volume Check:** {signal.volume_anomaly}")
                        st.caption(f"Volume Ratio: {vol_text} of MA(20)")

                    with col_b:
                        # Rejection Candle Info
                        rej_emoji = "🟢" if signal.rejection_quality == "STRONG" else "🟡"
                        st.success(f"{rej_emoji} **Rejection:** {signal.rejection_quality}")
                        if signal.rejection_details:
                            details = signal.rejection_details
                            if isinstance(details, dict) and 'reason' not in details:
                                # Has detailed metrics
                                st.caption(f"Confirmation: Green candle with strong bounce")
                            else:
                                st.caption(f"Quality: Buyer confirmation present")

                        # TP Adjustment Info
                        if signal.tp_adjustment:
                            st.info(f"📊 **TP Strategy:** {signal.tp_adjustment}")
                            if signal.nearest_resistance:
                                st.caption(f"Resistance @ Rp {signal.nearest_resistance:,.0f}")

                    # Phase 2: Weekly Trend Info
                    if signal.weekly_trend:
                        st.markdown("### 📅 Multi-Timeframe Analysis (Phase 2)")
                        col_w = st.columns(1)[0]
                        weeks = signal.weekly_bars_in_trend if signal.weekly_bars_in_trend else 0
                        st.success(f"✅ **Weekly-Daily Aligned** ({weeks} weeks bullish)")
                        st.caption("Both weekly and daily trends are bullish - Strong trend confirmed!")

                    st.markdown("---")
                    st.caption("✅ All advanced filters passed (Phase 1 + Phase 2) - High quality setup!")

                # Calculate lot size helper
                st.markdown("### 💰 Position Sizing")
                capital = st.number_input(
                    "Your Capital (IDR)",
                    min_value=0,
                    value=100_000_000,
                    step=10_000_000,
                    key=f"capital_inspector"
                )

                lot_size = journal_mgr.calculate_lot_size(
                    capital, RISK_PERCENT, signal.entry_price, signal.sl_price
                )

                st.success(f"💰 Suggested Lot Size: {lot_size} lot ({lot_size * 100} shares)")
            else:
                st.info("ℹ️ No signals available to inspect.")

        else:
            st.info("😴 No entry signals found. Market in consolidation or all stocks filtered out.")


elif page == "📈 Chart Analysis":
    st.title("📈 Chart Analysis")
    st.markdown("Analisis chart individual dengan semua indikator")

    # Help section
    with st.expander("ℹ️ How to Read the Chart"):
        st.markdown('''
        **Chart Elements:**
        - 🟢 **Green Line** → HMA60 (Hull Moving Average) - dynamic support
        - 🔴🟢 **Dots** → SuperTrend (red = bearish, green = bullish)
        - 🟦 **Blue Boxes** → Bullish FVG zones (entry areas for SMC)
        - 🟪 **Purple Boxes** → Bearish FVG zones (resistance)
        - 📊 **Volume Bars** → Compare with Volume MA line (blue)
        - 🔵🟠 **Stochastic** → K (blue) & D (orange) - oversold < 20, overbought > 80

        **SMC Entry Checklist:**

            ✅ Price approaching/in blue FVG box
            ✅ SuperTrend dots = Green
            ✅ Volume bars < Volume MA (LOW = best)
            ✅ Price above HMA60
            → READY FOR ENTRY!

        **Momentum Entry Checklist:**

            ✅ Price bouncing from HMA60 line
            ✅ SuperTrend = Green
            ✅ Stochastic K crossing above D
            ✅ Stochastic < 60
            → READY FOR ENTRY!
        ''')

    # Ticker selection
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        selected_ticker = st.selectbox(
            "Select Ticker",
            options=tickers,
            index=0 if tickers else None
        )

    with col2:
        show_volume = st.checkbox("Show Volume", value=True)

    with col3:
        if st.button("🔄 Refresh Data"):
            data_engine.update_ticker_data(selected_ticker)
            st.success("Data updated!")

    if selected_ticker:
        # Fetch data
        with st.spinner(f"Loading data for {selected_ticker}..."):
            stock_df = data_engine.get_ticker_data(selected_ticker)
            ihsg_df = data_engine.get_ihsg_data()

        if stock_df is not None and not stock_df.empty:
            # Analyze for signals
            signal = strategy.analyze_ticker(selected_ticker, stock_df, ihsg_df)

            # Show signal status
            if signal.signal_type == 'SMC_SETUP':
                st.warning(f"📢 **SMC SETUP (Prepare Limit Order)** - {signal.reason}")

                col1, col2, col3, col4, col5 = st.columns(5)
                col1.metric("Current Price", f"Rp {signal.current_price:,.0f}")
                col2.metric("Limit Entry", f"Rp {signal.entry_price:,.0f}")
                col3.metric("Stop Loss", f"Rp {signal.sl_price:,.0f}")
                col4.metric("TP1", f"Rp {signal.tp1_price:,.0f}")
                col5.metric("Risk:Reward", f"1:{signal.risk_reward_ratio:.2f}")

                st.info("📋 **ACTION:** Pasang BUY LIMIT order di Limit Entry, tunggu konfirmasi rejection!")

                if signal.volume_status == 'LOW':
                    st.success("🟢 Volume Status: LOW - Safe pullback!")

                # Advanced Filter Details (Phase 1) for Chart Analysis
                if signal.zone_type:
                    with st.expander("🎯 Advanced Filter Details", expanded=True):
                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            zone_emoji = "🟢" if signal.zone_type == "SWEET_SPOT" else "🟡"
                            zone_pct = signal.zone_position * 100 if signal.zone_position else 0
                            st.metric(f"{zone_emoji} Zone Type", signal.zone_type)
                            st.caption(f"{zone_pct:.1f}% of swing range")

                        with col_b:
                            vol_emoji = "✅" if signal.volume_anomaly == "NORMAL" else "⚠️"
                            vol_text = f"{signal.volume_ratio:.2f}x" if signal.volume_ratio else "N/A"
                            st.metric(f"{vol_emoji} Volume Anomaly", signal.volume_anomaly)
                            st.caption(f"Ratio: {vol_text}")

                        with col_c:
                            st.metric("⏳ Rejection Status", "PENDING")
                            st.caption("Waiting for buyer confirmation")

                        if signal.tp_adjustment:
                            st.info(f"📊 TP Strategy: {signal.tp_adjustment}")

                        # Phase 2: Weekly Trend
                        if signal.weekly_trend:
                            weeks = signal.weekly_bars_in_trend if signal.weekly_bars_in_trend else 0
                            st.success(f"📅 **Weekly-Daily Aligned** ({weeks} weeks bullish trend)")

            elif signal.signal_type in ['SMC_ENTRY', 'MOMENTUM_ENTRY']:
                st.success(f"✅ **{signal.signal_type}** - {signal.reason}")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Entry", f"Rp {signal.entry_price:,.0f}")
                col2.metric("Stop Loss", f"Rp {signal.sl_price:,.0f}")
                col3.metric("TP1", f"Rp {signal.tp1_price:,.0f}")
                col4.metric("Risk:Reward", f"1:{signal.risk_reward_ratio:.2f}")

                if signal.volume_status == 'LOW':
                    st.info("🟢 Volume Status: LOW - Safe pullback!")
                elif signal.volume_status == 'HIGH':
                    st.warning("🔴 Volume Status: HIGH - Risky pullback!")

                # Advanced Filter Details (Phase 1) for Chart Analysis
                if signal.signal_type == 'SMC_ENTRY' and signal.zone_type:
                    with st.expander("🎯 Advanced Filter Details", expanded=True):
                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            zone_emoji = "🟢" if signal.zone_type == "SWEET_SPOT" else "🟡"
                            zone_pct = signal.zone_position * 100 if signal.zone_position else 0
                            st.metric(f"{zone_emoji} Zone Type", signal.zone_type)
                            st.caption(f"{zone_pct:.1f}% of swing range")

                        with col_b:
                            vol_emoji = "✅" if signal.volume_anomaly == "NORMAL" else "⚠️"
                            vol_text = f"{signal.volume_ratio:.2f}x" if signal.volume_ratio else "N/A"
                            st.metric(f"{vol_emoji} Volume Anomaly", signal.volume_anomaly)
                            st.caption(f"Ratio: {vol_text}")

                        with col_c:
                            rej_emoji = "🟢" if signal.rejection_quality == "STRONG" else "🟡"
                            st.metric(f"{rej_emoji} Rejection", signal.rejection_quality)
                            st.caption("Buyer confirmation ✓")

                        if signal.tp_adjustment:
                            st.info(f"📊 TP Strategy: {signal.tp_adjustment}")

                        # Phase 2: Weekly Trend
                        if signal.weekly_trend:
                            weeks = signal.weekly_bars_in_trend if signal.weekly_bars_in_trend else 0
                            st.success(f"📅 **Weekly-Daily Aligned** ({weeks} weeks bullish trend)")

            else:
                st.info(f"ℹ️ {signal.reason}")

                col1, col2 = st.columns(2)
                col1.metric("Current Price", f"Rp {signal.current_price:,.0f}")
                col2.metric("Trend", signal.trend)

            # Display chart
            st.markdown("---")
            fig = create_candlestick_chart(stock_df, selected_ticker, ihsg_df, show_volume)
            st.plotly_chart(fig, use_container_width=True)

            # Calculator widget
            st.markdown("---")
            st.subheader("💰 Position Size Calculator")

            col1, col2, col3 = st.columns(3)

            with col1:
                calc_capital = st.number_input("Total Capital (IDR)", min_value=0, value=100_000_000, step=10_000_000)
                calc_risk = st.number_input("Risk %", min_value=0.5, max_value=10.0, value=RISK_PERCENT, step=0.5)

            with col2:
                calc_entry = st.number_input("Entry Price", min_value=0.0, value=float(signal.entry_price if signal.entry_price > 0 else signal.current_price))
                calc_sl = st.number_input("Stop Loss", min_value=0.0, value=float(signal.sl_price if signal.sl_price > 0 else signal.current_price * 0.95))

            with col3:
                lot_size = journal_mgr.calculate_lot_size(calc_capital, calc_risk, calc_entry, calc_sl)
                st.metric("Suggested Lot Size", f"{lot_size} lot")
                st.metric("Total Shares", f"{lot_size * 100}")
                st.metric("Total Investment", f"Rp {calc_entry * lot_size * 100:,.0f}")

        else:
            st.error(f"Failed to load data for {selected_ticker}")


elif page == "📔 Trading Journal":
    st.title("📔 Trading Journal")
    st.markdown("Catat dan monitor trading performance Anda")

    # Help section
    with st.expander("ℹ️ How to Use Trading Journal"):
        st.markdown('''
        **Adding New Trade:**
        1. Go to **Add Trade** tab
        2. Fill in ticker, entry date, entry price, position size
        3. Select strategy type (SMC or Momentum)
        4. Click `Add Trade` button
        5. Trade appears in **Open Positions**

        **Closing Trade:**
        1. Go to **Open Positions** tab
        2. Find your trade in the list
        3. Expand the trade card
        4. Enter exit date and exit price
        5. Click `Close Trade` button
        6. P/L calculated automatically
        7. Trade moves to **Closed Trades**
        ''')

    tab1, tab2, tab3 = st.tabs(["Open Positions", "Add Trade", "Closed Trades"])

    with tab1:
        st.subheader("📂 Open Positions")

        if st.button("🔄 Refresh Prices"):
            st.rerun()

        # Get open positions with current prices
        with st.spinner("Loading open positions..."):
            open_df = journal_mgr.get_open_positions(with_current_prices=True)

        if not open_df.empty:
            # Display positions
            for _, trade in open_df.iterrows():
                with st.expander(f"{trade['ticker']} - Entry: Rp {trade['entry_price']:,.0f}"):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Entry Date", trade['entry_date'])
                        st.metric("Entry Price", f"Rp {trade['entry_price']:,.0f}")
                        st.metric("Lot Size", f"{trade['lot_size']} lot")

                    with col2:
                        st.metric("Current Price", f"Rp {trade['current_price']:,.0f}" if pd.notna(trade.get('current_price')) else "N/A")
                        floating_pnl = trade.get('floating_pnl_pct', 0)
                        if pd.notna(floating_pnl):
                            st.metric("Floating P/L", f"{floating_pnl:+.2f}%",
                                     delta=f"{floating_pnl:.2f}%")

                    with col3:
                        st.metric("Stop Loss", f"Rp {trade['sl_price']:,.0f}")
                        st.metric("TP1", f"Rp {trade['tp1_price']:,.0f}")

                    with col4:
                        # Action buttons
                        if st.button("📝 Update SL", key=f"update_sl_{trade['id']}"):
                            new_sl = st.number_input("New SL", value=float(trade['sl_price']), key=f"new_sl_input_{trade['id']}")
                            if st.button("Confirm Update", key=f"confirm_sl_{trade['id']}"):
                                journal_mgr.update_trailing_stop(trade['id'], new_sl)
                                st.success("SL updated!")
                                st.rerun()

                        if st.button("✅ Close Position", key=f"close_{trade['id']}"):
                            st.session_state[f'closing_{trade["id"]}'] = True

                    # Close position form
                    if st.session_state.get(f'closing_{trade["id"]}', False):
                        with st.form(f"close_form_{trade['id']}"):
                            exit_price = st.number_input("Exit Price", value=float(trade.get('current_price', trade['entry_price'])))
                            exit_reason = st.selectbox("Exit Reason", ["TP Hit", "Stop Loss", "SuperTrend Exit", "Manual Exit"])

                            if st.form_submit_button("Confirm Close"):
                                journal_mgr.close_position(trade['id'], exit_price, reason=exit_reason)
                                st.success(f"Position {trade['ticker']} closed!")
                                del st.session_state[f'closing_{trade["id"]}']
                                st.rerun()

                    if trade.get('notes'):
                        st.info(f"📝 Notes: {trade['notes']}")

        else:
            st.info("No open positions. Start trading!")

    with tab2:
        st.subheader("➕ Add New Trade")

        with st.form("add_trade_form"):
            col1, col2 = st.columns(2)

            with col1:
                trade_ticker = st.selectbox("Ticker", options=tickers)
                entry_date = st.date_input("Entry Date", value=datetime.now())
                entry_price = st.number_input("Entry Price (IDR)", min_value=0.0, step=10.0)
                lot_size = st.number_input("Lot Size", min_value=1, value=1)

            with col2:
                sl_price = st.number_input("Stop Loss (IDR)", min_value=0.0, step=10.0)
                tp1_price = st.number_input("TP1 (IDR)", min_value=0.0, step=10.0)
                notes = st.text_area("Notes", placeholder="Entry strategy, market conditions, etc.")

            submit_trade = st.form_submit_button("💾 Save Trade", type="primary")

            if submit_trade:
                if entry_price > 0 and sl_price > 0 and tp1_price > 0:
                    trade_id = journal_mgr.record_entry(
                        ticker=trade_ticker,
                        entry_price=entry_price,
                        lot_size=lot_size,
                        sl_price=sl_price,
                        tp1_price=tp1_price,
                        entry_date=entry_date.strftime('%Y-%m-%d'),
                        notes=notes
                    )
                    st.success(f"✅ Trade #{trade_id} recorded successfully!")
                else:
                    st.error("Please fill all price fields!")

    with tab3:
        st.subheader("📚 Closed Trades & Performance")

        # Get statistics
        stats = journal_mgr.get_statistics()

        # Display stats
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Trades", stats['total_trades'])
        col2.metric("Win Rate", f"{stats['win_rate']:.1f}%")
        col3.metric("Avg P/L", f"{stats['avg_pnl_percent']:+.2f}%")
        col4.metric("Total P/L", f"Rp {stats['total_pnl_idr']:,.0f}")

        col1, col2 = st.columns(2)
        col1.metric("Best Trade", f"+{stats['best_trade_percent']:.2f}%")
        col2.metric("Worst Trade", f"{stats['worst_trade_percent']:.2f}%")

        # Performance charts
        if stats['total_trades'] > 0:
            st.markdown("---")

            col1, col2 = st.columns(2)

            with col1:
                # Win rate chart
                fig_winrate = create_win_rate_chart(stats)
                st.plotly_chart(fig_winrate, use_container_width=True)

            with col2:
                # P/L chart
                closed_df = journal_mgr.get_closed_trades()
                if not closed_df.empty:
                    fig_pnl = create_performance_chart(closed_df)
                    st.plotly_chart(fig_pnl, use_container_width=True)

        # Closed trades table
        st.markdown("---")
        st.subheader("Recent Closed Trades")

        closed_df = journal_mgr.get_closed_trades(limit=20)

        if not closed_df.empty:
            display_closed = closed_df[[
                'ticker', 'entry_date', 'entry_price', 'exit_date',
                'exit_price', 'pnl_percent', 'pnl_amount', 'notes'
            ]].copy()

            display_closed.columns = [
                'Ticker', 'Entry Date', 'Entry', 'Exit Date',
                'Exit', 'P/L %', 'P/L (IDR)', 'Notes'
            ]

            # Format
            for col in ['Entry', 'Exit']:
                display_closed[col] = display_closed[col].apply(lambda x: f"Rp {x:,.0f}")

            display_closed['P/L %'] = display_closed['P/L %'].apply(lambda x: f"{x:+.2f}%")
            display_closed['P/L (IDR)'] = display_closed['P/L (IDR)'].apply(lambda x: f"Rp {x:,.0f}")

            st.dataframe(display_closed, use_container_width=True, hide_index=True)
        else:
            st.info("No closed trades yet.")


# ===================================================================
# PAGE 4: SETTINGS
# ===================================================================

elif page == "⚙️ Settings":
    st.title("⚙️ Configuration Settings")
    st.markdown("Customize strategy parameters and system thresholds")

    from src.config_mgr import config_mgr

    current_config = config_mgr.get_all()

    with st.form("settings_form"):
        st.subheader("🛡️ Risk Management")
        col1, col2 = st.columns(2)
        with col1:
            risk_percent = st.number_input("Risk Per Trade (%)", min_value=0.1, max_value=10.0, value=float(current_config.get("RISK_PERCENT", 2.0)), step=0.1, help="Percentage of total capital to risk per trade")
            sl_atr = st.number_input("Stop Loss ATR Multiplier", min_value=1.0, max_value=5.0, value=float(current_config.get("SL_ATR_MULTIPLIER", 2.0)), step=0.1, help="Multiplier of ATR to set initial Stop Loss")
        with col2:
            min_liquidity = st.number_input("Min Daily Liquidity (IDR)", min_value=1_000_000_000, value=int(current_config.get("MIN_LIQUIDITY_IDR", 5_000_000_000)), step=500_000_000, help="Minimum average daily transaction value")
            tp1_atr = st.number_input("TP1 ATR Multiplier", min_value=1.0, max_value=10.0, value=float(current_config.get("TP1_ATR_MULTIPLIER", 3.0)), step=0.1, help="Multiplier of ATR to set Take Profit 1")

        st.subheader("📊 Indicators & Filters")
        col3, col4 = st.columns(2)
        with col3:
            hma_period = st.number_input("HMA Period", min_value=10, max_value=200, value=int(current_config.get("HMA_PERIOD", 60)), help="Hull Moving Average period for trend filter")
            supertrend_mult = st.number_input("SuperTrend Multiplier", min_value=1.0, max_value=5.0, value=float(current_config.get("SUPERTREND_MULTIPLIER", 3.0)), step=0.1, help="Multiplier for SuperTrend calculation")
        with col4:
            vol_low = st.number_input("Volume Low Threshold", min_value=0.1, max_value=1.0, value=float(current_config.get("VOLUME_LOW_THRESHOLD", 0.8)), step=0.1, help="Ratio below which volume is considered LOW (safe pullback)")
            rs_strong = st.number_input("RS Strong Threshold", min_value=0.0, max_value=20.0, value=float(current_config.get("RS_STRONG", 5.0)), step=0.5, help="Relative Strength score to consider Strong")

        submitted = st.form_submit_button("💾 Save Settings", type="primary")

        if submitted:
            config_mgr.set("RISK_PERCENT", risk_percent)
            config_mgr.set("MIN_LIQUIDITY_IDR", int(min_liquidity))
            config_mgr.set("SL_ATR_MULTIPLIER", sl_atr)
            config_mgr.set("TP1_ATR_MULTIPLIER", tp1_atr)
            config_mgr.set("HMA_PERIOD", int(hma_period))
            config_mgr.set("SUPERTREND_MULTIPLIER", supertrend_mult)
            config_mgr.set("VOLUME_LOW_THRESHOLD", vol_low)
            config_mgr.set("RS_STRONG", rs_strong)

            st.success("✅ Settings saved successfully. Please restart the application to apply changes fully.")
            st.balloons()

    if st.button("↺ Reset to Defaults"):
        config_mgr.reset_to_defaults()
        st.warning("Settings reset to defaults. Please refresh the page.")
        st.rerun()


# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "IDX Hybrid Sniper v2.0 | Buy on Weakness, Sell on Strength, Ride the Monster Trend"
    "</div>",
    unsafe_allow_html=True
)
